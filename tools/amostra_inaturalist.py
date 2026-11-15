#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Baixa uma amostra de fotos de aves do Brasil (ou de outro lugar, com --lugar) do iNaturalist
para avaliar a IA local.

Critérios da amostra (API v1 do iNaturalist, sem login):
  - lugar Brasil (place_id 6878), grupo Aves, espécie (rank=species), não cativa;
  - grau de pesquisa (identificação confirmada pela comunidade): é a "espécie correta";
  - foto em licença aberta (CC0, CC BY ou CC BY-NC);
  - observada a partir de --desde (padrão 2023-01-01). O modelo local foi treinado com fotos
    do iNaturalist de alguns anos atrás: observações recentes reduzem a chance de avaliar com
    fotos que ele já viu no treino (o corte exato do treino não é conhecido);
  - no máximo --por-especie fotos de cada espécie, para a amostra não ficar dominada pelas
    aves mais comuns.

Saída na pasta indicada: as fotos (tamanho "large", ~1024 px), especies.csv (arquivo;especie,
para o avaliar_identificacao.py) e creditos.csv (observação, autor e licença de cada foto).
As fotos ficam só no seu computador; não as redistribua sem o crédito e a licença de cada uma.

Uso (no ambiente conda "ibirder-teste"; o servidor do Claude não alcança o iNaturalist):
    python tools/amostra_inaturalist.py "D:\\iBirder\\amostra_inat" --total 300
    python tools/avaliar_identificacao.py "D:\\iBirder\\amostra_inat" --csv "D:\\iBirder\\amostra_inat\\especies.csv"
ou, de uma vez:
    python tools/avaliar_identificacao.py "D:\\iBirder\\amostra_inat" --baixar-inat 300
"""

import argparse
import csv
import logging
import sys
import time
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional, Sequence

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

API = "https://api.inaturalist.org/v1/observations"
API_LUGARES = "https://api.inaturalist.org/v1/places/autocomplete"
PLACE_BRASIL = 6878
LICENCAS = "cc0,cc-by,cc-by-nc"
POR_PAGINA = 200
PAUSA_API_S = 1.1        # o iNaturalist pede no máximo ~60 requisições por minuto
PAUSA_FOTO_S = 0.2
USER_AGENT = "iBirder-avaliacao/1.0 (ferramenta de teste do app iBirder; GPL v3)"
TENTATIVAS = 5           # o iNaturalist às vezes derruba a conexão ou responde 429/5xx
ESPERA_INICIAL_S = 3.0   # espera dobra a cada nova tentativa: 3, 6, 12, 24 s


def parametros_busca(desde: str, id_abaixo: Optional[int] = None, lugar: int = PLACE_BRASIL) -> Dict[str, str]:
    """Parâmetros da consulta de observações (paginação por id decrescente, sem limite de página)."""
    params = {
        "place_id": str(lugar), "iconic_taxa": "Aves", "quality_grade": "research",
        "rank": "species", "photos": "true", "captive": "false", "photo_license": LICENCAS,
        "d1": desde, "per_page": str(POR_PAGINA), "order_by": "id", "order": "desc",
    }
    if id_abaixo:
        params["id_below"] = str(id_abaixo)
    return params


def url_foto_grande(url: str) -> str:
    """A API devolve a miniatura 'square' (75 px); 'large' tem ~1024 px no lado maior."""
    for tamanho in ("square", "small", "medium", "thumb"):
        marcador = f"/{tamanho}."
        if marcador in url:
            return url.replace(marcador, "/large.")
    return url


def selecionar(observacoes: Sequence[dict], por_especie: int, contagem: Dict[str, int],
               filtro: Optional[Callable[[str], bool]] = None) -> List[dict]:
    """
    Escolhe, de uma página de observações, uma foto por observação, respeitando o limite por
    espécie (``contagem`` é atualizado). Retorna dicts com id, especie, url, licenca, autor, uri.
    """
    escolhidas = []
    for obs in observacoes:
        taxon = obs.get("taxon") or {}
        nome = (taxon.get("name") or "").strip()
        if taxon.get("rank") != "species" or len(nome.split()) != 2:
            continue
        if filtro and not filtro(nome):
            continue
        if contagem.get(nome, 0) >= por_especie:
            continue
        foto = next((f for f in obs.get("photos") or []
                     if (f.get("license_code") or "").lower() in LICENCAS.split(",") and f.get("url")), None)
        if foto is None:
            continue
        contagem[nome] = contagem.get(nome, 0) + 1
        escolhidas.append({
            "id": obs.get("id"), "especie": nome, "url": url_foto_grande(foto["url"]),
            "licenca": foto.get("license_code", ""), "autor": (obs.get("user") or {}).get("login", ""),
            "uri": obs.get("uri") or f"https://www.inaturalist.org/observations/{obs.get('id')}",
        })
    return escolhidas


def _deve_repetir(erro: Exception) -> bool:
    """Falhas passageiras: conexão caída, tempo esgotado, 429 (limite) ou erro 5xx do servidor."""
    import requests
    if isinstance(erro, (requests.ConnectionError, requests.Timeout)):
        return True
    if isinstance(erro, requests.HTTPError) and erro.response is not None:
        return erro.response.status_code == 429 or erro.response.status_code >= 500
    return False


def get_com_retentativa(sessao, url: str, params: Optional[Dict[str, str]] = None, timeout: int = 30):
    """GET com novas tentativas e espera crescente nas falhas passageiras; repassa as demais."""
    espera = ESPERA_INICIAL_S
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            resposta = sessao.get(url, params=params, timeout=timeout)
            resposta.raise_for_status()
            return resposta
        except Exception as e:
            if tentativa == TENTATIVAS or not _deve_repetir(e):
                raise
            logging.warning(f"  iNaturalist falhou ({e}); nova tentativa {tentativa + 1}/{TENTATIVAS} em {espera:.0f} s")
            time.sleep(espera)
            espera *= 2
    raise RuntimeError("inalcançável")


def resolver_lugar(sessao, lugar: str) -> int:
    """place_id do iNaturalist: o número, ou o primeiro lugar que a busca por nome encontrar."""
    if str(lugar).strip().isdigit():
        return int(lugar)
    resposta = get_com_retentativa(sessao, API_LUGARES, params={"q": lugar, "per_page": "1"})
    resultados = resposta.json().get("results") or []
    if not resultados:
        raise ValueError(f"Lugar não encontrado no iNaturalist: {lugar!r}")
    logging.info(f"Lugar: {resultados[0].get('display_name') or resultados[0].get('name')} "
                 f"(place_id {resultados[0]['id']})")
    return int(resultados[0]["id"])


def paginas(sessao, desde: str, max_paginas: int, lugar: int = PLACE_BRASIL) -> Iterator[List[dict]]:
    """Páginas de observações, da mais nova para a mais antiga."""
    id_abaixo = None
    for _ in range(max_paginas):
        resposta = get_com_retentativa(sessao, API, params=parametros_busca(desde, id_abaixo, lugar))
        resultados = resposta.json().get("results") or []
        if not resultados:
            return
        yield resultados
        id_abaixo = min(o["id"] for o in resultados)
        time.sleep(PAUSA_API_S)


def baixar_amostra(pasta: Path, total: int = 300, por_especie: int = 2, desde: str = "2023-01-01",
                   max_paginas: int = 60, filtro: Optional[Callable[[str], bool]] = None, sessao=None,
                   lugar="6878") -> Path:
    """Baixa a amostra em ``pasta`` e retorna o caminho do especies.csv. ``lugar``: place_id ou nome."""
    import requests
    pasta.mkdir(parents=True, exist_ok=True)
    if sessao is None:
        sessao = requests.Session()
        sessao.headers["User-Agent"] = USER_AGENT
    contagem: Dict[str, int] = {}
    selecao: List[dict] = []
    place_id = resolver_lugar(sessao, lugar)
    try:
        for pagina in paginas(sessao, desde, max_paginas, place_id):
            selecao += selecionar(pagina, por_especie, contagem, filtro)
            logging.info(f"  {len(selecao)} fotos selecionadas de {len(contagem)} espécies...")
            if len(selecao) >= total:
                break
    except Exception as e:
        if not selecao:
            raise
        logging.warning(f"  Busca interrompida ({e}); seguindo com as {len(selecao)} fotos já selecionadas.")
    selecao = selecao[:total]

    baixadas = []
    for i, item in enumerate(selecao, 1):
        destino = pasta / f"inat_{item['id']}.jpg"
        if not destino.exists():
            try:
                resposta = get_com_retentativa(sessao, item["url"])
                destino.write_bytes(resposta.content)
                time.sleep(PAUSA_FOTO_S)
            except Exception as e:
                logging.warning(f"  Foto da observação {item['id']} não baixada: {e}")
                continue
        baixadas.append((destino.name, item))
        if i % 25 == 0 or i == len(selecao):
            logging.info(f"  {i}/{len(selecao)} fotos baixadas")

    especies_csv = pasta / "especies.csv"
    with open(especies_csv, "w", encoding="utf-8", newline="") as f:
        escritor = csv.writer(f, delimiter=";")
        escritor.writerow(["arquivo", "especie"])
        escritor.writerows((nome, item["especie"]) for nome, item in baixadas)
    with open(pasta / "creditos.csv", "w", encoding="utf-8-sig", newline="") as f:
        escritor = csv.writer(f, delimiter=";")
        escritor.writerow(["arquivo", "especie", "observacao", "autor", "licenca"])
        escritor.writerows((nome, item["especie"], item["uri"], item["autor"], item["licenca"])
                           for nome, item in baixadas)
    logging.info(f"Amostra pronta: {len(baixadas)} fotos de {len({i['especie'] for _, i in baixadas})} "
                 f"espécies em {pasta}")
    return especies_csv


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Baixa fotos de aves do Brasil do iNaturalist para avaliar a IA.")
    parser.add_argument("pasta", type=Path, help="pasta onde salvar as fotos")
    parser.add_argument("--total", type=int, default=300, help="número de fotos (padrão 300)")
    parser.add_argument("--por-especie", type=int, default=2, help="máximo de fotos por espécie (padrão 2)")
    parser.add_argument("--desde", default="2023-01-01", help="data mínima da observação (AAAA-MM-DD)")
    parser.add_argument("--lugar", default=str(PLACE_BRASIL),
                        help="place_id do iNaturalist ou nome do lugar (padrão: Brasil, 6878); ex.: --lugar Portugal")
    parser.add_argument("--so-conhecidas", action="store_true",
                        help="só espécies que a IA local conhece (mede a qualidade do modelo, não a cobertura)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    filtro = None
    if args.so_conhecidas:
        filtro = especies_do_modelo().__contains__
    try:
        baixar_amostra(args.pasta, args.total, args.por_especie, args.desde, filtro=filtro, lugar=args.lugar)
    except Exception as e:
        logging.error(f"Falha ao baixar a amostra do iNaturalist: {e}")
        return 1
    return 0


def especies_do_modelo() -> set:
    """Espécies (gênero + espécie) que o modelo local conhece, pelos rótulos embarcados."""
    from core.model_manager import ModelManager
    from modules.step1_identity.id_worker import formatar_rotulo
    with open(ModelManager().labels_path, encoding="utf-8") as f:
        return {formatar_rotulo(linha.strip()) for linha in f if linha.strip()}


if __name__ == "__main__":
    sys.exit(main())
