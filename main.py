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

# BLOQUEIO DE TEMA CHROMIUM (v0.7.7): Impede que o WebEngine/Windows forcem modo escuro
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-features=DarkMode"

# Importações Locais
from ui.dialogo_atalho import DialogoAtalho
from core.config import carregar_config, salvar_config
from ui.janela_principal import JanelaPrincipal

# Imports do Core
from core.logger import setup_logger, save_crash_log, cleanup_session_log
from core.utils import limpar_temp_inteligente
# from core.wikiaves_worker import WikiAvesWorker # Removed in v0.2.1 migration

# Tenta importar o script de setup para criar atalhos
try:
    import setup_atalho
except ImportError:
    setup_atalho = None

# Configuração do AppUserModelID (Apenas Windows)
if platform.system() == "Windows":
    try:
        # ID único para dissociar do ícone do Python
        myappid = 'ibirder.app.visualizacao.v1.0'
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
            logging.error(f"Erro ao limpar temp: {e}") 

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
        logging.warning(f"Erro ao verificar atalho: {e}")

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


def garantir_dependencias():
    """Verifica e instala dependências críticas automaticamente."""
    libs = {
        'bs4': 'beautifulsoup4',
        'PIL': 'Pillow',
        'requests': 'requests',
        'numpy': 'numpy',
        'selenium': 'selenium',
        'webdriver_manager': 'webdriver-manager',
        'folium': 'folium',
        'geopandas': 'geopandas',
        'geopy': 'geopy',
        'shapely': 'shapely',
        'lxml': 'lxml'
    }
    
    for import_name, package_name in libs.items():
        try:
            __import__(import_name)
        except ImportError:
            logging.warning(f"[AUTO-REPARO] Import {import_name} falhou. Instalando {package_name}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package_name], 
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

import traceback

def exception_hook(exctype, value, tb):
    logging.critical("Exceção não tratada detectada:", exc_info=(exctype, value, tb))
    sys.exit(1)

sys.excepthook = exception_hook

if __name__ == "__main__":
    # 1. Init Logger
    logger = setup_logger()
    logging.info("Iniciando iBirder...")

    # 0. Self-Healing
    garantir_dependencias()

    # Checagem de Status da IA (Pós-Instalação)
    global AI_ENGINE_STATUS
    AI_ENGINE_STATUS = 'READY'
    try:
        from PIL import Image
    except ImportError:
        AI_ENGINE_STATUS = 'RESTART_REQUIRED'
        logging.warning("Pillow não encontrado. IA pode exigir reinicialização.")

    logging.info("Criando QApplication...")
    app = QApplication(sys.argv)
    
    # 1. Verificação de Ambiente (.venv)
    verificar_ambiente_virtual()
    
    # Gestão de Pasta Temporária
    temp_dir = Path(__file__).parent.absolute() / "temp"
    temp_dir.mkdir(exist_ok=True)
    atexit.register(cleanup_session_log)
    atexit.register(limpar_temp_inteligente)
    
    # 2. Configurações
    config = carregar_config()
    
    # 3. Trigger do Atalho
    verificar_e_criar_atalho()

    # 4. Ícone e Estilo (Sincronia Adaptativa v0.6.5)
    from core.style_manager import StyleManager
    dark_mode = StyleManager.detect_dark_mode()
    StyleManager.apply_theme(app, dark_mode=dark_mode)

    # 5. Inicia Janela Principal (Modo Local)
    logging.info("Criando JanelaPrincipal...")
    janela = JanelaPrincipal(ai_status=AI_ENGINE_STATUS)
    
    logging.info("Exibindo janela...")
    janela.show()

    logging.info("Entrando no loop de eventos.")
    sys.exit(app.exec())
