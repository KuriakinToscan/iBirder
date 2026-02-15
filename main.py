import sys
from PySide6.QtWidgets import QApplication
from ui.janela_principal import JanelaPrincipal

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Estilo básico para garantir que o tema escuro funcione
    app.setStyle("Fusion")

    janela = JanelaPrincipal()
    janela.show()

    sys.exit(app.exec())
