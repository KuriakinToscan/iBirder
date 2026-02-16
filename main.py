import sys
import ctypes
import platform
import os
import subprocess
import shutil
import atexit
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
import keyring

# Importações Locais
from ui.wizard_config import WizardConfig
from ui.dialogo_atalho import DialogoAtalho
from core.config import carregar_config, salvar_config
from ui.janela_principal import JanelaPrincipal

# Tenta importar o script de setup para criar atalhos
try:
    import setup_atalho
except ImportError:
    setup_atalho = None

# Configuração do AppUserModelID (Apenas Windows)
if platform.system() == "Windows":
    try:
        myappid = 'ibirder.v0.7.0.online'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass 

def limpar_temp():
    """Remove a pasta temporária e seu conteúdo ao fechar."""
    temp_dir = Path(__file__).parent.absolute() / "temp"
    if temp_dir.exists():
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Erro ao limpar temp: {e}") 

def verificar_ambiente_virtual():
    """Verifica se a pasta .venv existe no diretório do projeto."""
    base_path = Path(__file__).parent.absolute()
    venv_path = base_path / ".venv"
    
    if not venv_path.exists():
        app = QApplication.instance() or QApplication(sys.argv)
        from ui.dialogo_aviso import DialogoAviso
        DialogoAviso(
            "Erro de Ambiente", 
            "Ambiente virtual não encontrado.\n\nCertifique-se de que a pasta .venv está presente na pasta do iBirder e execute o setup_ambiente.ps1.", 
            tipo="erro"
        ).exec()
        sys.exit(1)

def verificar_e_criar_atalho():
    """
    Verifica se o atalho existe na Área de Trabalho.
    Respeita a preferência 'pular_pergunta_atalho' (config.json).
    """
    try:
        if platform.system() != "Windows":
            return 

        desktop = Path(os.environ["USERPROFILE"]) / "Desktop"
        atalho_path = desktop / "iBirder.lnk"

        if atalho_path.exists():
            return

        # 1. Verifica preferência config
        config = carregar_config()
        if config.get("pular_pergunta_atalho", False):
            return

        # 2. Pergunta ao usuário
        dialogo = DialogoAtalho()
        resultado = dialogo.exec() 
        
        criar = (resultado == 1)
        nao_perguntar = dialogo.nao_perguntar

        if nao_perguntar:
            config["pular_pergunta_atalho"] = True
            salvar_config(config)

        if criar:
            criar_atalho_windows(atalho_path)

    except Exception as e:
        print(f"Erro ao verificar atalho: {e}")

def criar_atalho_windows(atalho_path):
    """Cria atalho usando PowerShell."""
    if getattr(sys, 'frozen', False): 
        target_exe = sys.executable
        working_dir = str(Path(target_exe).parent)
        arguments = ""
    else: 
        base_path = Path(__file__).parent.absolute()
        pythonw_path = base_path / ".venv" / "Scripts" / "pythonw.exe"
        python_path = base_path / ".venv" / "Scripts" / "python.exe"
        
        if pythonw_path.exists():
            target_exe = str(pythonw_path)
            arguments = f'"{str(base_path / "main.py")}"'
        elif python_path.exists():
            target_exe = str(python_path)
            arguments = f'"{str(base_path / "main.py")}"'
        else:
            target_exe = sys.executable 
            arguments = f'"{str(base_path / "main.py")}"'
            
        working_dir = str(base_path)

    icon_path = str(Path(__file__).parent.absolute() / "assets" / "logo_ave.ico") 

    script = f'''
    $WshShell = New-Object -comObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut("{str(atalho_path)}")
    $Shortcut.TargetPath = "{target_exe}"
    $Shortcut.WorkingDirectory = "{working_dir}"
    $Shortcut.Arguments = '{arguments}'
    $Shortcut.IconLocation = "{icon_path}"
    $Shortcut.Save()
    '''
    
    subprocess.run(["powershell", "-Command", script], capture_output=True)

def detect_dark_mode_windows():
    try:
        import winreg
        registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
        key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return value == 0 
    except:
        return False

def detectar_tema_e_icone():
    """Retorna o nome do ícone baseado no tema."""
    usar_icone_escuro = False 
    try:
        if platform.system() == "Windows":
             if not detect_dark_mode_windows():
                 usar_icone_escuro = True
    except:
        pass

    nome_arquivo = "logo_ave_escuro.png" if usar_icone_escuro else "logo_ave_claro.png"
    base_path = Path(__file__).parent.absolute()
    caminho_absoluto = base_path / "assets" / nome_arquivo
    
    if not caminho_absoluto.exists():
        return "logo_ave.png"
        
    return nome_arquivo

if __name__ == "__main__":
    # 0. Init Logger
    logger = setup_logger()

    app = QApplication(sys.argv)
    
    # 1. Verificação de Ambiente (.venv)
    verificar_ambiente_virtual()
    
    # v0.8.2: Gestão de Pasta Temporária
    temp_dir = Path(__file__).parent.absolute() / "temp"
    temp_dir.mkdir(exist_ok=True)
    atexit.register(limpar_temp_inteligente)
    
    # 2. Configurações Iniciais (Modo Online Fixo)
    config = carregar_config()
    # Força modo online se não estiver
    if config.get("modo_operacao") != "online":
        config["modo_operacao"] = "online"
        config["lembrar_modo"] = True
        salvar_config(config)

    # 3. Validação da Chave Online
    chave = keyring.get_password("iBirder_Gemini_Key", "user")
    if not chave:
        # print("[CONFIG] Chave não encontrada. Abrindo Wizard...")
        wizard = WizardConfig()
        if not wizard.exec():
            pass
    else:
        # v0.7.9: Teste de conexão removido para preservar cota (Tier 1)
        pass

    # 4. Trigger do Atalho
    verificar_e_criar_atalho()

    # 5. Ícone e Estilo
    nome_icone = detectar_tema_e_icone()
    app.setStyle("Fusion")

    # 6. Inicia Janela Principal
    janela = JanelaPrincipal(nome_icone_janela=nome_icone)
    janela.show()

    sys.exit(app.exec())
