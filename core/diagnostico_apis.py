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
Diagnóstico das chaves de API (botão "Testar Chaves" das configurações).

Traduz a resposta do serviço em uma mensagem simples, dizendo o que o usuário precisa
fazer. Até a v1.2 o teste do Google considerava válida qualquer resposta 400 — inclusive
a de chave inexistente (API_KEY_INVALID) — e mostrava "Sucesso" para chaves que não
funcionavam.
"""

MANUAL = "Veja o passo a passo em \"Como obter essas chaves?\"."


def _erro_google(corpo):
    erro = (corpo or {}).get("error") or {}
    motivos = {d.get("reason") for d in erro.get("details", []) if isinstance(d, dict) and d.get("reason")}
    return erro.get("status", ""), (erro.get("message") or ""), motivos


def diagnosticar_google_vision(status_code, corpo):
    """
    Interpreta a resposta de uma chamada vazia a images:annotate.
    Retorna (ok, mensagem). Uma chamada vazia não consome a cota gratuita.
    """
    status, mensagem, motivos = _erro_google(corpo)
    msg = mensagem.lower()

    if "API_KEY_INVALID" in motivos or "api key not valid" in msg:
        return False, ("Chave inválida. Confira se copiou a chave inteira (começa com \"AIza\") "
                       "e se ela não foi apagada no Google Cloud. " + MANUAL)
    if "BILLING_DISABLED" in motivos or "billing" in msg:
        return False, ("O faturamento não está ativado no projeto do Google Cloud. Mesmo o uso gratuito "
                       "exige uma conta de faturamento vinculada (passo 2 do manual). " + MANUAL)
    if "SERVICE_DISABLED" in motivos or "has not been used" in msg or "is disabled" in msg:
        return False, ("A Cloud Vision API não está ativada neste projeto (passo 3 do manual). "
                       "Se acabou de ativar, aguarde alguns minutos e teste de novo.")
    if motivos & {"API_KEY_SERVICE_BLOCKED", "API_KEY_HTTP_REFERRER_BLOCKED",
                  "API_KEY_IP_ADDRESS_BLOCKED", "API_KEY_ANDROID_APP_BLOCKED", "API_KEY_IOS_APP_BLOCKED"}:
        return False, ("A chave existe, mas está restrita e não pode usar a Cloud Vision API. Nas restrições "
                       "da chave, permita a \"Cloud Vision API\" e deixe \"Restrições de aplicativo\" como "
                       "\"Nenhuma\" (passo 5 do manual).")
    if status_code == 429 or "RESOURCE_EXHAUSTED" in status or "RATE_LIMIT_EXCEEDED" in motivos:
        return False, "A cota da chave foi excedida. Tente novamente mais tarde ou verifique as cotas no Google Cloud."
    if status_code == 200 or (status_code == 400 and status == "INVALID_ARGUMENT"):
        # A autenticação passou; o 400 restante é só a requisição vazia usada no teste
        return True, "Chave válida e Cloud Vision API ativa."
    if status_code == 403:
        return False, f"Acesso negado pelo Google ({mensagem or status}). " + MANUAL
    return False, f"Resposta inesperada do Google (HTTP {status_code}): {mensagem or 'sem detalhes'}."


def normalizar_token_inat(texto):
    """
    Aceita o que o usuário copiar da página inaturalist.org/users/api_token:
    o JSON inteiro ({"api_token":"eyJ..."}), o código entre aspas ou "Bearer eyJ...".
    """
    import json
    import re
    texto = (texto or "").strip()
    if texto.startswith("{"):
        try:
            texto = str(json.loads(texto).get("api_token", texto))
        except (ValueError, AttributeError):
            achado = re.search(r"eyJ[A-Za-z0-9._\-]+", texto)
            texto = achado.group(0) if achado else texto
    texto = texto.strip().strip('"').strip("'")
    if texto.lower().startswith("bearer "):
        texto = texto[7:].strip()
    return texto


def diagnosticar_inaturalist(status_code):
    """Interpreta a resposta de GET /v1/users/me com o token informado."""
    if status_code == 200:
        return True, "Token válido."
    if status_code in (401, 403):
        return False, ("Token inválido ou expirado. O token do iNaturalist vale por cerca de 24 horas: "
                       "gere um novo em inaturalist.org/users/api_token (com a conta logada) e cole aqui.")
    if status_code == 429:
        return False, "Muitas requisições ao iNaturalist. Aguarde alguns minutos e teste de novo."
    return False, f"Resposta inesperada do iNaturalist (HTTP {status_code}). Tente novamente mais tarde."
