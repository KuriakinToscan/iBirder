"""Avaliação da IA local (tools/avaliar_identificacao.py): estatística e execução de ponta a ponta."""
import importlib.util
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("avaliar_identificacao", RAIZ / "tools" / "avaliar_identificacao.py")
av = importlib.util.module_from_spec(_spec)
sys.modules["avaliar_identificacao"] = av
_spec.loader.exec_module(av)


def test_wilson():
    baixo, alto = av.wilson(80, 100)
    assert baixo == pytest.approx(0.711, abs=0.002) and alto == pytest.approx(0.867, abs=0.002)
    assert av.wilson(0, 0) == (0.0, 0.0)


def test_mcnemar_exato():
    assert av.mcnemar_exato(0, 0) == 1.0
    assert av.mcnemar_exato(5, 5) == 1.0
    assert av.mcnemar_exato(10, 0) == pytest.approx(2 / 1024)


def _r(arquivo, posicao, confianca, modo="borda", conhecida=True):
    return av.Resultado(arquivo, "Turdus rufiventris", modo, [("X y", confianca)], posicao, conhecida)


def test_metricas_e_limiares():
    resultados = [_r("a", 1, 0.9), _r("b", 2, 0.8), _r("c", None, 0.4, conhecida=False), _r("d", 1, 0.5)]
    m = av.calcular_metricas(resultados)
    assert (m.n, m.top1, m.top3, m.conhecidas, m.top1_conhecidas) == (4, 2, 3, 3, 2)
    tabela = dict((t, (aceitas, acertos)) for t, aceitas, acertos in av.analisar_limiares(resultados, [0.3, 0.7, 0.85]))
    assert tabela == {0.3: (4, 2), 0.7: (2, 1), 0.85: (1, 1)}
    assert av.limiar_sugerido(av.analisar_limiares(resultados, [0.3, 0.7, 0.85]), 0.9, minimo_aceitas=1) == 0.85
    assert av.limiar_sugerido(av.analisar_limiares(resultados, [0.3]), 0.9) is None


def test_ranking_por_especie_com_prior():
    rotulos = ["Turdus rufiventris", "Turdus merula", "Turdus merula", "Pitangus sulphuratus"]
    saida = [0.2, 0.5, 0.1, 0.2]
    assert av.ranking_por_especie(rotulos, saida)[0] == ("Turdus merula", 0.5)
    so_brasil = av.ranking_por_especie(rotulos, saida, {"Turdus rufiventris", "Pitangus sulphuratus"})
    assert [nome for nome, _ in so_brasil] == ["Turdus rufiventris", "Pitangus sulphuratus"]
    assert sum(valor for _, valor in so_brasil) == pytest.approx(1.0)


def test_especies_brasil_embarcadas():
    especies = av.especies_brasil()
    assert "Pitangus sulphuratus" in especies and "Turdus merula" not in especies


def test_relatorio_compara_modos_com_a_referencia():
    resultados = []
    for i, (ref_ok, espelho_ok) in enumerate([(True, True), (False, True), (False, True), (True, False)]):
        for modo in av.MODOS:
            ok = espelho_ok if modo == "espelho" else ref_ok
            resultados.append(_r(f"f{i}", 1 if ok else None, 0.8, modo=modo))
    m = {modo: av.calcular_metricas([r for r in resultados if r.modo == modo]) for modo in av.MODOS}
    assert av.comparar_com_referencia(m["espelho"], m["espremida"])[:2] == (2, 1)
    texto = av.montar_relatorio(resultados, {}, 0.9, 1.0, fora_do_brasil=1)
    assert "espelho         |                 2 |                       1" in texto
    assert "não está na lista do Brasil" in texto


def test_especie_canonica():
    pytest.importorskip("PySide6.QtCore")
    assert av.especie_canonica("Rufous Hornero") == "Furnarius rufus"
    assert av.especie_canonica("turdus rufiventris juensis") == "Turdus rufiventris"
    assert av.especie_canonica("Bird") is None


def test_csv_verdade(tmp_path):
    planilha = tmp_path / "especies.csv"
    planilha.write_text("Arquivo;Especie\nC:\\Fotos\\IMG_1.JPG;Furnarius rufus\n;vazio\n", encoding="utf-8-sig")
    assert av.ler_csv_verdade(planilha) == {"img_1.jpg": "Furnarius rufus"}
    errada = tmp_path / "errada.csv"
    errada.write_text("foto,nome\na.jpg,b\n", encoding="utf-8")
    with pytest.raises(ValueError):
        av.ler_csv_verdade(errada)


def test_ponta_a_ponta_com_o_modelo(tmp_path):
    pytest.importorskip("PySide6.QtCore")
    pytest.importorskip("ai_edge_litert")
    from PIL import Image
    pasta = tmp_path / "fotos"
    pasta.mkdir()
    for i, cor in enumerate([(90, 140, 60), (200, 120, 40)]):
        Image.new("RGB", (1200, 800), cor).save(pasta / f"f{i}.jpg")
    (pasta / "sem_especie.jpg").write_bytes((pasta / "f0.jpg").read_bytes())
    planilha = tmp_path / "especies.csv"
    planilha.write_text("arquivo,especie\nf0.jpg,Furnarius rufus\nf1.jpg,Rufous Hornero\n", encoding="utf-8")
    relatorio, por_foto = tmp_path / "r.txt", tmp_path / "p.csv"
    codigo = av.main([str(pasta), "--csv", str(planilha), "--relatorio", str(relatorio), "--saida-csv", str(por_foto)])
    assert codigo == 0
    assert relatorio.read_bytes().startswith(b"\xef\xbb\xbf")  # BOM: acentos certos no PowerShell
    texto = relatorio.read_text(encoding="utf-8-sig")
    assert "modo espremida: o que o app usa" in texto and "Modo espelho+brasil" in texto
    assert "Cada modo x espremida" in texto
    assert "Fotos avaliadas: 2" in texto and "sem espécie conhecida): 1" in texto and "McNemar" in texto
    assert len(por_foto.read_text(encoding="utf-8-sig").strip().splitlines()) == 1 + 2 * len(av.MODOS)
