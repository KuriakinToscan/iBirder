#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Layouts da janela principal (v1.4; Trilha na v1.6). Tema (cores) e layout (arrumação) são escolhas
independentes em Configurações > Aparência; a escolha fica em config.json ("layout").
"""

from ui.layouts.base import PAINEIS_EXTRAS, Layout, Paineis
from ui.layouts.cartoes import LayoutCartoes
from ui.layouts.completo import LayoutCompleto
from ui.layouts.ficha import LayoutFicha
from ui.layouts.guiado import LayoutGuiado
from ui.layouts.mesa import LayoutMesa
from ui.layouts.trilha import LayoutTrilha

# Padrão de quem instala agora (v1.6). Quem atualiza mantém o layout salvo; um config.json
# antigo sem a chave "layout" usava o Painel completo (ver core/config.py).
LAYOUT_PADRAO = "trilha"

LAYOUTS = {layout.id: layout for layout in (LayoutCompleto(), LayoutGuiado(), LayoutFicha(), LayoutMesa(),
                                         LayoutTrilha(), LayoutCartoes())}

# Layouts da v1.6 ainda em construção (plano de 17/11/2026): aparecem desativados, com
# miniatura, nas Configurações. Cada um sai daqui quando entra em LAYOUTS.
LAYOUTS_PLANEJADOS = (
    ("mesa_luz", "Mesa de luz", "Foto grande no centro, fila numa tira embaixo e a ficha em seções à direita."),
    ("quadro", "Quadro da sessão", "A pasta da saída de campo em colunas: na fila, conferindo agora, gravadas e puladas."),
    ("foco", "Foco", "A foto ocupa a janela; resultado e ficha flutuam sobre ela. Bom para o teclado."),
)


def obter_layout(id_layout):
    """Layout pelo identificador; desconhecido ou vazio cai no padrão."""
    return LAYOUTS.get(id_layout or LAYOUT_PADRAO, LAYOUTS[LAYOUT_PADRAO])


__all__ = ["Layout", "Paineis", "PAINEIS_EXTRAS", "LAYOUTS", "LAYOUT_PADRAO", "LAYOUTS_PLANEJADOS", "obter_layout"]
