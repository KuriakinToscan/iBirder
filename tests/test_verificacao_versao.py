"""Aviso de novas versões: comparação, leitura da Release, intervalo de 24 h e versão ignorada."""
from datetime import datetime, timedelta, timezone

import pytest

from core import verificacao_versao as vv

RELEASE = {
    "tag_name": "v1.4",
    "name": "iBirder v1.4",
    "body": "## Novidades\n- Temas visuais",
    "html_url": "https://github.com/KuriakinToscan/iBirder/releases/tag/v1.4",
    "published_at": "2026-11-02T13:00:00Z",
    "draft": False,
    "prerelease": False,
    "assets": [
        {"name": "outro.zip", "browser_download_url": "https://exemplo/outro.zip"},
        {"name": "Instalador_iBirder_v1.4.exe", "browser_download_url": "https://exemplo/Instalador_iBirder_v1.4.exe"},
    ],
}
AGORA = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize("remota, local, esperado", [
    ("v1.4", "1.3", True),
    ("V1.4", "1.3", True),       # tag criada com V maiúsculo
    ("v1.3", "1.3", False),
    ("v1.3.0", "1.3", False),
    ("v1.10", "1.9", True),      # comparação numérica, não de texto
    ("v1.2", "1.3", False),
    ("versao-nova", "1.3", False),  # tag inválida nunca gera aviso
    ("", "1.3", False),
])
def test_e_mais_nova(remota, local, esperado):
    assert vv.e_mais_nova(remota, local) is esperado


def test_ler_release_extrai_instalador_e_data():
    info = vv.ler_release(RELEASE)
    assert info["versao"] == "1.4" and info["tag"] == "v1.4"
    assert info["url_instalador"].endswith("Instalador_iBirder_v1.4.exe")
    assert info["data"] == datetime(2026, 11, 2, 13, 0, tzinfo=timezone.utc)
    assert info["notas"].startswith("## Novidades")


def test_ler_release_sem_instalador_usa_pagina():
    info = vv.ler_release({**RELEASE, "assets": []})
    assert info["url_instalador"] is None
    assert info["url_pagina"].endswith("/v1.4")


@pytest.mark.parametrize("dados", [
    None, {}, {"tag_name": ""}, {**RELEASE, "draft": True}, {**RELEASE, "prerelease": True},
])
def test_ler_release_invalida(dados):
    assert vv.ler_release(dados) is None


def test_deve_verificar_intervalo_de_24h():
    assert vv.deve_verificar({}, AGORA)  # nunca verificou
    recente = (AGORA - timedelta(hours=3)).isoformat()
    antiga = (AGORA - timedelta(hours=25)).isoformat()
    futura = (AGORA + timedelta(days=2)).isoformat()  # relógio do PC voltou no tempo
    assert not vv.deve_verificar({"ultima_verificacao_versao": recente}, AGORA)
    assert vv.deve_verificar({"ultima_verificacao_versao": antiga}, AGORA)
    assert vv.deve_verificar({"ultima_verificacao_versao": futura}, AGORA)
    assert vv.deve_verificar({"ultima_verificacao_versao": "lixo"}, AGORA)


def test_deve_verificar_desligado():
    assert not vv.deve_verificar({"verificar_atualizacoes": False}, AGORA)


def test_versao_ignorada_so_vale_na_verificacao_automatica():
    info = vv.ler_release(RELEASE)
    config = {"versao_ignorada": "1.4"}
    assert not vv.deve_avisar(info, "1.3", config)
    assert vv.deve_avisar(info, "1.3", config, manual=True)
    # Versão mais nova que a ignorada volta a ser avisada
    info_15 = vv.ler_release({**RELEASE, "tag_name": "v1.5"})
    assert vv.deve_avisar(info_15, "1.3", config)
    assert not vv.deve_avisar(info, "1.4", {})
    assert not vv.deve_avisar(None, "1.3", {})


class _Resposta:
    def __init__(self, status, dados=None, headers=None):
        self.status_code = status
        self._dados = dados
        self.headers = headers or {}

    def json(self):
        if self._dados is None:
            raise ValueError("sem JSON")
        return self._dados


class _Sessao:
    def __init__(self, resposta):
        self.resposta = resposta
        self.chamadas = []

    def get(self, url, **kwargs):
        self.chamadas.append((url, kwargs))
        if isinstance(self.resposta, Exception):
            raise self.resposta
        return self.resposta


def _usar_sessao(monkeypatch, resposta):
    from core import http
    sessao = _Sessao(resposta)
    monkeypatch.setattr(http, "get_session", lambda: sessao)
    return sessao


def test_consultar_ultima_release(monkeypatch):
    sessao = _usar_sessao(monkeypatch, _Resposta(200, RELEASE))
    assert vv.consultar_ultima_release()["tag"] == "v1.4"
    url, kwargs = sessao.chamadas[0]
    assert url == vv.URL_ULTIMA_RELEASE and kwargs["timeout"] == vv.TIMEOUT
    assert kwargs["headers"]["User-Agent"].startswith("iBirder/")


def test_consultar_sem_release_publicada(monkeypatch):
    _usar_sessao(monkeypatch, _Resposta(404))
    assert vv.consultar_ultima_release() is None


@pytest.mark.parametrize("resposta, trecho", [
    (_Resposta(403, headers={"X-RateLimit-Remaining": "0"}), "limite"),
    (_Resposta(500), "500"),
    (_Resposta(200, None), "inválida"),
    (ConnectionError("rede"), "sem conexão"),
])
def test_consultar_erros_legiveis(monkeypatch, resposta, trecho):
    _usar_sessao(monkeypatch, resposta)
    with pytest.raises(RuntimeError, match=trecho):
        vv.consultar_ultima_release()


# ------------------------------------------------------------------ AppUpdater (sem rede)

@pytest.fixture
def config_em_memoria(monkeypatch):
    from core import config as cfg
    estado = {"verificar_atualizacoes": True, "ultima_verificacao_versao": "", "versao_ignorada": ""}

    def atualizar(**campos):
        estado.update(campos)
        return dict(estado)

    monkeypatch.setattr(cfg, "carregar_config", lambda: dict(estado))
    monkeypatch.setattr(cfg, "atualizar_config", atualizar)
    return estado


def _updater(versao="1.3"):
    pytest.importorskip("PySide6.QtCore")
    from core.updater import AppUpdater
    updater = AppUpdater()
    updater.current_version = versao
    avisos, concluidas = [], []
    updater.app_update_available.connect(avisos.append)
    updater.verificacao_concluida.connect(lambda i, e, m: concluidas.append((i, e, m)))
    return updater, avisos, concluidas


def test_updater_avisa_e_registra_a_verificacao(config_em_memoria):
    updater, avisos, concluidas = _updater()
    updater._on_resultado(vv.ler_release(RELEASE), "", False)
    assert [a["tag"] for a in avisos] == ["v1.4"]
    assert config_em_memoria["ultima_verificacao_versao"]
    assert concluidas[0][1] == ""


def test_updater_falha_de_rede_nao_conta_como_verificada(config_em_memoria):
    updater, avisos, concluidas = _updater()
    updater._on_resultado({}, "sem conexão com o GitHub (ConnectionError)", True)
    assert not avisos and not config_em_memoria["ultima_verificacao_versao"]
    assert concluidas == [({}, "sem conexão com o GitHub (ConnectionError)", True)]


def test_updater_respeita_versao_ignorada(config_em_memoria):
    updater, avisos, _ = _updater()
    updater.ignorar_versao("1.4")
    updater._on_resultado(vv.ler_release(RELEASE), "", False)
    assert not avisos
    updater._on_resultado(vv.ler_release(RELEASE), "", True)  # manual sempre mostra
    assert len(avisos) == 1


def test_updater_nao_consulta_dentro_do_intervalo(config_em_memoria):
    config_em_memoria["ultima_verificacao_versao"] = datetime.now(timezone.utc).isoformat()
    updater, _, _ = _updater()
    assert updater.check_for_updates() is False
    assert updater.worker is None


# ------------------------------------------------------------------ Diálogo (offscreen)

@pytest.fixture
def qapp():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    QtWidgets = pytest.importorskip("PySide6.QtWidgets")
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_dialogo_com_instalador(qapp, monkeypatch):
    from ui.dialogs import nova_versao_dialog as nvd
    abertos = []
    monkeypatch.setattr(nvd.QDesktopServices, "openUrl", lambda url: abertos.append(url.toString()))
    dlg = nvd.DialogoNovaVersao(vv.ler_release(RELEASE), "1.3")
    assert not dlg.btn_baixar.isHidden() and dlg.btn_baixar.isDefault()
    dlg.btn_baixar.click()
    assert dlg.escolha == "baixar" and abertos == ["https://exemplo/Instalador_iBirder_v1.4.exe"]


def test_dialogo_sem_instalador_e_ignorar(qapp):
    from ui.dialogs.nova_versao_dialog import DialogoNovaVersao
    dlg = DialogoNovaVersao(vv.ler_release({**RELEASE, "assets": [], "body": ""}), "1.3")
    assert dlg.btn_baixar.isHidden() and dlg.btn_pagina.isDefault()
    dlg.btn_ignorar.click()
    assert dlg.escolha == "ignorar"
