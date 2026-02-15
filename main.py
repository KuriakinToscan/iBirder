import sys
from PySide6.QtWidgets import QApplication
from ui.janela_principal import JanelaPrincipal

import ctypes

if __name__ == "__main__":
    # Define AppUserModelID para ícone correto na barra de tarefas
    myappid = 'ibirder.app_identificacao.v1'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)
    
    # Estilo básico para garantir que o tema escuro funcione
    app.setStyle("Fusion")

    janela = JanelaPrincipal()
    janela.show()

    sys.exit(app.exec())
