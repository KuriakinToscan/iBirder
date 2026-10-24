#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#
#  Este programa é um software livre: você pode redistribuí-lo e/ou
#  modificá-lo sob os termos da Licença Pública Geral GNU conforme
#  publicada pela Free Software Foundation, tanto a versão 3 da
#  Licença, como (a seu critério) qualquer versão posterior.
#
#  Este programa é distribuído na esperança de que possa ser útil,
#  mas SEM NENHUMA GARANTIA; sem uma garantia implícita de
#  ADEQUAÇÃO A QUALQUER MERCADO OU APLICAÇÃO EM PARTICULAR.
#  Veja a Licença Pública Geral GNU para mais detalhes.
#
#  Você deve ter recebido uma cópia da Licença Pública Geral GNU
#  junto com este programa. Se não, veja <https://www.gnu.org/licenses/>.

"""
Publicação da foto identificada como observação no iNaturalist (issue #9, fase 1).

Fluxo: POST /v1/observations (espécie, data, local, geoprivacidade, licença) e, com o id
devolvido, POST /v1/observation_photos com o arquivo. O id fica gravado na foto
("iBirder|Publicacao|iNaturalist|<id>") para avisar antes de publicar de novo.

Decisões (24/10/2026): observação em CC BY por padrão; geoprivacidade aberta, com sugestão
de "ocultada" para espécies CR/EN/VU da Portaria MMA 148/2022 ou do Anexo I da CITES.
A licença da foto segue a configuração da conta do usuário no iNaturalist (recomendado: CC BY-NC).

Nada aqui depende do Qt: a interface (ui/dialogs/publicar_inat_dialog.py) e a thread de
envio usam estas funções, que também são testadas sem rede.
"""

import logging
import re
from pathlib import Path

from PIL import Image

from core import http
from modules.step3_geography import listas_conservacao as listas

INAT_API = "https://api.inaturalist.org/v1"
INAT_SITE = "https://www.inaturalist.org"

GEOPRIVACIDADES = {
    "open": "Aberta (coordenada exata)",
    "obscured": "Ocultada (ponto aleatório numa área de ~0,2° x 0,2°)",
    "private": "Privada (nenhuma localização pública)",
}

# Licenças aceitas pelo GBIF para a observação (CC BY-SA e CC BY-ND não são exportadas)
LICENCAS_OBSERVACAO = {
    "CC-BY": "CC BY (uso livre com crédito)",
    "CC-BY-NC": "CC BY-NC (só uso não comercial, com crédito)",
    "CC0": "CC0 (domínio público)",
}
LICENCA_PADRAO = "CC-BY"

CATEGORIAS_SENSIVEIS = {"CR", "CR (PEX)", "EN", "VU"}
EXTENSOES_ACEITAS = {".jpg", ".jpeg", ".png"}

CHAVE_REGISTRO = ("Publicacao", "iNaturalist")


class ErroPublicacao(Exception):
    """Falha na publicação; a mensagem já está pronta para o usuário."""


class TokenExpirado(ErroPublicacao):
    """O JWT não vale mais: é preciso obter outro (e, se for o caso, entrar de novo)."""


# ---------------------------------------------------------------- preparação

def sugerir_geoprivacidade(nome_cientifico, inat_id=None):
    """
    ("obscured", motivo) para espécie ameaçada na lista nacional (CR, EN, VU) ou no Anexo I
    da CITES; ("open", "") nos demais casos.
    """
    nacional = listas.status_nacional(nome_cientifico, inat_id)
    if nacional and nacional.get("categoria") in CATEGORIAS_SENSIVEIS:
        return "obscured", (f"{nacional['categoria_extenso']} ({nacional['categoria']}) "
                            f"na {listas.FONTE_NACIONAL}")
    anexo = listas.anexo_cites(nome_cientifico)
    if anexo and "I" in anexo.split("/"):
        return "obscured", "Anexo I da CITES"
    return "open", ""


def ler_data_foto(caminho):
    """Data e hora da foto (EXIF DateTimeOriginal) como 'AAAA-MM-DD HH:MM:SS', ou None."""
    try:
        with Image.open(caminho) as img:
            exif = img.getexif()
            bruto = exif.get_ifd(0x8769).get(0x9003) or exif.get(0x0132)  # DateTimeOriginal / DateTime
    except Exception as e:
        logging.debug(f"Sem data no EXIF de {caminho}: {e}")
        return None
    m = re.match(r"(\d{4}):(\d{2}):(\d{2})[ T](\d{2}):(\d{2}):(\d{2})", str(bruto or "").strip())
    if not m or m.group(1) == "0000":
        return None
    a, mes, d, h, mi, s = m.groups()
    return f"{a}-{mes}-{d} {h}:{mi}:{s}"


def ler_publicacao(registro):
    """Id da observação já publicada a partir desta foto (registro do iBirder), ou None."""
    if not registro:
        return None
    return registro.get("dados", {}).get(CHAVE_REGISTRO)


def url_observacao(id_observacao):
    return f"{INAT_SITE}/observations/{id_observacao}"


def montar_observacao(taxon_id, nome_cientifico, data, latitude=None, longitude=None,
                      geoprivacidade="open", licenca=LICENCA_PADRAO, descricao="", precisao_m=None):
    """Corpo do POST /v1/observations. Lança ErroPublicacao se faltar o essencial."""
    if not taxon_id:
        raise ErroPublicacao("A espécie não foi encontrada no iNaturalist; não é possível publicar.")
    if not data:
        raise ErroPublicacao("A foto não tem data de captura (EXIF). O iNaturalist precisa da data da observação.")
    if geoprivacidade not in GEOPRIVACIDADES:
        raise ErroPublicacao(f"Geoprivacidade inválida: {geoprivacidade}")
    if licenca not in LICENCAS_OBSERVACAO:
        raise ErroPublicacao(f"Licença inválida: {licenca}")

    obs = {
        "taxon_id": int(taxon_id),
        "species_guess": nome_cientifico,
        "observed_on_string": data,
        "geoprivacy": geoprivacidade,
        "license": licenca,
    }
    if latitude is not None and longitude is not None:
        lat, lon = float(latitude), float(longitude)
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ErroPublicacao(f"Coordenadas inválidas: {lat}, {lon}")
        obs["latitude"], obs["longitude"] = round(lat, 6), round(lon, 6)
        if precisao_m:
            obs["positional_accuracy"] = int(precisao_m)
    if descricao and descricao.strip():
        obs["description"] = descricao.strip()
    return {"observation": obs}


def verificar_foto(caminho):
    """Lança ErroPublicacao se o arquivo não puder ser enviado."""
    caminho = Path(caminho)
    if not caminho.exists():
        raise ErroPublicacao(f"Arquivo não encontrado: {caminho.name}")
    if caminho.suffix.lower() not in EXTENSOES_ACEITAS:
        raise ErroPublicacao(f"O iBirder publica só fotos JPG ou PNG ({caminho.name}).")


def obter_taxon_id(nome_cientifico):
    """Id do táxon no iNaturalist, só se o nome científico bater (busca com cache do TaxonService)."""
    from core.taxon_service import get_taxon
    taxon = get_taxon(nome_cientifico)
    if not taxon.found:
        return None
    nome_inat = " ".join((taxon.search.get("name") or "").lower().split())
    if nome_inat != " ".join((nome_cientifico or "").lower().split()):
        logging.warning(f"[Publicação] Busca por {nome_cientifico} trouxe {taxon.search.get('name')}; ignorada")
        return None
    return taxon.id


# ---------------------------------------------------------------- envio

def _mensagem_erro(resp):
    try:
        corpo = resp.json()
        erro = corpo.get("error") or corpo
        texto = erro.get("original", {}).get("error") if isinstance(erro, dict) else None
        return str(texto or erro)[:300]
    except Exception:
        return resp.text[:300]


def _verificar(resp, etapa):
    if resp.status_code == 401:
        raise TokenExpirado("A autorização do iNaturalist expirou.")
    if resp.status_code not in (200, 201):
        detalhe = _mensagem_erro(resp)
        logging.error(f"[Publicação] {etapa}: HTTP {resp.status_code} {detalhe}")
        raise ErroPublicacao(f"O iNaturalist recusou {etapa} (HTTP {resp.status_code}): {detalhe}")


def publicar(jwt, corpo, caminho_foto, sessao=None, progresso=None):
    """
    Cria a observação e anexa a foto. Retorna {"id", "uuid", "url", "foto_ok", "licenca"}.
    Se a observação for criada e a foto falhar, não desfaz: retorna foto_ok=False para o
    usuário anexar a foto pelo site (a observação existe e não deve ser duplicada).
    """
    verificar_foto(caminho_foto)
    sessao = sessao or http.get_session()
    cabecalho = {"Authorization": f"Bearer {jwt}"}
    avisar = progresso or (lambda texto: None)

    avisar("Criando a observação no iNaturalist...")
    resp = sessao.post(f"{INAT_API}/observations", json=corpo, headers=cabecalho, timeout=30)
    _verificar(resp, "a observação")
    dados = resp.json()
    if isinstance(dados, list):
        dados = dados[0] if dados else {}
    if isinstance(dados, dict) and "results" in dados:
        dados = (dados["results"] or [{}])[0]
    id_obs = dados.get("id")
    if not id_obs:
        raise ErroPublicacao("O iNaturalist não devolveu o número da observação criada.")
    logging.info(f"[Publicação] Observação {id_obs} criada")

    licenca_pedida = corpo["observation"].get("license")
    licenca = dados.get("license_code") or dados.get("license")
    if licenca and licenca_pedida and str(licenca).upper() != licenca_pedida.upper():
        logging.warning(f"[Publicação] Licença pedida {licenca_pedida}, aplicada {licenca}")

    avisar("Enviando a foto...")
    foto_ok = True
    try:
        with open(caminho_foto, "rb") as arquivo:
            resp = sessao.post(f"{INAT_API}/observation_photos", headers=cabecalho, timeout=120,
                               data={"observation_photo[observation_id]": str(id_obs)},
                               files={"file": (Path(caminho_foto).name, arquivo)})
        _verificar(resp, "a foto")
        logging.info(f"[Publicação] Foto anexada à observação {id_obs}")
    except Exception as e:
        logging.error(f"[Publicação] Observação {id_obs} criada, mas a foto falhou: {e}")
        foto_ok = False

    return {"id": id_obs, "uuid": dados.get("uuid"), "url": url_observacao(id_obs),
            "foto_ok": foto_ok, "licenca": licenca}
