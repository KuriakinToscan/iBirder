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
Login no iNaturalist por OAuth 2.0 com PKCE (issue #9), usado para publicar observações.

O token JWT colado nas configurações (inat_api_token) continua servindo só para a
identificação na nuvem. Para publicar, o usuário autoriza o iBirder no navegador:

  1. o app abre /oauth/authorize com um code_challenge (SHA-256 de um segredo de uso único);
  2. o iNaturalist devolve o código para http://127.0.0.1:<porta>/callback, onde um servidor
     local temporário o recebe;
  3. o código e o segredo (code_verifier) são trocados pelo access token em /oauth/token;
  4. o access token é trocado pelo JWT da API (api.inaturalist.org) em /users/api_token.

PKCE dispensa o client secret, que não pode ficar escondido num app desktop. O aplicativo
precisa estar registrado no iNaturalist com o REDIRECT_URI abaixo, exatamente igual.
"""

import base64
import hashlib
import logging
import secrets
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

from core import http

INAT_SITE = "https://www.inaturalist.org"
URL_AUTORIZACAO = f"{INAT_SITE}/oauth/authorize"
URL_TOKEN = f"{INAT_SITE}/oauth/token"
URL_API_TOKEN = f"{INAT_SITE}/users/api_token"

PORTA_RETORNO = 8913
REDIRECT_URI = f"http://127.0.0.1:{PORTA_RETORNO}/callback"

# ID do aplicativo iBirder registrado em inaturalist.org/oauth/applications (público no PKCE).
# Vazio até o registro; a chave "inat_app_id" do config.json tem prioridade.
INAT_APP_ID = ""

TEMPO_LIMITE_LOGIN = 180  # segundos esperando o usuário autorizar no navegador

PAGINA_RETORNO = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<title>iBirder</title></head><body style="font-family: sans-serif; margin: 3em;">
<h2>{titulo}</h2><p>{texto}</p></body></html>"""


class ErroLoginInat(Exception):
    """Falha no login; a mensagem já está pronta para o usuário."""


def obter_app_id(config):
    """ID do aplicativo: o do config.json (se preenchido) ou o embarcado."""
    return (config.get("inat_app_id") or "").strip() or INAT_APP_ID


def gerar_pkce():
    """(code_verifier, code_challenge) conforme a RFC 7636, método S256."""
    verificador = secrets.token_urlsafe(64)[:128]
    return verificador, desafio_pkce(verificador)


def desafio_pkce(verificador):
    resumo = hashlib.sha256(verificador.encode("ascii")).digest()
    return base64.urlsafe_b64encode(resumo).rstrip(b"=").decode("ascii")


def montar_url_autorizacao(app_id, desafio, estado):
    parametros = {
        "client_id": app_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "code_challenge": desafio,
        "code_challenge_method": "S256",
        "state": estado,
    }
    return f"{URL_AUTORIZACAO}?{urllib.parse.urlencode(parametros)}"


def ler_retorno(caminho, estado_esperado):
    """
    Interpreta o caminho recebido no callback (ex.: '/callback?code=...&state=...').
    Retorna o código de autorização; lança ErroLoginInat se o usuário negou ou o estado não confere.
    """
    url = urllib.parse.urlparse(caminho)
    if url.path.rstrip("/") != "/callback":
        raise ErroLoginInat("Retorno inesperado do iNaturalist.")
    params = urllib.parse.parse_qs(url.query)
    if "error" in params:
        if params["error"][0] == "access_denied":
            raise ErroLoginInat("A autorização foi recusada no iNaturalist.")
        raise ErroLoginInat(f"O iNaturalist recusou a autorização ({params['error'][0]}).")
    if params.get("state", [""])[0] != estado_esperado:
        raise ErroLoginInat("A resposta do iNaturalist não confere com o pedido (estado inválido). Tente de novo.")
    codigo = params.get("code", [""])[0]
    if not codigo:
        raise ErroLoginInat("O iNaturalist não devolveu o código de autorização.")
    return codigo


def _esperar_codigo(estado, abrir_url, url, tempo_limite):
    """Sobe o servidor local, abre o navegador e espera um único retorno."""
    resultado = {}
    recebido = threading.Event()

    class Retorno(BaseHTTPRequestHandler):
        def do_GET(self):
            if urllib.parse.urlparse(self.path).path.rstrip("/") != "/callback":
                self.send_response(404)
                self.end_headers()
                return
            try:
                resultado["codigo"] = ler_retorno(self.path, estado)
                titulo, texto = "iBirder conectado ao iNaturalist", "Pode fechar esta aba e voltar ao iBirder."
            except ErroLoginInat as e:
                resultado["erro"] = e
                titulo, texto = "Não foi possível conectar", str(e)
            corpo = PAGINA_RETORNO.format(titulo=titulo, texto=texto).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)
            recebido.set()

        def log_message(self, formato, *args):
            logging.debug("[OAuth iNat] " + formato % args)

    try:
        servidor = HTTPServer(("127.0.0.1", PORTA_RETORNO), Retorno)
    except OSError as e:
        raise ErroLoginInat(f"A porta {PORTA_RETORNO} do computador está ocupada por outro programa "
                            f"({e.strerror or e}). Feche-o e tente de novo.") from e
    servidor.timeout = 1
    try:
        abrir_url(url)
        espera = 0
        while not recebido.is_set() and espera < tempo_limite:
            servidor.handle_request()
            espera += servidor.timeout
    finally:
        servidor.server_close()

    if "erro" in resultado:
        raise resultado["erro"]
    if "codigo" not in resultado:
        raise ErroLoginInat("Tempo esgotado esperando a autorização no navegador. Tente de novo.")
    return resultado["codigo"]


def trocar_codigo(app_id, codigo, verificador, sessao=None):
    """Troca o código de autorização pelo access token (OAuth)."""
    sessao = sessao or http.get_session()
    resp = sessao.post(URL_TOKEN, data={
        "client_id": app_id,
        "code": codigo,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
        "code_verifier": verificador,
    }, timeout=20)
    if resp.status_code != 200:
        logging.error(f"[OAuth iNat] /oauth/token respondeu {resp.status_code}: {resp.text[:300]}")
        raise ErroLoginInat(f"O iNaturalist não liberou o acesso (HTTP {resp.status_code}). Tente de novo.")
    token = (resp.json() or {}).get("access_token")
    if not token:
        raise ErroLoginInat("O iNaturalist não devolveu o token de acesso.")
    return token


def obter_jwt(access_token, sessao=None):
    """
    JWT da API (api.inaturalist.org) a partir do access token OAuth.
    Retorna None se o access token não vale mais (o usuário precisa entrar de novo).
    """
    sessao = sessao or http.get_session()
    resp = sessao.get(URL_API_TOKEN, headers={"Authorization": f"Bearer {access_token}"}, timeout=20)
    if resp.status_code == 401:
        return None
    if resp.status_code != 200:
        raise ErroLoginInat(f"Falha ao obter a autorização da API do iNaturalist (HTTP {resp.status_code}).")
    jwt = (resp.json() or {}).get("api_token")
    if not jwt:
        raise ErroLoginInat("O iNaturalist não devolveu o token da API.")
    return jwt


def autorizar(app_id, abrir_url=webbrowser.open, tempo_limite=TEMPO_LIMITE_LOGIN, sessao=None):
    """Fluxo completo no navegador. Retorna o access token OAuth (bloqueia até o retorno)."""
    if not app_id:
        raise ErroLoginInat("O aplicativo iBirder ainda não foi registrado no iNaturalist "
                            "(falta o ID do aplicativo). Veja o guia do usuário.")
    verificador, desafio = gerar_pkce()
    estado = secrets.token_urlsafe(16)
    logging.info("[OAuth iNat] Abrindo o navegador para autorizar o iBirder no iNaturalist")
    codigo = _esperar_codigo(estado, abrir_url, montar_url_autorizacao(app_id, desafio, estado), tempo_limite)
    token = trocar_codigo(app_id, codigo, verificador, sessao)
    logging.info("[OAuth iNat] Autorização concluída")
    return token
