#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Foto de referência de cada espécie candidata (v1.6, Cartões de escolha), sem Qt.

A foto é a padrão do táxon no iNaturalist (`default_photo`), em tamanho médio (até 500 px),
com o crédito e a licença que vêm junto. Fica em cache no disco
(`temp/candidatas/<especie>.jpg` + `.json`): a mesma espécie não é baixada de novo.

Nenhum acesso ao WikiAves: o WikiAves continua consultado só para a espécie escolhida.
Sem rede, `obter_foto` devolve None e o cartão aparece sem foto.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from core import http
from core.paths import TEMP_DIR
from core.taxon_service import get_taxon

PASTA_CACHE = TEMP_DIR / "candidatas"
TAMANHO_MAXIMO_BYTES = 2 * 1024 * 1024  # foto média do iNaturalist tem ~50 a 150 KB

# Siglas de licença do iNaturalist -> texto curto exibido no cartão
LICENCAS = {
    "cc0": "CC0",
    "cc-by": "CC BY",
    "cc-by-nc": "CC BY-NC",
    "cc-by-sa": "CC BY-SA",
    "cc-by-nd": "CC BY-ND",
    "cc-by-nc-sa": "CC BY-NC-SA",
    "cc-by-nc-nd": "CC BY-NC-ND",
}


@dataclass
class FotoReferencia:
    """Foto baixada de uma espécie, com o que o cartão precisa mostrar."""
    nome_cientifico: str
    caminho: str            # arquivo JPEG no cache
    credito: str            # "(c) Fulano"
    licenca: str            # "CC BY-NC", "" se a foto não tiver licença aberta declarada
    nome_comum: str = ""    # nome popular em português do iNaturalist, se houver
    url_taxon: str = ""     # página do táxon no iNaturalist

    @property
    def texto_credito(self) -> str:
        return f"{self.credito}, {self.licenca}" if self.licenca else self.credito


def _arquivo_base(nome_cientifico: str, pasta: Path) -> Path:
    """Nome de arquivo seguro: 'Turdus rufiventris' -> 'turdus_rufiventris'."""
    chave = re.sub(r"[^a-z0-9]+", "_", (nome_cientifico or "").strip().lower()).strip("_")
    if not chave:
        raise ValueError("Nome científico vazio.")
    return pasta / chave


def _credito_limpo(atribuicao: str) -> str:
    """'(c) Fulano, some rights reserved (CC BY-NC), uploaded by X' -> '(c) Fulano'."""
    texto = (atribuicao or "").split(", uploaded by")[0]
    texto = re.sub(r",?\s*(some|all|no) rights reserved.*$", "", texto, flags=re.IGNORECASE)
    return texto.strip() or "(c) iNaturalist"


def ler_cache(nome_cientifico: str, pasta: Path = PASTA_CACHE) -> FotoReferencia | None:
    """Foto já baixada da espécie, ou None."""
    try:
        base = _arquivo_base(nome_cientifico, pasta)
    except ValueError:
        return None
    meta, imagem = base.with_suffix(".json"), base.with_suffix(".jpg")
    if not (meta.is_file() and imagem.is_file()):
        return None
    try:
        dados = json.loads(meta.read_text(encoding="utf-8"))
        dados["caminho"] = str(imagem)
        return FotoReferencia(**dados)
    except (OSError, ValueError, TypeError) as e:
        logging.debug(f"[FotosReferencia] Cache ilegível de {nome_cientifico}: {e}")
        return None


def obter_foto(nome_cientifico: str, pasta: Path = PASTA_CACHE) -> FotoReferencia | None:
    """
    Foto de referência da espécie: do cache ou baixada do iNaturalist. None se a espécie ou
    a foto não existirem, ou se a rede falhar (o erro vai para o log, sem exceção).
    """
    em_cache = ler_cache(nome_cientifico, pasta)
    if em_cache is not None:
        return em_cache
    try:
        taxon = get_taxon(nome_cientifico)
        foto = taxon.default_photo if taxon.found else None
        if not foto:
            logging.debug(f"[FotosReferencia] Sem foto padrão para {nome_cientifico}.")
            return None
        url = foto.get("medium_url") or foto.get("url") or foto.get("square_url")
        if not url:
            return None
        url = url.replace("/square.", "/medium.")
        resposta = http.get(url, timeout=10)
        resposta.raise_for_status()
        conteudo = resposta.content
        if not conteudo or len(conteudo) > TAMANHO_MAXIMO_BYTES:
            logging.warning(f"[FotosReferencia] Foto de {nome_cientifico} vazia ou grande demais.")
            return None
        base = _arquivo_base(nome_cientifico, pasta)
        pasta.mkdir(parents=True, exist_ok=True)
        imagem = base.with_suffix(".jpg")
        imagem.write_bytes(conteudo)
        resultado = FotoReferencia(
            nome_cientifico=nome_cientifico,
            caminho=str(imagem),
            credito=_credito_limpo(foto.get("attribution", "")),
            licenca=LICENCAS.get((foto.get("license_code") or "").lower(), ""),
            nome_comum=taxon.nome_comum_pt or "",
            url_taxon=taxon.url,
        )
        meta = asdict(resultado)
        meta.pop("caminho")
        base.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        return resultado
    except Exception as e:  # rede, JSON, disco: o cartão só fica sem foto
        logging.warning(f"[FotosReferencia] Foto de {nome_cientifico} indisponível: {e}")
        return None


__all__ = ["FotoReferencia", "PASTA_CACHE", "obter_foto", "ler_cache"]
