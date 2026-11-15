"""Arquivos do BioCLIP: lista de espécies, ranking e download conferido (core/model_manager.py)."""
import hashlib
import json

import numpy as np
import pytest

from modules.step1_identity import bioclip


def test_gravar_e_ler_especies(tmp_path):
    caminho = tmp_path / "e.txt"
    bioclip.gravar_especies(caminho, ["Pitangus sulphuratus", "Turdus merula"], [True, False])
    nomes, brasil = bioclip.ler_especies(caminho)
    assert nomes == ["Pitangus sulphuratus", "Turdus merula"] and brasil.tolist() == [True, False]


def test_ranking_so_brasil_e_mundo():
    c = bioclip.ClassificadorBioclip.__new__(bioclip.ClassificadorBioclip)
    c.especies = ["A a", "B b", "C c"]
    c.brasil = np.array([True, False, True])
    c.indices_brasil = np.flatnonzero(c.brasil)
    c.textos = np.eye(3, 4, dtype=np.float32)
    c.escala = 100.0
    emb = np.array([0.1, 0.9, 0.3, 0.0], dtype=np.float32)
    emb /= np.linalg.norm(emb)
    mundo = c.ranking(emb, so_brasil=False)
    assert mundo[0][0] == "B b" and sum(p for _, p in mundo) == pytest.approx(1.0)
    brasil = c.ranking(emb, so_brasil=True)
    assert [n for n, _ in brasil] == ["C c", "A a"] and sum(p for _, p in brasil) == pytest.approx(1.0)


def test_threads_padrao_entre_1_e_4():
    assert 1 <= bioclip.threads_padrao() <= 4


# ------------------------------------------------------------------ download (sem rede)

class _Resposta:
    def __init__(self, dados):
        self.dados = dados

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size):
        for i in range(0, len(self.dados), chunk_size):
            yield self.dados[i:i + chunk_size]


def _gerente(tmp_path, conteudo, sha=None):
    from core.model_manager import ModelManager
    (tmp_path / "bioclip_modelo.json").write_text(json.dumps({
        "url_base": "https://exemplo.invalid/rel/",
        "arquivos": {"bioclip_info.json": {"bytes": len(conteudo),
                                           "sha256": sha or hashlib.sha256(conteudo).hexdigest()}}}),
        encoding="utf-8")
    return ModelManager(tmp_path)


def test_download_conferido(tmp_path, monkeypatch):
    from core import model_manager
    conteudo = b'{"escala_logits": 100}'
    pedidos = []
    monkeypatch.setattr(model_manager.requests, "get", lambda url, **k: pedidos.append(url) or _Resposta(conteudo))
    gerente = _gerente(tmp_path, conteudo)
    assert not gerente.check_resources()
    assert gerente.download_resources()
    assert gerente.check_resources() and pedidos == ["https://exemplo.invalid/rel/bioclip_info.json"]
    assert (gerente.bioclip_dir / "bioclip_info.json").read_bytes() == conteudo
    assert gerente.download_resources() and len(pedidos) == 1  # já presente: não baixa de novo


def test_download_com_sha_errado_e_descartado(tmp_path, monkeypatch):
    from core import model_manager
    conteudo = b"conteudo adulterado"
    monkeypatch.setattr(model_manager.requests, "get", lambda url, **k: _Resposta(conteudo))
    mensagens = []
    gerente = _gerente(tmp_path, conteudo, sha="0" * 64)
    assert not gerente.download_resources(callback=mensagens.append)
    assert not any(gerente.bioclip_dir.iterdir()) and "não confere" in mensagens[-1]


def test_manifesto_do_repositorio():
    from core.model_manager import ModelManager
    dados = ModelManager().manifesto()
    assert dados["url_base"].startswith("https://github.com/KuriakinToscan/iBirder/releases/download/modelo-bioclip-")
    assert set(dados["arquivos"]) == {bioclip.ARQUIVO_MODELO, bioclip.ARQUIVO_TEXTOS, bioclip.ARQUIVO_ESPECIES,
                                      bioclip.ARQUIVO_INFO}
    assert all(len(a["sha256"]) == 64 and a["bytes"] > 0 for a in dados["arquivos"].values())
    assert dados["arquivos"][bioclip.ARQUIVO_MODELO]["bytes"] < 100e6
