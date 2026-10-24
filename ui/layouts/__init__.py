#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Layouts da janela principal (v1.4). Tema (cores) e layout (arrumação) são escolhas
independentes em Configurações > Aparência; a escolha fica em config.json ("layout").
"""

from ui.layouts.base import Layout, Paineis
from ui.layouts.completo import LayoutCompleto

LAYOUT_PADRAO = "completo"

LAYOUTS = {layout.id: layout for layout in (LayoutCompleto(),)}

# Propostas do redesenho ainda em construção: aparecem desativadas nas Configurações
LAYOUTS_PLANEJADOS = (
    ("guiado", "Fluxo guiado", "Uma etapa por vez: foto, identificação, conferência e gravação."),
    ("ficha", "Ficha compacta", "Tudo numa tela só, sem rolagem, com busca rápida de espécies (Ctrl+K)."),
    ("mesa", "Mesa de trabalho", "Uma pasta inteira em fila: grave e vá para a próxima foto."),
)


def obter_layout(id_layout):
    """Layout pelo identificador; desconhecido ou vazio cai no padrão."""
    return LAYOUTS.get(id_layout or LAYOUT_PADRAO, LAYOUTS[LAYOUT_PADRAO])


__all__ = ["Layout", "Paineis", "LAYOUTS", "LAYOUT_PADRAO", "LAYOUTS_PLANEJADOS", "obter_layout"]
