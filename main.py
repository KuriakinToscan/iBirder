import sys
import platform
import subprocess
from PySide6.QtWidgets import QApplication
from ui.janela_principal import JanelaPrincipal

# Configuração do AppUserModelID (Apenas Windows)
if platform.system() == "Windows":
    try:
        import ctypes
        myappid = 'ibirder.app_identificacao.v0.1.4.final'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass # Silencioso em caso de erro

def detectar_tema_e_icone():
    """
    Detecta se o sistema está em modo escuro ou claro de forma silenciosa.
    Retorna o nome do ícone apropriado.
    Em caso de dúvida ou erro, retorna 'logo_ave_clara.png' (melhor contraste geral).
    """
    sistema = platform.system()
    tema_escuro = True # Padrão seguro para maior visibilidade (ícone claro em fundo escuro)

    try:
        if sistema == "Windows":
            import winreg
            try:
                registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
                key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                winreg.CloseKey(key)
                # 0 = Dark Mode, 1 = Light Mode
                if value == 1:
                    tema_escuro = False
            except Exception:
                pass # Mantém o padrão (Escuro/Clara.png) se falhar leitura do registro
            
        elif sistema == "Linux":
            try:
                # Tenta detectar via gsettings (GNOME/Unity)
                cmd = ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"]
                resultado = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode("utf-8").lower()
                
                if "prefer-dark" in resultado:
                    tema_escuro = True
                elif "default" in resultado or "light" in resultado:
                     tema_escuro = False
                else:
                    # Fallback antigo
                    cmd_gtk = ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"]
                    resultado_gtk = subprocess.check_output(cmd_gtk, stderr=subprocess.DEVNULL).decode("utf-8").lower()
                    if "dark" in resultado_gtk:
                        tema_escuro = True
            except Exception:
                pass # Mantém o padrão se falhar
                
    except Exception:
        pass # Silêncio absoluto em erros gerais

    # Seleção final do ícone
    if tema_escuro:
        return "logo_ave_clara.png"
    else:
        return "logo_ave_escuro.png"

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Define o ícone com base no tema
    nome_icone = detectar_tema_e_icone()
    
    # Estilo básico para garantir que o tema escuro funcione bem com Fusion
    app.setStyle("Fusion")

    janela = JanelaPrincipal(nome_icone_janela=nome_icone)
    janela.show()

    sys.exit(app.exec())
