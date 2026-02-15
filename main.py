import sys
import os
import platform
import subprocess
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox
from ui.janela_principal import JanelaPrincipal

# Tenta importar o script de setup para criar atalhos
try:
    import setup_atalho
except ImportError:
    setup_atalho = None

# Configuração do AppUserModelID (Apenas Windows)
if platform.system() == "Windows":
    try:
        import ctypes
        myappid = 'ibirder.app_identificacao.v0.1.6.final'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass # Silencioso em caso de erro

def verificar_ambiente_virtual():
    """Verifica se a pasta .venv existe no diretório do projeto."""
    base_path = Path(__file__).parent.absolute()
    venv_path = base_path / ".venv"
    
    if not venv_path.exists():
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("Erro de Ambiente")
        msg.setText("Ambiente virtual não encontrado.")
        msg.setInformativeText("Certifique-se de que a pasta .venv está presente na pasta do iBirder e execute o setup_ambiente.ps1.")
        msg.exec()
        sys.exit(1)

def verificar_e_criar_atalho():
    """Verifica se o atalho existe e oferece para criar."""
    if setup_atalho is None:
        return

    sistema = platform.system()
    base_path = Path(__file__).parent.absolute()
    icon_path = base_path / "assets" / "logo_ave.png"
    
    atalho_existe = False
    atalho_path = None
    
    if sistema == "Windows":
        desktop = Path(os.environ["USERPROFILE"]) / "Desktop"
        atalho_path = desktop / "iBirder.lnk"
        atalho_existe = atalho_path.exists()
    elif sistema == "Linux":
        apps_dir = Path.home() / ".local" / "share" / "applications"
        atalho_path = apps_dir / "ibirder.desktop"
        atalho_existe = atalho_path.exists()
    
    if not atalho_existe:
        resposta = QMessageBox.question(
            None,
            "Criar Atalho",
            "Notei que você ainda não tem um atalho na Área de Trabalho.\nDeseja criar um agora para facilitar o acesso?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if resposta == QMessageBox.Yes:
            try:
                if sistema == "Windows":
                    # Identifica pythonw.exe
                    python_exe = base_path / ".venv" / "Scripts" / "pythonw.exe"
                    if not python_exe.exists():
                         python_exe = base_path / ".venv" / "Scripts" / "python.exe"
                    
                    if python_exe.exists():
                        setup_atalho.create_windows_shortcut(
                            target=str(python_exe),
                            arguments=f'"{str(base_path / "main.py")}"',
                            icon=str(icon_path),
                            shortcut_path=str(atalho_path),
                            working_dir=str(base_path)
                        )
                        QMessageBox.information(None, "Sucesso", "Atalho criado na Área de Trabalho!")
                    
                elif sistema == "Linux":
                    python_exe = base_path / ".venv" / "bin" / "python3"
                    if not python_exe.exists():
                        python_exe = base_path / ".venv" / "bin" / "python"
                        
                    if python_exe.exists():
                        setup_atalho.create_linux_desktop_file(
                            target=str(python_exe),
                            arguments=str(base_path / "main.py"),
                            icon=str(icon_path),
                            working_dir=str(base_path)
                        )
                        QMessageBox.information(None, "Sucesso", "Atalho criado no menu de aplicativos!")
            except Exception as e:
                # Falha silenciosa ou log leve, para não assustar o usuário
                print(f"Erro ao criar atalho: {e}")

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
    
    # 1. Verificação de Ambiente (.venv)
    verificar_ambiente_virtual()
    
    # 2. Verifica e oferece criação de atalho (após QApplication existir para usar QMessageBox)
    # Apenas se não estivermos congelados (exe)
    if not getattr(sys, 'frozen', False):
        verificar_e_criar_atalho()
    
    # Define o ícone com base no tema
    nome_icone = detectar_tema_e_icone()
    
    # Estilo básico para garantir que o tema escuro funcione bem com Fusion
    app.setStyle("Fusion")

    janela = JanelaPrincipal(nome_icone_janela=nome_icone)
    janela.show()

    sys.exit(app.exec())
