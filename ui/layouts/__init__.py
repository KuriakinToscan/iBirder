#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Layouts da janela principal (v1.4; redesenho na v1.6). Tema (cores) e layout (arrumação) são
escolhas independentes em Configurações > Aparência; a escolha fica em config.json ("layout").
"""

from core.config import LAYOUTS_RENOMEADOS
from ui.layouts.base import PAINEIS_EXTRAS, Layout, Paineis
from ui.layouts.cartoes import LayoutCartoes
from ui.layouts.completo import LayoutCompleto
from ui.layouts.ficha import LayoutFicha
from ui.layouts.foco import LayoutFoco
from ui.layouts.mesa_luz import LayoutMesaLuz
from ui.layouts.quadro import LayoutQuadro
from ui.layouts.trilha import LayoutTrilha

# Padrão de quem instala agora (v1.6). Quem atualiza mantém o layout salvo; um config.json
# antigo sem a chave "layout" usava o Painel completo (ver core/config.py).
LAYOUT_PADRAO = "trilha"

# Ordem das Configurações: os da v1.6 primeiro, depois os que continuam da v1.4
LAYOUTS = {layout.id: layout for layout in (LayoutTrilha(), LayoutCartoes(), LayoutMesaLuz(),
                                         LayoutQuadro(), LayoutFoco(), LayoutCompleto(),
                                         LayoutFicha())}


def obter_layout(id_layout):
    """
    Layout pelo identificador. Os ids que saíram na v1.6 ("guiado", "mesa") levam ao
    sucessor; desconhecido ou vazio cai no padrão.
    """
    id_layout = LAYOUTS_RENOMEADOS.get(id_layout, id_layout)
    return LAYOUTS.get(id_layout or LAYOUT_PADRAO, LAYOUTS[LAYOUT_PADRAO])


__all__ = ["Layout", "Paineis", "PAINEIS_EXTRAS", "LAYOUTS", "LAYOUT_PADRAO", "obter_layout"]
