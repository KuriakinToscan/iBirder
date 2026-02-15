import sys
import platform
import subprocess
from PySide6.QtWidgets import QApplication
from ui.janela_principal import JanelaPrincipal

# Configuração do AppUserModelID (Apenas Windows)
if platform.system() == "Windows":
    try:
        import ctypes
        myappid = 'ibirder.app_identificacao.v0.1.2.final'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception as e:
        print(f"[DEBUG] Erro ao definir AppUserModelID: {e}")

def detectar_tema_e_icone():
    """
    Detecta se o sistema está em modo escuro ou claro.
    Retorna o nome do ícone apropriado.
    """
    sistema = platform.system()
    tema_escuro = False # Assume claro inicialmente, mas fallback final é 'clara.png' (para fundo escuro) se der erro
    
    print(f"[DEBUG] Detectando tema para SO: {sistema}")

    try:
        if sistema == "Windows":
            import winreg
            registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            
            # 0 = Dark Mode, 1 = Light Mode
            tema_escuro = (value == 0)
            
        elif sistema == "Linux":
            # Tenta detectar via gsettings (GNOME/Unity)
            try:
                # Verifica color-scheme (prefer-dark)
                cmd = ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"]
                resultado = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode("utf-8").lower()
                
                if "prefer-dark" in resultado:
                    tema_escuro = True
                else:
                    # Fallback antigo: verifica gtk-theme se tem 'dark' no nome
                    cmd_gtk = ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"]
                    resultado_gtk = subprocess.check_output(cmd_gtk, stderr=subprocess.DEVNULL).decode("utf-8").lower()
                    if "dark" in resultado_gtk:
                        tema_escuro = True
                        
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("[DEBUG] Falha ao executar gsettings ou comando não encontrado.")
                # Em caso de dúvida no Linux, muitas distros usam dark themes por padrão em terminais/barras
                tema_escuro = True 

    except Exception as e:
        print(f"[DEBUG] Erro genérico na detecção de tema: {e}")
        # Fallback Universal pedido pelo usuário: logo_ave_clara.png
        return "logo_ave_clara.png"

    if tema_escuro:
        print("[DEBUG] Tema detectado: Escuro - Carregando logo_ave_clara.png")
        return "logo_ave_clara.png"
    else:
        print("[DEBUG] Tema detectado: Claro - Carregando logo_ave_escuro.png")
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
