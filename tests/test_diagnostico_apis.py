"""Mensagens do botão "Testar Chaves" (issue #1: instruções confusas para leigos)."""
from core.diagnostico_apis import diagnosticar_google_vision, diagnosticar_inaturalist


def _erro(code, status, message, reason=None):
    detalhes = [{"@type": "type.googleapis.com/google.rpc.ErrorInfo", "reason": reason}] if reason else []
    return {"error": {"code": code, "status": status, "message": message, "details": detalhes}}


def test_chave_inexistente_nao_e_aceita():
    # Resposta real do Google para uma chave falsa (antes o app mostrava "Sucesso")
    ok, msg = diagnosticar_google_vision(400, _erro(400, "INVALID_ARGUMENT",
                                                    "API key not valid. Please pass a valid API key.", "API_KEY_INVALID"))
    assert not ok and "Chave inválida" in msg


def test_faturamento_desativado():
    ok, msg = diagnosticar_google_vision(403, _erro(403, "PERMISSION_DENIED",
                                                    "This API method requires billing to be enabled.", "BILLING_DISABLED"))
    assert not ok and "faturamento" in msg


def test_api_nao_ativada():
    ok, msg = diagnosticar_google_vision(403, _erro(403, "PERMISSION_DENIED",
                                                    "Cloud Vision API has not been used in project 123 before or it is disabled.",
                                                    "SERVICE_DISABLED"))
    assert not ok and "Cloud Vision API não está ativada" in msg


def test_chave_restrita():
    ok, msg = diagnosticar_google_vision(403, _erro(403, "PERMISSION_DENIED", "Requests to this API are blocked.",
                                                    "API_KEY_SERVICE_BLOCKED"))
    assert not ok and "restrita" in msg


def test_chave_valida():
    assert diagnosticar_google_vision(200, {"responses": []})[0]
    # Autenticação aceita; o 400 vem só da requisição vazia do teste
    assert diagnosticar_google_vision(400, _erro(400, "INVALID_ARGUMENT", "Empty requests."))[0]


def test_inaturalist():
    assert diagnosticar_inaturalist(200)[0]
    ok, msg = diagnosticar_inaturalist(401)
    assert not ok and "24 horas" in msg


def test_token_inat_aceita_o_que_o_usuario_copiar():
    from core.diagnostico_apis import normalizar_token_inat
    jwt = "eyJhbGciOiJIUzUxMiJ9.eyJ1c2VyX2lkIjo5fQ.abc-DEF_123"
    assert normalizar_token_inat('{"api_token":"%s"}' % jwt) == jwt          # página inteira
    assert normalizar_token_inat(' "%s" ' % jwt) == jwt                       # com aspas
    assert normalizar_token_inat("Bearer %s" % jwt) == jwt                   # com prefixo
    assert normalizar_token_inat('{"api_token":"%s"' % jwt) == jwt          # JSON cortado
    assert normalizar_token_inat("") == ""
