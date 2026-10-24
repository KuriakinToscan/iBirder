"""Testes dos logs: rotação, mascaramento de chaves e diagnóstico."""
import logging
import os
import time

import pytest

import core.logger as lg


@pytest.fixture
def logs_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(lg, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(lg, "TEMP_DIR", tmp_path / "temp")
    monkeypatch.setattr(lg, "ARQUIVO_SESSAO", None)
    root = logging.getLogger()
    antes = list(root.handlers)
    yield tmp_path / "logs"
    for h in root.handlers[:]:
        if h not in antes:
            root.removeHandler(h)
            h.close()


def test_mascara_chaves_e_tokens():
    texto = ('POST /v1/images:annotate?key=AIzaSyC3cPFkTjQ4me-htBy5veEsi8Wcrd34iqo HTTP/1.1 | '
             'Authorization: Bearer eyJhbGciOiJIUzUxMiJ9.eyJ1c2VyX2lkIjo5NzMzNDE5fQ.S7wreiCZmW9bWGk')
    limpo = lg.mascarar_segredos(texto)
    assert "AIzaSyC3" not in limpo and "eyJhbGci" not in limpo
    assert "key=***" in limpo and "Bearer ***" in limpo


def test_mascara_chave_configurada(monkeypatch):
    lg.atualizar_segredos({"xc_api_key": "5e485df54249c0435a13", "inat_api_token": "", "google_vision_api_key": ""})
    try:
        assert lg.mascarar_segredos("usando 5e485df54249c0435a13 agora") == "usando *** agora"
    finally:
        lg.atualizar_segredos({})


def test_url_com_chave_registrada_por_biblioteca_sai_mascarada(logs_tmp):
    lg.setup_logger()
    # urllib3 fica em WARNING; simula uma biblioteca registrando a URL com a chave
    logging.getLogger("outra_lib").warning('"POST /v1/images:annotate?key=%s HTTP/1.1" 400', "AIzaSyFAKEFAKEFAKEFAKEFAKE12")
    for h in logging.getLogger().handlers:
        h.flush()
    conteudo = lg.ARQUIVO_SESSAO.read_text(encoding="utf-8")
    assert "AIzaSyFAKE" not in conteudo and "key=***" in conteudo
    assert logging.getLogger("urllib3").level == logging.WARNING


def test_mantem_apenas_os_logs_mais_recentes(logs_tmp):
    logs_tmp.mkdir(parents=True)
    for i in range(8):
        p = logs_tmp / f"sessao_2026-01-0{i + 1}_00-00-00.log"
        p.write_text("x")
        os.utime(p, (time.time() - 1000 + i, time.time() - 1000 + i))
    lg.setup_logger()   # cria o log atual e poda
    restantes = sorted(p.name for p in logs_tmp.glob("sessao_*.log"))
    assert len(restantes) == lg.MANTER_LOGS
    assert lg.ARQUIVO_SESSAO.name in restantes
    assert "sessao_2026-01-01_00-00-00.log" not in restantes


def test_crash_log_e_diagnostico(logs_tmp):
    lg.setup_logger()
    logging.error("falha de teste com token Bearer abcdefghijklmnop1234")
    lg.save_crash_log()
    assert len(list(logs_tmp.glob("error_*.txt"))) == 1
    diag = lg.gerar_diagnostico()
    assert "Versão do app" in diag and "falha de teste" in diag
    assert "abcdefghijklmnop1234" not in diag
