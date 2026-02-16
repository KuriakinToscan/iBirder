import sys
import ctypes
import platform
import os
import subprocess
from pathlib import Path
from PySide6.QtWidgets import QApplication, QCheckBox
from PySide6.QtGui import QIcon
import keyring

# Importações Locais
from ui.dialogo_modo import DialogoModo
from ui.wizard_config import WizardConfig
from ui.dialogo_atalho import DialogoAtalho # v0.3.6
from core.config import carregar_config, salvar_config

# Tenta importar o script de setup para criar atalhos
try:
    import setup_atalho
except ImportError:
    setup_atalho = None

# Configuração do AppUserModelID (Apenas Windows)
if platform.system() == "Windows":
    try:
        # Alterado para v0.3.3.startup para forçar reavaliação de cache pelo Windows
        myappid = 'ibirder.v0.3.3.startup_fix'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass 

def verificar_dependencias_ia():
    """
    Verifica se o OpenCV e Numpy estão instalados (v0.6.6).
    Se não, tenta instalar automaticamente via pip.
    """
    try:
        import cv2
        import numpy
        return True
    except ImportError:
        from PySide6.QtWidgets import QProgressDialog, QMessageBox
        from PySide6.QtCore import Qt
        
        dlg = QProgressDialog("Configurando Motor de Visão (OpenCV)...\nIsso levará apenas alguns segundos.", None, 0, 0)
        dlg.setWindowTitle("Configuração Inicial")
        dlg.setWindowModality(Qt.WindowModal)
        dlg.setCancelButton(None)
        dlg.setMinimumDuration(0)
        dlg.show()
        QApplication.processEvents()
        
        try:
            # Instalação silenciosa
            print("[SETUP] Instalando opencv-python-headless numpy...")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "opencv-python-headless", "numpy"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            dlg.close()
            return True
        except Exception as e:
            dlg.close()
            print(f"[ERRO] Falha na auto-instalação: {e}")
            QMessageBox.warning(None, "Aviso de Dependência", "Não foi possível configurar a IA offline automaticamente.\nVerifique sua conexão com a internet para o primeiro acesso.")
            return False

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
    Se não, pergunta ao usuário se deseja criar (Dialogo Customizado v0.3.6).
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

        print("[CONFIG] Solicitando criação de atalho...") 
        
        # 2. Pergunta ao usuário (Dialogo Customizado)
        dialogo = DialogoAtalho()
        resultado = dialogo.exec() # Retorna 1 (Accepted) ou 0 (Rejected)
        
        criar = (resultado == 1)
        nao_perguntar = dialogo.nao_perguntar # Propriedade customizada

        # Salva preferência se marcado
        if nao_perguntar:
            config["pular_pergunta_atalho"] = True
            salvar_config(config)

        if criar:
            criar_atalho_windows(atalho_path)
            # Feedback sutil (ou remover se quiser ser ultra-minimalista)
            # print("[SISTEMA] Atalho criado com sucesso.")

    except Exception as e:
        print(f"Erro ao verificar atalho: {e}")

def criar_atalho_windows(atalho_path):
    """Cria atalho usando PowerShell."""
    
    # Determina o executável Python a ser usado
    if getattr(sys, 'frozen', False): # Se for um executável PyInstaller
        target_exe = sys.executable
        working_dir = str(Path(target_exe).parent)
        arguments = ""
    else: # Se for um script Python
        base_path = Path(__file__).parent.absolute()
        # Tenta encontrar pythonw.exe no venv, senão python.exe
        pythonw_path = base_path / ".venv" / "Scripts" / "pythonw.exe"
        python_path = base_path / ".venv" / "Scripts" / "python.exe"
        
        if pythonw_path.exists():
            target_exe = str(pythonw_path)
            arguments = f'"{str(base_path / "main.py")}"'
        elif python_path.exists():
            target_exe = str(python_path)
            arguments = f'"{str(base_path / "main.py")}"'
        else:
            target_exe = sys.executable # Fallback para o python do sistema
            arguments = f'"{str(base_path / "main.py")}"'
            
        working_dir = str(base_path)

    # Caminho do ícone
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
        return value == 0 # 0 = Dark, 1 = Light
    except:
        return False

def detectar_tema_e_icone():
    """Retorna o nome do ícone baseado no tema."""
    usar_icone_escuro = False 

    try:
        if platform.system() == "Windows":
             # Se for Light Mode (AppsUseLightTheme=1) -> Ícone ESCURO
             # Se for Dark Mode (AppsUseLightTheme=0) -> Ícone CLARO
             if not detect_dark_mode_windows():
                 usar_icone_escuro = True
                 # print("[SISTEMA] Modo CLARO detectado. Usando ícone ESCURO.")
             else:
                 pass
                 # print("[SISTEMA] Modo ESCURO detectado. Usando ícone CLARO.")
    except:
        pass

    # Nome correto do arquivo é logo_ave_claro.png
    nome_arquivo = "logo_ave_escuro.png" if usar_icone_escuro else "logo_ave_claro.png"
    
    base_path = Path(__file__).parent.absolute()
    caminho_absoluto = base_path / "assets" / nome_arquivo
    
    if not caminho_absoluto.exists():
        print(f"[AVISO] Ícone {nome_arquivo} não encontrado. Usando original.")
        return "logo_ave.png"
    else:
        # print(f"[SISTEMA] Ícone {nome_arquivo} carregado.")
        pass
        
    return nome_arquivo

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 1. Verificação de Ambiente (.venv)
    verificar_ambiente_virtual()

    # 1.1 Verificação de Dependências IA (v0.6.6 Auto-Install)
    # Garante que OpenCV exista antes de importar qualquer coisa que o use
    verificar_dependencias_ia()
    
    # 2. Configurações Iniciais (Modo & Atalho)
    config = carregar_config()
    modo_inicial = "offline" 
    
    # A) Trigger do Modo (Startup)
    if config.get("lembrar_modo") and config.get("modo_operacao"):
        print(f"[CONFIG] Modo salvo detectado: {config['modo_operacao']}")
        modo_inicial = config["modo_operacao"]
    else:
        # print("[CONFIG] Solicitando escolha de modo...") 
        dialogo = DialogoModo()
        if dialogo.exec():
            modo_inicial = dialogo.modo_selecionado
            if dialogo.lembrar:
                config["modo_operacao"] = modo_inicial
                config["lembrar_modo"] = True
                salvar_config(config)
        else:
            # Se cancelar, definimos um padrão seguro mas não salvamos
            modo_inicial = "offline"

    # A.1) Validação da Chave Online (Novo v0.3.4)
    # Se o modo escolhido (ou salvo) for Online, verificamos se temos a chave.
    if modo_inicial == "online":
        chave = keyring.get_password("iBirder_Gemini_Key", "user")
        if not chave:
            print("[CONFIG] Chave não encontrada para modo Online via config. Abrindo Wizard...")
            
            # Avisa antes de abrir wizard para não ser muito abrupto?
            # O Wizard já tem intro "Bem-vindo", então direto é ok.
            # Mas vamos garantir que a janela não esteja aberta ainda (estamos antes do show).
            
            wizard = WizardConfig()
            if wizard.exec():
                # Sucesso
                # print("[CONFIG] Chave configurada com sucesso via Wizard startup.")
                pass
            else:
                # Cancelou -> Fallback para Offline
                # print("[CONFIG] Wizard cancelado. Revertendo para Offline.")
                modo_inicial = "offline"
                
                # Se tinha salvo como lembrar online, talvez devêssemos esquecer?
                # Sim, evita loop na próxima vez
                if config.get("modo_operacao") == "online":
                    config["modo_operacao"] = None
                    config["lembrar_modo"] = False
                    salvar_config(config)

    # B) Trigger do Atalho
    # Verifica sempre agora, conforme solicitado
    verificar_e_criar_atalho()

    # 3. Ícone e Estilo
    nome_icone = detectar_tema_e_icone()
    app.setStyle("Fusion")

    # 4. Inicia Janela Principal
    # Importação Tardia para garantir dependências (v0.6.6)
    from ui.janela_principal import JanelaPrincipal
    janela = JanelaPrincipal(nome_icone_janela=nome_icone, modo_inicial=modo_inicial)
    janela.show()

    sys.exit(app.exec())
