#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Layouts da janela principal (v1.4). Tema (cores) e layout (arrumação) são escolhas
independentes em Configurações > Aparência; a escolha fica em config.json ("layout").
"""

from ui.layouts.base import PAINEIS_EXTRAS, Layout, Paineis
from ui.layouts.completo import LayoutCompleto
from ui.layouts.ficha import LayoutFicha
from ui.layouts.guiado import LayoutGuiado
from ui.layouts.mesa import LayoutMesa

LAYOUT_PADRAO = "completo"

LAYOUTS = {layout.id: layout for layout in (LayoutCompleto(), LayoutGuiado(), LayoutFicha(), LayoutMesa())}

# Propostas do redesenho ainda em construção: aparecem desativadas nas Configurações
LAYOUTS_PLANEJADOS = ()


def obter_layout(id_layout):
    """Layout pelo identificador; desconhecido ou vazio cai no padrão."""
    return LAYOUTS.get(id_layout or LAYOUT_PADRAO, LAYOUTS[LAYOUT_PADRAO])


__all__ = ["Layout", "Paineis", "PAINEIS_EXTRAS", "LAYOUTS", "LAYOUT_PADRAO", "LAYOUTS_PLANEJADOS", "obter_layout"]
