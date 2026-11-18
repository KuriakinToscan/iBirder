"""
Temas visuais (v1.4; paleta x modo desde a v1.6): toda combinação de paleta e modo define
todos os tokens, com contraste legível (WCAG AA; 7:1 no Alto contraste), e a interface não
usa cor fixa fora dos tokens. Sem Qt para a maior parte dos testes.
"""
import os
import re
from pathlib import Path

import pytest

from core import temas
from core.temas import COMBINACOES, PALETAS, TEMAS, TEMA_PADRAO, TOKENS_COR, TOKENS_NUMERO, TOKENS_TEXTO

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
    ("texto", "hover"), ("texto", "selecao"),  # item sob o mouse e item selecionado nas listas
]

IDS_COMBINACOES = [f"{t.id}-{t.modo}" for t in COMBINACOES]


@pytest.mark.parametrize("tema", COMBINACOES, ids=IDS_COMBINACOES)
def test_tema_define_todos_os_tokens(tema):
    obrigatorios = set(TOKENS_COR) | set(TOKENS_TEXTO) | set(TOKENS_NUMERO)
    assert obrigatorios <= set(tema.tokens), obrigatorios - set(tema.tokens)
    for token in TOKENS_COR:
        assert RE_HEX.match(tema[token]), f"{tema.id}.{token} = {tema[token]!r}"
    for token in TOKENS_NUMERO:
        assert isinstance(tema[token], int) and tema[token] >= 0
    for token in TOKENS_TEXTO:
        assert isinstance(tema[token], str) and tema[token]


@pytest.mark.parametrize("tema", COMBINACOES, ids=IDS_COMBINACOES)
@pytest.mark.parametrize("texto,fundo", PARES_TEXTO)
def test_contraste_minimo(tema, texto, fundo):
    minimo = PALETAS[tema.id].contraste_minimo
    razao = temas.contraste(tema[texto], tema[fundo])
    assert razao >= minimo, f"{tema.id} ({tema.modo}): {texto} sobre {fundo} = {razao:.2f}:1"


@pytest.mark.parametrize("tema", COMBINACOES, ids=IDS_COMBINACOES)
def test_logo_do_tema_existe(tema):
    assert (RAIZ / "assets" / tema.logo).is_file()


@pytest.mark.parametrize("tema", COMBINACOES, ids=IDS_COMBINACOES)
def test_modo_escuro_e_mesmo_escuro(tema):
    """No modo escuro o fundo é escuro e o texto claro (e o contrário no claro)."""
    escuro = temas.luminancia(tema["fundo"]) < temas.luminancia(tema["texto"])
    assert escuro == tema.escuro


def test_obter_tema_cai_no_padrao():
    assert temas.obter_tema("clean").id == "clean"
    assert temas.obter_tema(None).id == TEMA_PADRAO
    assert temas.obter_tema("inexistente").id == TEMA_PADRAO
    assert temas.obter_tema("clean", "escuro").modo == "escuro"
    assert temas.obter_tema("clean", "qualquer").modo == "claro"


def test_paletas_da_v14_continuam_iguais_no_claro():
    """As três paletas da v1.4 não mudaram no modo claro (quem atualiza não vê diferença)."""
    assert TEMAS["offwhite"]["destaque"] == "#374151"
    assert TEMAS["clean"]["selecao"] == "#E3F2EF"
    assert TEMAS["classico"]["fonte_titulo"] == "Georgia"
    assert TEMAS["offwhite"].logo == "logo_ave.svg"


def test_modo_efetivo_e_preferencia():
    assert temas.modo_efetivo("sistema", sistema_escuro=True) == "escuro"
    assert temas.modo_efetivo("sistema", sistema_escuro=False) == "claro"
    assert temas.modo_efetivo("claro", sistema_escuro=True) == "claro"
    assert temas.modo_efetivo("escuro", sistema_escuro=False) == "escuro"
    assert temas.normalizar_preferencia_modo(None) == "sistema"
    assert temas.normalizar_preferencia_modo("roxo") == "sistema"


def test_derivar_tokens_completa_e_respeita_o_declarado():
    base = {"fundo": "#101010", "superficie": "#202020", "borda": "#404040", "texto": "#F0F0F0",
            "texto_secundario": "#C0C0C0", "texto_suave": "#A0A0A0", "destaque": "#80C0FF",
            "link": "#99CCFF"}
    tokens = temas.derivar_tokens(base, "escuro")
    assert set(TOKENS_COR) <= set(tokens)
    assert tokens["link"] == "#99CCFF"           # declarado: fica
    assert tokens["enfase"] == "#80C0FF"         # derivado do destaque
    assert tokens["erro_fundo"] == temas.ESTADOS["escuro"]["erro_fundo"]
    with pytest.raises(ValueError):
        temas.derivar_tokens({"fundo": "#000000"}, "claro")


def test_misturar():
    assert temas.misturar("#000000", "#FFFFFF", 0.5) == "#808080"
    assert temas.misturar("#123456", "#ABCDEF", 0) == "#123456"


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


@pytest.mark.parametrize("tema", COMBINACOES, ids=IDS_COMBINACOES)
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
    modo_original = StyleManager.modo_preferido()
    try:
        StyleManager.apply_theme(app, tema="offwhite", modo="claro")
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

        # Modo escuro fixo: mesma paleta, tokens escuros, e o sinal sai de novo
        StyleManager.apply_theme(app, tema="clean", modo="escuro")
        assert StyleManager.modo_escuro()
        assert StyleManager.modo_preferido() == "escuro"
        assert rotulo.styleSheet() == f"color: {temas.obter_tema('clean', 'escuro')['texto']};"
        assert recebidos[-1] == "clean"
        assert app.palette().window().color().name().upper() == temas.obter_tema("clean", "escuro")["fundo"]
    finally:
        StyleManager.apply_theme(app, tema=tema_original, modo=modo_original)


def test_modo_sistema_segue_o_sistema(monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6.QtWidgets")
    from PySide6.QtWidgets import QApplication
    from core.style_manager import StyleManager

    app = QApplication.instance() or QApplication([])
    tema_original, modo_original = StyleManager.tema_atual().id, StyleManager.modo_preferido()
    try:
        monkeypatch.setattr(StyleManager, "sistema_escuro", staticmethod(lambda: True))
        StyleManager.apply_theme(app, tema="gralha", modo="sistema")
        assert StyleManager.modo_escuro()
        monkeypatch.setattr(StyleManager, "sistema_escuro", staticmethod(lambda: False))
        StyleManager._ao_mudar_modo_do_sistema(app)   # o que o sinal colorSchemeChanged chama
        assert not StyleManager.modo_escuro()
        # Com o modo fixo, a troca no sistema não muda nada
        StyleManager.apply_theme(app, tema="gralha", modo="claro")
        monkeypatch.setattr(StyleManager, "sistema_escuro", staticmethod(lambda: True))
        StyleManager._ao_mudar_modo_do_sistema(app)
        assert not StyleManager.modo_escuro()
    finally:
        StyleManager.apply_theme(app, tema=tema_original, modo=modo_original)


def test_icone_segue_a_cor_do_tema(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6.QtWidgets")
    from PySide6.QtWidgets import QApplication, QPushButton
    from core.style_manager import StyleManager

    app = QApplication.instance() or QApplication([])
    tema_original, modo_original = StyleManager.tema_atual().id, StyleManager.modo_preferido()
    try:
        StyleManager.apply_theme(app, tema="offwhite", modo="claro")
        botao = QPushButton()
        StyleManager.definir_icone(botao, RAIZ / "assets" / "icon_help.svg")
        claro = botao.icon().pixmap(24, 24).toImage()
        StyleManager.apply_theme(app, tema="offwhite", modo="escuro")
        escuro = botao.icon().pixmap(24, 24).toImage()
        assert not botao.icon().isNull()
        assert claro != escuro   # refeito na cor do modo escuro
    finally:
        StyleManager.apply_theme(app, tema=tema_original, modo=modo_original)


def test_interface_compila():
    """A suíte não importa a janela principal (QtWebEngine); ao menos garante a sintaxe."""
    for arquivo in sorted((RAIZ / "ui").rglob("*.py")):
        compile(arquivo.read_text(encoding="utf-8"), str(arquivo), "exec")
