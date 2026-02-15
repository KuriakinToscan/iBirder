import sys
from PySide6.QtWidgets import QApplication
from ui.janela_principal import JanelaPrincipal

import ctypes
import winreg

if __name__ == "__main__":
    # Define AppUserModelID para ícone correto na barra de tarefas
    # Alterado para v0.1.2.final para forçar limpeza de cache de ícone do Windows
    myappid = 'ibirder.app_identificacao.v0.1.2.final'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)
    
    # Detecção de Tema do Windows (Dark/Light)
    nome_icone = "logo_ave.png" # Padrão
    try:
        registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
        key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        
        if value == 0: # Dark Mode
            print("[DEBUG] Tema detectado: Escuro - Carregando logo_ave_clara.png")
            nome_icone = "logo_ave_clara.png"
        else: # Light Mode
            print("[DEBUG] Tema detectado: Claro - Carregando logo_ave_escuro.png")
            nome_icone = "logo_ave_escuro.png"
            
        winreg.CloseKey(key)
    except Exception as e:
        print(f"[DEBUG] Erro ao detectar tema: {e} - Usando padrão")

    # Estilo básico para garantir que o tema escuro funcione
    app.setStyle("Fusion")

    janela = JanelaPrincipal(nome_icone_janela=nome_icone)
    janela.show()

    sys.exit(app.exec())
