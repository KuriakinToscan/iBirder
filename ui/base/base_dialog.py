#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#
#  Este programa é um software livre: você pode redistribuí-lo e/ou 
#  modificá-lo sob os termos da Licença Pública Geral GNU conforme 
#  publicada pela Free Software Foundation, tanto a versão 3 da 
#  Licença, como (a seu critério) qualquer versão posterior.
#
#  Este programa é distribuído na esperança de que possa ser útil, 
#  mas SEM NENHUMA GARANTIA; sem uma garantia implícita de 
#  ADEQUAÇÃO A QUALQUER MERCADO OU APLICAÇÃO EM PARTICULAR. 
#  Veja a Licença Pública Geral GNU para mais detalhes.
#
#  Você deve ter recebido uma cópia da Licença Pública Geral GNU 
#  junto com este programa. Se não, veja <https://www.gnu.org/licenses/>.

import sys
import os
from pathlib import Path
from PySide6.QtWidgets import QDialog, QVBoxLayout
from PySide6.QtGui import QIcon
from core.style_manager import StyleManager

class BaseDialog(QDialog):
    """
    Classe base para todos os diálogos secundários do iBirder.
    Aplica automaticamente o título, margens consistentes, ícone do aplicativo
    e o QSS global via StyleManager.
    
    Os diálogos filhos devem acessar o self.main_layout para adicionar seus widgets,
    em vez de sobrescrever o layout principal do QDialog.
    """
    def __init__(self, title="iBirder", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        
        # 1. Aplicando o Estilo Global Centralizado (v0.3.37)
        self.setStyleSheet(StyleManager.get_global_stylesheet())
        
        # 2. Configurando Icone Oficial Adaptativo (v0.3.43 / v0.3.44.1 - WinReg)
        if StyleManager.detect_dark_mode():
            icon_file = "logo_ave_claro.svg" 
        else:
            icon_file = "logo_ave_escuro.svg"

        icon_path = self._obter_caminho_asset(icon_file)
        if os.path.exists(icon_path):
             self.setWindowIcon(QIcon(icon_path))
             
        # 3. Layout Mestre Padrão Abstrato
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(10)
        
        # 4. Sincronia de Title Bar (v0.6.6)
        StyleManager.setup_window_theme(self)

    def _obter_caminho_asset(self, nome_arquivo):
        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS)
        else:
            base_path = Path(__file__).parent.parent.parent / 'assets'
        return str(base_path / nome_arquivo)
