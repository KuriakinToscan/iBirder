import sys
import os
import platform
import subprocess
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QDir
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
        # Alterado para v0.2.1-fix-icons para forçar limpeza completa de cache
        myappid = 'ibirder.app_identificacao.v0.2.1-fix-icons'
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
        # Uso de QMessageBox customizado para botões em Português
        msg = QMessageBox()
        msg.setWindowTitle("Criar Atalho")
        msg.setText("Notei que você ainda não tem um atalho na Área de Trabalho.")
        msg.setInformativeText("Deseja criar um agora para facilitar o acesso?")
        msg.setIcon(QMessageBox.Question)
        
        btn_sim = msg.addButton("Sim", QMessageBox.YesRole)
        btn_nao = msg.addButton("Não", QMessageBox.NoRole)
        msg.setDefaultButton(btn_sim)
        
        msg.exec()
        
        if msg.clickedButton() == btn_sim:
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
    Detecta se o sistema está em modo escuro ou claro.
    Lógica INVERTIDA para robustez:
    - Se for detectado ESCURO com certeza -> Usa CLARO (para contraste).
    - Se for detectado CLARO com certeza -> Usa ESCURO.
    - Se houver QUALQUER dúivida ou erro -> Usa CLARO (padrão mais seguro).
    """
    sistema = platform.system()
    usar_icone_claro = True # Padrão (Fallback Seguro)

    try:
        if sistema == "Windows":
            import winreg
            try:
                registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
                key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                winreg.CloseKey(key)
                
                # AppsUseLightTheme: 0 = Dark, 1 = Light
                if value == 1:
                    # Sistema CLARO -> Usa ícone ESCURO
                    usar_icone_claro = False
                    print("[SISTEMA] Modo Claro detectado. Aplicando ícone ESCURO.")
                elif value == 0:
                    # Sistema ESCURO -> Usa ícone CLARO
                    usar_icone_claro = True
                    print("[SISTEMA] Modo Escuro detectado. Aplicando ícone CLARO para visibilidade.")
                    
            except Exception:
                pass # Mantém padrão (CLARO)
            
        elif sistema == "Linux":
            try:
                cmd = ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"]
                resultado = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode("utf-8").lower()
                
                if "prefer-dark" in resultado:
                    usar_icone_claro = True
                elif "default" in resultado or "light" in resultado:
                     usar_icone_claro = False
                else:
                    # Fallback GTK
                    cmd_gtk = ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"]
                    resultado_gtk = subprocess.check_output(cmd_gtk, stderr=subprocess.DEVNULL).decode("utf-8").lower()
                    if "dark" in resultado_gtk:
                        usar_icone_claro = True
            except Exception:
                pass # Mantém padrão (CLARO)
                
    except Exception:
        pass # Mantém padrão (CLARO)

    # Retorna o nome do arquivo
    nome_arquivo = "logo_ave_clara.png" if usar_icone_claro else "logo_ave_escuro.png"
    
    # ---------------------------------------------------------
    # CORREÇÃO CRÍTICA: CAMINHO ABSOLUTO PARA O ÍCONE
    # O setWindowIcon às vezes falha com caminhos relativos
    # dependendo do CWD. Vamos forçar absoluto.
    # ---------------------------------------------------------
    base_assets = Path(__file__).parent.absolute() / "assets"
    caminho_absoluto = base_assets / nome_arquivo
    
    # Se o arquivo específico não existir (ex: dev não criou ainda), fallback para original
    if not caminho_absoluto.exists():
        print(f"[AVISO] Ícone {nome_arquivo} não encontrado. Usando original.")
        return "logo_ave.png"
        
    return nome_arquivo

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 1. Verificação de Ambiente (.venv)
    verificar_ambiente_virtual()
    
    # 2. Verifica e oferece criação de atalho
    if not getattr(sys, 'frozen', False):
        verificar_e_criar_atalho()
    
    # Define o ícone com base no tema (retorna nome do arquivo)
    nome_icone = detectar_tema_e_icone()
    
    # Estilo básico
    app.setStyle("Fusion")

    # Passa o nome do ícone. A JanelaPrincipal já lida com caminhos,
    # mas vamos garantir que ela receba o nome correto que validamos.
    janela = JanelaPrincipal(nome_icone_janela=nome_icone)
    janela.show()

    sys.exit(app.exec())
