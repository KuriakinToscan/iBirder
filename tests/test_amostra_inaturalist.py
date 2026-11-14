"""Amostra do iNaturalist para avaliar a IA (tools/amostra_inaturalist.py), com a API simulada."""
import io
import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools import amostra_inaturalist as am  # noqa: E402


def _obs(id_, nome, licenca="cc-by", rank="species"):
    return {"id": id_, "uri": f"https://www.inaturalist.org/observations/{id_}",
            "taxon": {"name": nome, "rank": rank}, "user": {"login": f"u{id_}"},
            "photos": [{"url": f"https://inaturalist-open-data.s3.amazonaws.com/photos/{id_}/square.jpg",
                        "license_code": licenca}]}


def test_url_foto_grande():
    assert am.url_foto_grande("https://x/photos/1/square.jpg") == "https://x/photos/1/large.jpg"
    assert am.url_foto_grande("https://x/photos/1/medium.jpeg?123") == "https://x/photos/1/large.jpeg?123"


def test_parametros_busca():
    p = am.parametros_busca("2023-01-01", 500)
    assert p["place_id"] == "6878" and p["quality_grade"] == "research" and p["iconic_taxa"] == "Aves"
    assert p["id_below"] == "500" and "id_below" not in am.parametros_busca("2023-01-01")


def test_selecionar_respeita_limite_licenca_e_rank():
    contagem = {}
    pagina = [_obs(1, "Pitangus sulphuratus"), _obs(2, "Pitangus sulphuratus"), _obs(3, "Pitangus sulphuratus"),
              _obs(4, "Furnarius rufus", licenca="cc-by-nc-nd"), _obs(5, "Turdus", rank="genus"),
              _obs(6, "Turdus rufiventris")]
    escolhidas = am.selecionar(pagina, 2, contagem)
    assert [e["id"] for e in escolhidas] == [1, 2, 6]
    assert escolhidas[0]["url"].endswith("/large.jpg") and escolhidas[0]["autor"] == "u1"
    assert am.selecionar(pagina, 2, {}, filtro=lambda n: n == "Turdus rufiventris")[0]["id"] == 6


class _Resposta:
    def __init__(self, json_=None, content=b""):
        self._json, self.content = json_, content

    def raise_for_status(self):
        pass

    def json(self):
        return self._json


class _Sessao:
    def __init__(self, paginas):
        self.paginas = list(paginas)
        buffer = io.BytesIO()
        Image.new("RGB", (60, 40), (10, 20, 30)).save(buffer, "JPEG")
        self.jpeg = buffer.getvalue()

    def get(self, url, params=None, timeout=None):
        if url == am.API:
            return _Resposta({"results": self.paginas.pop(0) if self.paginas else []})
        return _Resposta(content=self.jpeg)


def test_baixar_amostra(tmp_path, monkeypatch):
    monkeypatch.setattr(am, "PAUSA_API_S", 0)
    monkeypatch.setattr(am, "PAUSA_FOTO_S", 0)
    sessao = _Sessao([[_obs(9, "Pitangus sulphuratus"), _obs(8, "Furnarius rufus")], [_obs(7, "Turdus rufiventris")]])
    especies = am.baixar_amostra(tmp_path, total=3, sessao=sessao)
    linhas = especies.read_text(encoding="utf-8").strip().splitlines()
    assert linhas[0] == "arquivo;especie" and "inat_7.jpg;Turdus rufiventris" in linhas and len(linhas) == 4
    assert (tmp_path / "inat_9.jpg").exists()
    assert "u8" in (tmp_path / "creditos.csv").read_text(encoding="utf-8-sig")


def test_especies_do_modelo():
    pytest.importorskip("PySide6.QtCore")
    especies = am.especies_do_modelo()
    assert "Pitangus sulphuratus" in especies and "Furnarius rufus" not in especies


class _SessaoInstavel(_Sessao):
    """Derruba a conexão nas ``falhas`` primeiras consultas à API e, depois, em ``cair_apos``."""

    def __init__(self, paginas, falhas=0, cair_apos=None):
        super().__init__(paginas)
        self.falhas, self.cair_apos, self.consultas = falhas, cair_apos, 0

    def get(self, url, params=None, timeout=None):
        import requests
        if url == am.API:
            self.consultas += 1
            if self.falhas > 0 or (self.cair_apos is not None and self.consultas > self.cair_apos):
                self.falhas -= 1
                raise requests.ConnectionError("Remote end closed connection without response")
        return super().get(url, params, timeout)


def _sem_pausas(monkeypatch):
    for nome in ("PAUSA_API_S", "PAUSA_FOTO_S", "ESPERA_INICIAL_S"):
        monkeypatch.setattr(am, nome, 0)


def test_conexao_caida_e_repetida(tmp_path, monkeypatch):
    pytest.importorskip("requests")
    _sem_pausas(monkeypatch)
    sessao = _SessaoInstavel([[_obs(9, "Pitangus sulphuratus")]], falhas=2)
    especies = am.baixar_amostra(tmp_path, total=1, sessao=sessao)
    assert "inat_9.jpg;Pitangus sulphuratus" in especies.read_text(encoding="utf-8")


def test_busca_interrompida_segue_com_o_que_tem(tmp_path, monkeypatch):
    pytest.importorskip("requests")
    _sem_pausas(monkeypatch)
    sessao = _SessaoInstavel([[_obs(9, "Pitangus sulphuratus")], [_obs(8, "Furnarius rufus")]], cair_apos=1)
    especies = am.baixar_amostra(tmp_path, total=5, sessao=sessao)
    linhas = especies.read_text(encoding="utf-8").strip().splitlines()
    assert linhas == ["arquivo;especie", "inat_9.jpg;Pitangus sulphuratus"]


def test_erro_definitivo_nao_e_repetido(monkeypatch):
    requests = pytest.importorskip("requests")
    _sem_pausas(monkeypatch)
    resposta = requests.Response()
    resposta.status_code = 404
    chamadas = []

    class _Sessao404:
        def get(self, url, params=None, timeout=None):
            chamadas.append(url)
            return resposta

    with pytest.raises(requests.HTTPError):
        am.get_com_retentativa(_Sessao404(), "https://x")
    assert len(chamadas) == 1
