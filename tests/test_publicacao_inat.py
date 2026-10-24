"""Testes offline da publicação no iNaturalist (issue #9): OAuth PKCE, corpo da observação e envio."""
import http.client
import threading
import urllib.parse

import pytest
from PIL import Image

from core import inat_oauth
from modules.step6_persistence.exif_manager import EXIFManager
from modules.step7_publicacao import inat_publicador as pub


class Resposta:
    def __init__(self, status=200, corpo=None, texto=""):
        self.status_code = status
        self._corpo = corpo
        self.text = texto

    def json(self):
        return self._corpo


class SessaoFalsa:
    """Responde em ordem e guarda as chamadas (método, url, kwargs)."""

    def __init__(self, *respostas):
        self.respostas = list(respostas)
        self.chamadas = []

    def _responder(self, metodo, url, **kwargs):
        if "files" in kwargs:
            kwargs["conteudo"] = kwargs["files"]["file"][1].read()
        self.chamadas.append((metodo, url, kwargs))
        resposta = self.respostas.pop(0)
        if isinstance(resposta, Exception):
            raise resposta
        return resposta

    def post(self, url, **kwargs):
        return self._responder("POST", url, **kwargs)

    def get(self, url, **kwargs):
        return self._responder("GET", url, **kwargs)


@pytest.fixture
def foto(tmp_path):
    caminho = tmp_path / "IMG_0001.jpg"
    exif = Image.Exif()
    exif.get_ifd(0x8769)[0x9003] = "2026:10:16 07:32:10"
    Image.new("RGB", (8, 8), "white").save(caminho, exif=exif)
    return caminho


# ---------------------------------------------------------------- OAuth (PKCE)

def test_desafio_pkce_confere_com_a_rfc_7636():
    # Exemplo do Apêndice B da RFC 7636
    assert inat_oauth.desafio_pkce("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk") == \
        "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"


def test_verificador_pkce_tem_tamanho_e_caracteres_validos():
    verificador, desafio = inat_oauth.gerar_pkce()
    assert 43 <= len(verificador) <= 128
    assert set(verificador) <= set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")
    assert desafio == inat_oauth.desafio_pkce(verificador)


def test_url_de_autorizacao():
    url = urllib.parse.urlparse(inat_oauth.montar_url_autorizacao("app123", "desafio", "estado1"))
    params = urllib.parse.parse_qs(url.query)
    assert f"{url.scheme}://{url.netloc}{url.path}" == "https://www.inaturalist.org/oauth/authorize"
    assert params == {"client_id": ["app123"], "redirect_uri": [inat_oauth.REDIRECT_URI],
                      "response_type": ["code"], "code_challenge": ["desafio"],
                      "code_challenge_method": ["S256"], "state": ["estado1"]}


def test_retorno_valido_e_recusas():
    assert inat_oauth.ler_retorno("/callback?code=abc&state=s1", "s1") == "abc"
    with pytest.raises(inat_oauth.ErroLoginInat, match="estado"):
        inat_oauth.ler_retorno("/callback?code=abc&state=outro", "s1")
    with pytest.raises(inat_oauth.ErroLoginInat, match="recusada"):
        inat_oauth.ler_retorno("/callback?error=access_denied&state=s1", "s1")
    with pytest.raises(inat_oauth.ErroLoginInat, match="código"):
        inat_oauth.ler_retorno("/callback?state=s1", "s1")


def test_servidor_local_recebe_o_codigo():
    def navegador_falso(url):
        estado = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["state"][0]

        def visitar():
            conexao = http.client.HTTPConnection("127.0.0.1", inat_oauth.PORTA_RETORNO, timeout=5)
            conexao.request("GET", f"/callback?code=cod42&state={estado}")
            assert conexao.getresponse().status == 200
        threading.Thread(target=visitar, daemon=True).start()

    url = inat_oauth.montar_url_autorizacao("app", "d", "estadoX")
    assert inat_oauth._esperar_codigo("estadoX", navegador_falso, url, tempo_limite=10) == "cod42"


def test_troca_do_codigo_e_jwt():
    sessao = SessaoFalsa(Resposta(200, {"access_token": "tok"}), Resposta(200, {"api_token": "jwt"}))
    assert inat_oauth.trocar_codigo("app", "cod", "verif", sessao) == "tok"
    _, url, kwargs = sessao.chamadas[0]
    assert url == inat_oauth.URL_TOKEN
    assert kwargs["data"]["code_verifier"] == "verif" and kwargs["data"]["grant_type"] == "authorization_code"
    assert "client_secret" not in kwargs["data"]
    assert inat_oauth.obter_jwt("tok", sessao) == "jwt"
    assert sessao.chamadas[1][2]["headers"] == {"Authorization": "Bearer tok"}


def test_jwt_com_token_expirado_retorna_none():
    assert inat_oauth.obter_jwt("velho", SessaoFalsa(Resposta(401))) is None


def test_sem_app_id_explica_o_motivo():
    with pytest.raises(inat_oauth.ErroLoginInat, match="registrado"):
        inat_oauth.autorizar("")


# ---------------------------------------------------------------- preparação

@pytest.mark.parametrize("nome, esperado", [
    ("Amadonastur lacernulatus", "obscured"),  # VU na Portaria MMA 148/2022
    ("Aceros nipalensis", "obscured"),         # Anexo I da CITES
    ("Turdus rufiventris", "open"),
])
def test_sugestao_de_geoprivacidade(nome, esperado):
    geo, motivo = pub.sugerir_geoprivacidade(nome)
    assert geo == esperado
    assert bool(motivo) == (esperado == "obscured")


def test_data_da_foto(foto, tmp_path):
    assert pub.ler_data_foto(foto) == "2026-10-16 07:32:10"
    sem_exif = tmp_path / "sem.jpg"
    Image.new("RGB", (4, 4)).save(sem_exif)
    assert pub.ler_data_foto(sem_exif) is None


def test_corpo_da_observacao():
    corpo = pub.montar_observacao(12345, "Turdus rufiventris", "2026-10-16 07:32:10", -31.7712345, -52.3412345,
                                  geoprivacidade="obscured", licenca="CC-BY", descricao="  teste ")
    assert corpo == {"observation": {
        "taxon_id": 12345, "species_guess": "Turdus rufiventris", "observed_on_string": "2026-10-16 07:32:10",
        "geoprivacy": "obscured", "license": "CC-BY", "latitude": -31.771234, "longitude": -52.341234,
        "description": "teste"}}


def test_corpo_sem_local_e_validacoes():
    corpo = pub.montar_observacao(1, "X y", "2026-10-16 07:32:10")
    assert "latitude" not in corpo["observation"]
    with pytest.raises(pub.ErroPublicacao, match="data"):
        pub.montar_observacao(1, "X y", None)
    with pytest.raises(pub.ErroPublicacao, match="espécie"):
        pub.montar_observacao(None, "X y", "2026-10-16 07:32:10")
    with pytest.raises(pub.ErroPublicacao):
        pub.montar_observacao(1, "X y", "2026-10-16 07:32:10", licenca="CC-BY-SA")
    with pytest.raises(pub.ErroPublicacao, match="Coordenadas"):
        pub.montar_observacao(1, "X y", "2026-10-16 07:32:10", 95, 10)


def test_foto_ja_publicada_e_mantida_ao_reprocessar():
    registro = {"tags": ["iBirder|Publicacao|iNaturalist|987", "iBirder|Registro|Data|2026-01-01 10:00"],
                "dados": {("Publicacao", "iNaturalist"): "987"}}
    assert pub.ler_publicacao(registro) == "987"
    assert pub.ler_publicacao(None) is None
    cmds = EXIFManager()._gerar_comandos({"nome_cientifico": "Turdus rufiventris"}, {}, registro_anterior=registro)
    assert not any("Publicacao" in c for c in cmds)
    assert "-XMP-lr:HierarchicalSubject-=iBirder|Registro|Data|2026-01-01 10:00" in cmds


# ---------------------------------------------------------------- envio

def test_publicar_cria_observacao_e_envia_foto(foto):
    sessao = SessaoFalsa(Resposta(200, {"id": 555, "uuid": "u-1", "license_code": "cc-by"}), Resposta(200, {"id": 9}))
    corpo = pub.montar_observacao(1, "X y", "2026-10-16 07:32:10")
    resultado = pub.publicar("jwt", corpo, foto, sessao=sessao)
    assert resultado == {"id": 555, "uuid": "u-1", "url": "https://www.inaturalist.org/observations/555",
                         "foto_ok": True, "licenca": "cc-by"}
    (_, url1, kw1), (_, url2, kw2) = sessao.chamadas
    assert url1.endswith("/v1/observations") and kw1["json"] == corpo
    assert kw1["headers"] == {"Authorization": "Bearer jwt"}
    assert url2.endswith("/v1/observation_photos")
    assert kw2["data"] == {"observation_photo[observation_id]": "555"}  # id numérico (UUID dá 422)
    assert kw2["conteudo"] == foto.read_bytes()


def test_foto_que_falha_nao_desfaz_a_observacao(foto):
    sessao = SessaoFalsa(Resposta(200, {"id": 7}), Resposta(500, {"error": "falhou"}))
    resultado = pub.publicar("jwt", pub.montar_observacao(1, "X y", "2026-10-16 07:32:10"), foto, sessao=sessao)
    assert resultado["id"] == 7 and resultado["foto_ok"] is False


def test_token_expirado_e_erros(foto, tmp_path):
    corpo = pub.montar_observacao(1, "X y", "2026-10-16 07:32:10")
    with pytest.raises(pub.TokenExpirado):
        pub.publicar("jwt", corpo, foto, sessao=SessaoFalsa(Resposta(401)))
    with pytest.raises(pub.ErroPublicacao, match="HTTP 422"):
        pub.publicar("jwt", corpo, foto, sessao=SessaoFalsa(Resposta(422, {"error": {"original": {"error": "inválido"}}})))
    raw = tmp_path / "IMG.CR3"
    raw.write_bytes(b"x")
    with pytest.raises(pub.ErroPublicacao, match="JPG"):
        pub.publicar("jwt", corpo, raw, sessao=SessaoFalsa())


def test_login_refeito_uma_vez_quando_o_token_salvo_expirou(monkeypatch, foto):
    from modules.step7_publicacao import publicacao_worker as pw
    config = {"inat_oauth_token": "velho", "inat_app_id": "app"}
    monkeypatch.setattr(pw, "carregar_config", lambda: dict(config))
    monkeypatch.setattr(pw, "atualizar_config", lambda **campos: config.update(campos))
    logins = []
    resultado = pw.executar_publicacao(
        {"observation": {}}, foto, progresso=lambda texto: None,
        autorizar=lambda app_id: logins.append(app_id) or "novo",
        obter_jwt=lambda token: None if token == "velho" else "jwt-" + token,
        publicar=lambda jwt, corpo, caminho, progresso: {"id": 1, "jwt": jwt})
    assert logins == ["app"] and resultado["jwt"] == "jwt-novo"
    assert config["inat_oauth_token"] == "novo"
