import sys
import ctypes
import platform
import os
import subprocess
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox, QCheckBox
from PySide6.QtGui import QIcon

# Importações Locais
from ui.janela_principal import JanelaPrincipal
from ui.dialogo_modo import DialogoModo
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

def verificar_ambiente_virtual():
    """Verifica se a pasta .venv existe no diretório do projeto."""
    base_path = Path(__file__).parent.absolute()
    venv_path = base_path / ".venv"
    
    if not venv_path.exists():
        app = QApplication.instance() or QApplication(sys.argv)
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("Erro de Ambiente")
        msg.setText("Ambiente virtual não encontrado.")
        msg.setInformativeText("Certifique-se de que a pasta .venv está presente na pasta do iBirder e execute o setup_ambiente.ps1.")
        msg.exec()
        sys.exit(1)

def verificar_e_criar_atalho():
    """
    Verifica se o atalho existe na Área de Trabalho.
    Se não, pergunta ao usuário se deseja criar.
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
        
        # 2. Pergunta ao usuário
        msg = QMessageBox()
        msg.setWindowTitle("Criar Atalho")
        msg.setText("Deseja criar um atalho do iBirder na sua Área de Trabalho?")
        msg.setIcon(QMessageBox.Question)
        
        btn_sim = msg.addButton("Sim", QMessageBox.YesRole)
        btn_nao = msg.addButton("Não", QMessageBox.NoRole)
        
        # Checkbox "Não perguntar novamente"
        cb_nao_perguntar = QCheckBox("Não perguntar novamente")
        msg.setCheckBox(cb_nao_perguntar)

        msg.exec()

        # Salva preferência se marcado
        if cb_nao_perguntar.isChecked():
            config["pular_pergunta_atalho"] = True
            salvar_config(config)

        if msg.clickedButton() == btn_sim:
            criar_atalho_windows(atalho_path)
            QMessageBox.information(None, "Sucesso", "Atalho criado na Área de Trabalho!")

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
                 print("[SISTEMA] Modo CLARO detectado. Usando ícone ESCURO.")
             else:
                 print("[SISTEMA] Modo ESCURO detectado. Usando ícone CLARO.")
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
        print(f"[SISTEMA] Ícone {nome_arquivo} carregado.")
        
    return nome_arquivo

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 1. Verificação de Ambiente (.venv)
    verificar_ambiente_virtual()
    
    # 2. Configurações Iniciais (Modo & Atalho)
    config = carregar_config()
    modo_inicial = "offline" 
    
    # A) Trigger do Modo (Startup)
    if config.get("lembrar_modo") and config.get("modo_operacao"):
        print(f"[CONFIG] Modo salvo detectado: {config['modo_operacao']}")
        modo_inicial = config["modo_operacao"]
    else:
        print("[CONFIG] Solicitando escolha de modo...") 
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

    # B) Trigger do Atalho
    # Verifica sempre agora, conforme solicitado
    verificar_e_criar_atalho()

    # 3. Ícone e Estilo
    nome_icone = detectar_tema_e_icone()
    app.setStyle("Fusion")

    # 4. Inicia Janela Principal
    janela = JanelaPrincipal(nome_icone_janela=nome_icone, modo_inicial=modo_inicial)
    janela.show()

    sys.exit(app.exec())
