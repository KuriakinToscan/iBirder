import sys
import os
import platform
import subprocess
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon
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
        # Alterado para v0.2.3.check para forçar reavaliação de cache pelo Windows
        myappid = 'ibirder.v0.2.3.check'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass 
    
    # Tenta definir novamente com v0.2.4 para limpar cache
    try:
        import ctypes
        myappid = 'ibirder.v0.2.4.final_check'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass 

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
                print(f"Erro ao criar atalho: {e}")

def detectar_tema_e_icone():
    """
    Detecta se o sistema está em modo escuro ou claro.
    Lógica Simplificada e À Prova de Falhas (v0.2.3):
    1. Tenta detectar Light Mode.
    2. Se for LIGHT -> Retorna ícone ESCURO.
    3. Qualquer outra coisa (Dark, Erro, Indefinido) -> Retorna ícone CLARO.
    """
    sistema = platform.system()
    usar_icone_escuro = False # Padrão é False (ou seja, usa CLARO)

    try:
        if sistema == "Windows":
            import winreg
            try:
                registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
                key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                winreg.CloseKey(key)
                
                # AppsUseLightTheme: 1 = Light Mode
                if value == 1:
                    usar_icone_escuro = True
                    print("[SISTEMA] Modo CLARO detectado. Usando ícone ESCURO.")
                else:
                    print("[SISTEMA] Modo ESCURO (ou outro) detectado. Usando ícone CLARO.")
                    
            except Exception:
                pass # Mantém padrão (CLARO)
            
        elif sistema == "Linux":
            try:
                cmd = ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"]
                resultado = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode("utf-8").lower()
                
                if "light" in resultado and "dark" not in resultado:
                     usar_icone_escuro = True
                     
            except Exception:
                pass # Mantém padrão (CLARO)
                
    except Exception:
        pass # Mantém padrão (CLARO)

    # Retorna o nome do arquivo
    # CORREÇÃO v0.2.4: Nome correto do arquivo é logo_ave_claro.png (masculino)
    nome_arquivo = "logo_ave_escuro.png" if usar_icone_escuro else "logo_ave_claro.png"
    
    # Validação de caminho absoluto para setWindowIcon
    # Usa os.path.join e abspath para garantia total no Windows
    basedir = os.path.dirname(os.path.abspath(__file__))
    caminho_absoluto = os.path.join(basedir, "assets", nome_arquivo)
    
    if not os.path.exists(caminho_absoluto):
        print(f"[AVISO] Ícone {nome_arquivo} não encontrado em {caminho_absoluto}. Usando original.")
        return "logo_ave.png"
    else:
        print(f"[SISTEMA] Ícone {nome_arquivo} carregado com sucesso.")
        
    return nome_arquivo

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 1. Verificação de Ambiente (.venv)
    verificar_ambiente_virtual()
    
    # 2. Configuração de Ícone Dinâmico
    nome_icone = detectar_tema_e_icone()
    
    # 3. Verifica e oferece criação de atalho
    if not getattr(sys, 'frozen', False):
        verificar_e_criar_atalho()
    
    # Estilo básico
    app.setStyle("Fusion")

    # Passa o nome do ícone dinâmico.
    janela = JanelaPrincipal(nome_icone_janela=nome_icone)
    janela.show()

    sys.exit(app.exec())
