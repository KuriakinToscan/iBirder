"""
Temas visuais (v1.4): todo tema define todos os tokens, com contraste legível (WCAG AA),
e a interface não usa cor fixa fora dos tokens. Sem Qt para a maior parte dos testes.
"""
import os
import re
from pathlib import Path

import pytest

from core import temas
from core.temas import TEMAS, TEMA_PADRAO, TOKENS_COR, TOKENS_NUMERO, TOKENS_TEXTO

RAIZ = Path(__file__).resolve().parent.parent
RE_HEX = re.compile(r"^#[0-9A-F]{6}$")
RE_HEX_CODIGO = re.compile(r"#[0-9A-Fa-f]{6}\b")

# Cores que codificam dado no mapa (legenda de densidade, alfinete, selo) e não mudam com o tema
CORES_DE_DADO = {
    "map_widget.py": {"#FF0000", "#FFA500", "#FFFF00", "#D63E2A", "#8B1F12", "#EF4444"},
}

# (texto, fundo): pares que precisam de 4,5:1 (WCAG 2.1 AA para texto normal)
PARES_TEXTO = [
    ("texto", "superficie"), ("texto", "superficie_alt"), ("texto", "fundo"),
    ("texto_secundario", "fundo"), ("destaque", "fundo"),  # barra de etapas do Fluxo guiado
    ("texto_secundario", "superficie"), ("texto_secundario", "superficie_alt"),
    ("texto_suave", "superficie"), ("texto_suave", "superficie_alt"),
    ("titulo_sessao", "superficie"), ("titulo_sessao", "fundo"),
    ("texto_destaque", "destaque"), ("texto_destaque", "destaque_hover"),
    ("botao_texto", "botao_fundo"), ("botao_texto", "botao_hover"),
    ("secundario_texto", "secundario_fundo"),
    ("link", "superficie"), ("link", "superficie_alt"), ("link", "selecao"),  # chips de sugestão
    ("alerta_texto", "alerta_fundo"), ("sucesso_texto", "sucesso_fundo"),
    ("erro_texto", "erro_fundo"), ("texto_barra_titulo", "barra_titulo"),
]


@pytest.mark.parametrize("tema", TEMAS.values(), ids=list(TEMAS))
def test_tema_define_todos_os_tokens(tema):
    obrigatorios = set(TOKENS_COR) | set(TOKENS_TEXTO) | set(TOKENS_NUMERO)
    assert obrigatorios <= set(tema.tokens), obrigatorios - set(tema.tokens)
    for token in TOKENS_COR:
        assert RE_HEX.match(tema[token]), f"{tema.id}.{token} = {tema[token]!r}"
    for token in TOKENS_NUMERO:
        assert isinstance(tema[token], int) and tema[token] >= 0
    for token in TOKENS_TEXTO:
        assert isinstance(tema[token], str) and tema[token]


@pytest.mark.parametrize("tema", TEMAS.values(), ids=list(TEMAS))
@pytest.mark.parametrize("texto,fundo", PARES_TEXTO)
def test_contraste_minimo(tema, texto, fundo):
    razao = temas.contraste(tema[texto], tema[fundo])
    assert razao >= 4.5, f"{tema.id}: {texto} sobre {fundo} = {razao:.2f}:1"


@pytest.mark.parametrize("tema", TEMAS.values(), ids=list(TEMAS))
def test_logo_do_tema_existe(tema):
    assert (RAIZ / "assets" / tema.logo).is_file()


def test_obter_tema_cai_no_padrao():
    assert temas.obter_tema("clean").id == "clean"
    assert temas.obter_tema(None).id == TEMA_PADRAO
    assert temas.obter_tema("inexistente").id == TEMA_PADRAO


def test_renderizar():
    tema = TEMAS["clean"]
    saida = temas.renderizar("color: var(--texto); border-radius: var(--raio); x: var(--nao_existe);", tema)
    assert saida == "color: #111827; border-radius: 12px; x: var(--nao_existe);"


def test_contraste_e_cores_dwm():
    assert temas.contraste("#000000", "#FFFFFF") == pytest.approx(21.0)
    assert temas.cor_bgr("#112233") == 0x332211
    assert temas.barra_titulo_escura(TEMAS["offwhite"])
    assert not temas.barra_titulo_escura(TEMAS["clean"])
    assert temas.barra_titulo_escura(TEMAS["classico"])


@pytest.mark.parametrize("tema", TEMAS.values(), ids=list(TEMAS))
def test_qss_global_sem_token_sobrando(tema):
    from core.style_manager import QSS_GLOBAL
    assert "var(--" not in temas.renderizar(QSS_GLOBAL, tema)


def test_interface_sem_cor_fixa():
    """Toda cor da ui/ vem dos tokens; só as cores que codificam dado no mapa são fixas."""
    encontradas = []
    for arquivo in sorted((RAIZ / "ui").rglob("*.py")):
        permitidas = CORES_DE_DADO.get(arquivo.name, set())
        for n, linha in enumerate(arquivo.read_text(encoding="utf-8").splitlines(), 1):
            for cor in RE_HEX_CODIGO.findall(linha):
                if cor.upper() not in permitidas:
                    encontradas.append(f"{arquivo.relative_to(RAIZ)}:{n}: {cor}")
    assert not encontradas, "\n".join(encontradas)


def test_troca_de_tema_reestiliza_widgets():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6.QtWidgets")
    from PySide6.QtWidgets import QApplication, QLabel
    from core.style_manager import StyleManager

    app = QApplication.instance() or QApplication([])
    tema_original = StyleManager.tema_atual().id
    try:
        StyleManager.apply_theme(app, tema="offwhite")
        rotulo = QLabel()
        StyleManager.estilizar(rotulo, "color: var(--texto);")
        StyleManager.definir_texto(rotulo, "<span style='color: var(--link);'>x</span>")
        recebidos = []
        StyleManager.sinal_tema_alterado().connect(recebidos.append)

        StyleManager.apply_theme(app, tema="classico")
        assert rotulo.styleSheet() == "color: #2B2A26;"
        assert "#2E4A3B" in rotulo.text()
        assert recebidos == ["classico"]

        # Texto trocado depois por setText comum não é sobrescrito na próxima troca
        rotulo.setText("outro")
        StyleManager.apply_theme(app, tema="clean")
        assert rotulo.text() == "outro"
        assert rotulo.styleSheet() == "color: #111827;"
    finally:
        StyleManager.apply_theme(app, tema=tema_original)


def test_interface_compila():
    """A suíte não importa a janela principal (QtWebEngine); ao menos garante a sintaxe."""
    for arquivo in sorted((RAIZ / "ui").rglob("*.py")):
        compile(arquivo.read_text(encoding="utf-8"), str(arquivo), "exec")
