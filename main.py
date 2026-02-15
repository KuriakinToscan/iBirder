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
        # Alterado para v0.2.2.force_icon para forçar limpeza completa de cache E ignorar tema
        myappid = 'ibirder.v0.2.2.force_icon'
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 1. Verificação de Ambiente (.venv)
    verificar_ambiente_virtual()
    
    # 2. Configuração de Ícone FORÇADA (Brute Force)
    # Sem detecção de tema. Sem fallback complexo. Caminho absoluto.
    basedir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(basedir, 'assets', 'logo_ave.png')
    
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    else:
        print(f"[ERRO] Ícone não encontrado em: {icon_path}")

    # 3. Verifica e oferece criação de atalho
    if not getattr(sys, 'frozen', False):
        verificar_e_criar_atalho()
    
    # Estilo básico
    app.setStyle("Fusion")

    # Janela Principal agora carrega o padrão 'logo_ave.png' internamente se não passarmos nada,
    # ou podemos passar explicitamente 'logo_ave.png' para garantir.
    janela = JanelaPrincipal(nome_icone_janela="logo_ave.png")
    janela.show()

    sys.exit(app.exec())
