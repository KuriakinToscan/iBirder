#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Verificação de novas versões do iBirder (Releases do GitHub).

Funções sem interface, para teste e reuso; a thread e os avisos ficam em
core/updater.py e ui/dialogs/nova_versao_dialog.py.

Regras:
- Na abertura do app, consulta no máximo uma vez a cada INTERVALO_HORAS e só se
  "verificar_atualizacoes" estiver ligado nas configurações.
- A verificação manual (menu de ajuda) sempre consulta.
- "Ignorar esta versão" guarda a versão em "versao_ignorada": a verificação automática
  não avisa dela (uma versão mais nova volta a ser avisada).
"""

import logging
import re
from datetime import datetime, timedelta, timezone

URL_ULTIMA_RELEASE = "https://api.github.com/repos/KuriakinToscan/iBirder/releases/latest"
URL_RELEASES = "https://github.com/KuriakinToscan/iBirder/releases"
INTERVALO_HORAS = 24
TIMEOUT = (4, 8)  # conexão, leitura (segundos)


def normalizar_versao(texto):
    """'v1.3' / 'V1.3' / ' 1.3 ' -> '1.3'; '' se vazio."""
    return re.sub(r"^[vV]", "", str(texto or "").strip())


def e_mais_nova(remota, local):
    """True se a versão remota for maior que a local (1.10 > 1.9). Versão inválida -> False."""
    from packaging.version import InvalidVersion, Version
    try:
        return Version(normalizar_versao(remota)) > Version(normalizar_versao(local))
    except InvalidVersion:
        logging.warning(f"Versão não reconhecida na comparação: remota={remota!r}, local={local!r}")
        return False


def _data_iso(texto):
    try:
        return datetime.fromisoformat(str(texto).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def ler_release(dados):
    """
    Extrai o que o aviso precisa da resposta de /releases/latest. None se a resposta não
    for uma Release publicada e válida (rascunho, pré-lançamento ou sem tag).
    """
    if not isinstance(dados, dict) or dados.get("draft") or dados.get("prerelease"):
        return None
    tag = str(dados.get("tag_name") or "").strip()
    if not tag:
        return None
    instalador = None
    for asset in dados.get("assets") or []:
        nome = str(asset.get("name") or "")
        if nome.lower().endswith(".exe"):
            url = asset.get("browser_download_url")
            # Prefere o instalador oficial se houver mais de um .exe
            if url and (instalador is None or nome.lower().startswith("instalador_ibirder")):
                instalador = url
    return {
        "versao": normalizar_versao(tag),
        "tag": tag,
        "titulo": str(dados.get("name") or "").strip() or f"iBirder {tag}",
        "data": _data_iso(dados.get("published_at")),
        "notas": str(dados.get("body") or "").strip(),
        "url_pagina": dados.get("html_url") or URL_RELEASES,
        "url_instalador": instalador,
    }


def deve_verificar(config, agora=None, intervalo_horas=INTERVALO_HORAS):
    """True se a verificação automática deve consultar o GitHub agora."""
    if not config.get("verificar_atualizacoes", True):
        return False
    ultima = _data_iso(config.get("ultima_verificacao_versao"))
    if ultima is None:
        return True
    if ultima.tzinfo is None:
        ultima = ultima.replace(tzinfo=timezone.utc)
    agora = agora or datetime.now(timezone.utc)
    # Relógio voltou no tempo (data futura gravada): verifica de novo
    return not (timedelta(0) <= agora - ultima < timedelta(hours=intervalo_horas))


def deve_avisar(info, versao_local, config, manual=False):
    """True se a Release encontrada deve ser mostrada ao usuário."""
    if not info or not e_mais_nova(info["versao"], versao_local):
        return False
    if manual:
        return True
    return normalizar_versao(config.get("versao_ignorada")) != info["versao"]


def descrever_data(data):
    """datetime -> '24/10/2026'; '' se não houver data."""
    if not data:
        return ""
    try:
        return data.astimezone().strftime("%d/%m/%Y")
    except (OverflowError, OSError, ValueError):
        return data.strftime("%d/%m/%Y")


def consultar_ultima_release():
    """
    Consulta a última Release no GitHub. Retorna o dicionário de ler_release() ou None
    (sem Release publicada). Lança RuntimeError com mensagem legível em falha de rede ou
    resposta inesperada.
    """
    from core import http
    from core.config import APP_VERSION
    headers = {"Accept": "application/vnd.github+json", "User-Agent": f"iBirder/{APP_VERSION}"}
    try:
        resp = http.get_session().get(URL_ULTIMA_RELEASE, headers=headers, timeout=TIMEOUT)
    except Exception as e:
        raise RuntimeError(f"sem conexão com o GitHub ({e.__class__.__name__})") from e
    if resp.status_code == 404:
        return None  # repositório sem Release publicada
    if resp.status_code == 403 and resp.headers.get("X-RateLimit-Remaining") == "0":
        raise RuntimeError("limite de consultas do GitHub atingido; tente novamente mais tarde")
    if resp.status_code != 200:
        raise RuntimeError(f"o GitHub respondeu com o código {resp.status_code}")
    try:
        dados = resp.json()
    except ValueError as e:
        raise RuntimeError("resposta inválida do GitHub") from e
    return ler_release(dados)
