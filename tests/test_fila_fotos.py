"""Fila de fotos da Mesa de trabalho (core/fila_fotos.py e o painel da fila)."""
import os

import pytest

from core import fila_fotos as ff


def _pasta(tmp_path, nomes):
    for nome in nomes:
        (tmp_path / nome).write_bytes(b"")
    return tmp_path


def test_listar_em_ordem_natural_e_so_imagens(tmp_path):
    _pasta(tmp_path, ["IMG_10.jpg", "IMG_2.JPG", "IMG_1.jpeg", "nota.txt", "b.png", "raw.CR2"])
    (tmp_path / "sub").mkdir()
    nomes = [c.name for c in ff.listar_fotos(tmp_path)]
    assert nomes == ["b.png", "IMG_1.jpeg", "IMG_2.JPG", "IMG_10.jpg"]


def test_pasta_inexistente_da_lista_vazia(tmp_path):
    assert ff.listar_fotos(tmp_path / "nao_existe") == []
    assert len(ff.FilaFotos(tmp_path / "nao_existe")) == 0


def test_proxima_pula_gravadas_e_volta_ao_inicio():
    fila = ff.FilaFotos(caminhos=["a.jpg", "b.jpg", "c.jpg", "d.jpg"])
    assert fila.proxima() == 0  # nada aberto: a primeira pendente
    fila.marcar(1, ff.JA_GRAVADA)
    fila.atual = 0
    assert fila.proxima() == 2
    fila.marcar(2, ff.PULADA)
    assert fila.proxima() == 3
    fila.atual = 3
    assert fila.proxima() == 0  # volta ao início
    fila.marcar(0, ff.GRAVADA)
    assert fila.proxima() is None  # a própria foto de partida não conta


def test_marcar_atualiza_caminho_renomeado():
    fila = ff.FilaFotos(caminhos=["IMG_1.jpg"])
    fila.marcar(0, ff.GRAVADA, caminho="Sabia-laranjeira_20261024.jpg", especie="Turdus rufiventris")
    assert fila.indice_de("Sabia-laranjeira_20261024.jpg") == 0
    assert fila.indice_de("IMG_1.jpg") is None
    with pytest.raises(ValueError):
        fila.marcar(0, "inventada")


def test_resumo():
    fila = ff.FilaFotos(caminhos=["a.jpg", "b.jpg", "c.jpg", "d.jpg"])
    assert fila.resumo() == "0 de 4 gravadas"
    fila.marcar(0, ff.GRAVADA)
    fila.marcar(1, ff.JA_GRAVADA)
    fila.marcar(2, ff.PULADA)
    assert fila.resumo() == "1 de 4 gravadas · 1 já tinha registro · 1 pulada"
    assert ff.FilaFotos().resumo() == "Nenhuma foto na fila"


def test_painel_segue_o_estado_e_avanca_ao_gravar(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6.QtWidgets")
    from PIL import Image
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication

    from ui import estado_identificacao as ei
    from ui.widgets import painel_fila

    QApplication.instance() or QApplication([])
    # Configurações num arquivo temporário (não mexe na pasta lembrada do usuário)
    ini = str(tmp_path / "configuracoes.ini")
    monkeypatch.setattr(painel_fila, "QSettings", lambda *_: QSettings(ini, QSettings.IniFormat))
    for nome in ("IMG_1.jpg", "IMG_2.jpg", "IMG_3.jpg"):
        Image.new("RGB", (40, 30), (90, 120, 60)).save(tmp_path / nome)

    # IMG_2 já tem registro do iBirder
    from modules.step6_persistence import registro_ibirder
    monkeypatch.setattr(registro_ibirder, "ler_registro", lambda c: (
        {"dados": {("Taxonomia", "ScientificName"): "Pitangus sulphuratus"}} if c.name == "IMG_2.jpg" else None))

    estado = ei.EstadoIdentificacao()
    painel = painel_fila.PainelFila(estado)
    painel.show()
    abertas = []

    def abrir(caminho):  # o que a janela faz ao receber abrir_foto
        abertas.append(caminho)
        estado.limpar()
        estado.foto_aberta(caminho)

    painel.abrir_foto.connect(abrir)
    painel.carregar_pasta(tmp_path)
    painel._verificador.wait(5000)
    QApplication.processEvents()

    assert painel.fila.itens[1].situacao == ff.JA_GRAVADA
    assert abertas == [str(tmp_path / "IMG_1.jpg")]  # começa pela primeira pendente
    assert painel.fila.atual == 0 and "Aberta" in painel.lista.item(0).text()
    assert not painel.lista.item(0).icon().isNull()  # miniatura

    # Gravou (e renomeou): marca a foto e abre a próxima pendente, pulando a já gravada
    assert painel.avanca_ao_gravar()
    estado.identificacao_concluida({"nome_cientifico": "Turdus rufiventris", "status_msg": "ok"})
    estado.gravada(str(tmp_path / "Sabia_20261024.jpg"))
    QApplication.processEvents()
    assert painel.fila.itens[0].situacao == ff.GRAVADA
    assert painel.fila.itens[0].caminho.name == "Sabia_20261024.jpg"
    assert "Turdus rufiventris" in painel.lista.item(0).text()
    assert abertas[-1] == str(tmp_path / "IMG_3.jpg") and painel.fila.atual == 2

    # Última pendente: gravar não tem para onde avançar
    assert not painel.avanca_ao_gravar()
    painel.pular()
    assert painel.fila.itens[2].situacao == ff.PULADA
    assert "1 pulada" in painel.lbl_resumo.text()
    painel.close()
