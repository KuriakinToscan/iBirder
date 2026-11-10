"""config.json: gravação atômica e cópia do arquivo ilegível em vez de apagar as chaves."""
import json

import pytest

from core import config


@pytest.fixture
def caminho(tmp_path, monkeypatch):
    destino = tmp_path / "config.json"
    monkeypatch.setattr(config, "obter_caminho_config", lambda: destino)
    monkeypatch.setattr(config, "config_corrompido", None)
    return destino


def test_salvar_e_carregar(caminho):
    config.salvar_config({"inat_api_token": "abc", "tema": "clean"})
    assert not caminho.with_name("config.json.tmp").exists()
    lido = config.carregar_config()
    assert lido["inat_api_token"] == "abc" and lido["tema"] == "clean"
    assert "layout" in lido  # chaves novas vêm do padrão


def test_aceita_bom_do_bloco_de_notas(caminho):
    caminho.write_bytes(b"\xef\xbb\xbf" + json.dumps({"tema": "classico"}).encode())
    assert config.carregar_config()["tema"] == "classico"
    assert config.config_corrompido is None


@pytest.mark.parametrize("conteudo", [b'{"inat_api_token": "abc"', b"\xff\xfe\x00lixo", b"[1, 2]"])
def test_arquivo_ilegivel_e_guardado_e_nao_sobrescrito(caminho, conteudo):
    caminho.write_bytes(conteudo)
    lido = config.carregar_config()
    assert lido["inat_api_token"] == ""
    copia = caminho.with_name("config.json.corrompido")
    assert copia.read_bytes() == conteudo
    assert config.config_corrompido == copia
    # Salvar depois não apaga a cópia
    config.atualizar_config(tema="clean")
    assert copia.exists() and json.loads(caminho.read_text(encoding="utf-8"))["tema"] == "clean"


def test_copias_nao_se_sobrescrevem(caminho):
    for _ in range(2):
        caminho.write_text("{", encoding="utf-8")
        config.carregar_config()
    assert caminho.with_name("config.json.corrompido").exists()
    assert caminho.with_name("config.json.corrompido-2").exists()
