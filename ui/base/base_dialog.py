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
        
        # 2. Configurando Icone Oficial (Não deixa a janelinha branca feia do SO)
        icon_path = self._obter_caminho_asset("logo_ave.svg")
        if os.path.exists(icon_path):
             self.setWindowIcon(QIcon(icon_path))
             
        # 3. Layout Mestre Padrão Abstrato
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(10)

    def _obter_caminho_asset(self, nome_arquivo):
        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS)
        else:
            base_path = Path(__file__).parent.parent.parent / 'assets'
        return str(base_path / nome_arquivo)
