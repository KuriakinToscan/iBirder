#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#
#  Este programa é um software livre: você pode redistribuí-lo e/ou 
#  modificá-lo sob os termos da Licença Pública Geral GNU conforme 
#  publicada pela Free Software Foundation, tanto a versão 3 da 
#  Licença, como (a seu critério) qualquer versão posterior.
#
#  Este programa é distribuído na esperança de que possa ser útil, 
#  mas SEM NENHUMA GARANTIA; sem uma garantia implícita de 
#  ADEQUAÇÃO A QUALQUER MERCADO OU APLICAÇÃO EM PARTICULAR. 
#  Veja a Licença Pública Geral GNU para mais detalhes.
#
#  Você deve ter recebido uma cópia da Licença Pública Geral GNU 
#  junto com este programa. Se não, veja <https://www.gnu.org/licenses/>.

import sys
import ctypes
import platform
import os
import subprocess
import shutil
import atexit
import logging
import json
import traceback
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon

from pathlib import Path

# IMPORTAÇÕES ESSENCIAIS (Sempre Seguras)
# Definidas no escopo global para acesso por todas as funções
from core.paths import BASE_DIR, IS_FROZEN, garantir_diretorios

# BLOQUEIO DE TEMA CHROMIUM (v1.0.8)
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-features=DarkMode"
# from core.wikiaves_worker import WikiAvesWorker # Removed in v0.2.1 migration



# Configuração do AppUserModelID (Apenas Windows)
if platform.system() == "Windows":
    try:
        # ID único para dissociar do ícone do Python
        myappid = 'ibirder.app.visualizacao.v1.0.1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass 

def limpar_temp():
    """Remove a pasta temporária e seu conteúdo ao fechar."""
    temp_dir = BASE_DIR / "temp"
    if temp_dir.exists():
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            logging.error(f"Erro ao limpar temp: {e}") 

def verificar_ambiente_virtual():
    """Verifica se a pasta .venv existe no diretório do projeto (Apenas em desenvolvimento)."""
    if IS_FROZEN:
        return

    venv_path = BASE_DIR / ".venv"
    
    if not venv_path.exists():
        app = QApplication.instance() or QApplication(sys.argv)
        from ui.dialogo_aviso import DialogoAviso
        DialogoAviso(
            "Erro de Ambiente", 
            "Ambiente virtual não encontrado.\n\nCertifique-se de que a pasta .venv está presente na pasta do iBirder e execute o setup_ambiente.ps1.", 
            tipo="erro"
        ).exec()
        sys.exit(1)

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

def salvar_log_desespero(mensagem):
    """Última tentativa de salvar algo se tudo falhar."""
    try:
        paths = [
            Path.home() / "Desktop" / "iBirder_ERROR.txt",
            Path(sys.executable).parent / "FALHA_CRITICA.txt",
            Path("C:/Temp/iBirder_crash.txt")
        ]
        for p in paths:
            try:
                p.parent.mkdir(exist_ok=True, parents=True)
                with open(p, "w", encoding='utf-8') as f:
                    f.write(mensagem)
                return str(p)
            except:
                continue
    except:
        pass
    return None

if __name__ == "__main__":
    try:
        # 0. Checkpoint Zero (v1.0.1)
        print("CHECKPOINT 0: Iniciando interpretador...") 
        
        # 1. Garantia de Pastas
        if not garantir_diretorios():
            print("[FATAL] O iBirder não pôde criar as pastas de dados em %APPDATA%.")
            
        # 2. Init Logger e Diagnóstico Pesado
        from core.logger import setup_logger, save_crash_log, cleanup_session_log
        from core.utils import limpar_temp_inteligente
        from core.config import carregar_config, salvar_config
        
        logger = setup_logger()
        logging.info(f"--- INICIANDO DIAGNÓSTICO iBirder v1.0.1 ---")
        logging.info(f"Frozen: {IS_FROZEN} | SO: {os.name} | Plataforma: {sys.platform}")
        logging.info(f"Diretório Base (Data): {BASE_DIR}")
        
        logging.info("CHECKPOINT 1: Logger pronto. Verificando ambiente...")
        
        # 0. Self-Healing (Apenas em Dev)
        # if not IS_FROZEN:
        #    garantir_dependencias()

        # Checagem de Status da IA
        global AI_ENGINE_STATUS
        AI_ENGINE_STATUS = 'READY'
        try:
            from PIL import Image
            logging.info("PIL importado com sucesso.")
        except ImportError:
            AI_ENGINE_STATUS = 'RESTART_REQUIRED'
            logging.warning("Pillow não encontrado.")

        logging.info("CHECKPOINT 3: Criando QApplication...")
        app = QApplication(sys.argv)
        
        # Ícone global da aplicação (barra de tarefas do Windows)
        if getattr(sys, 'frozen', False):
            icon_path = os.path.join(sys._MEIPASS, 'assets', 'logo_ave.ico')
        else:
            icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'logo_ave.ico')
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
        
        logging.info("CHECKPOINT 4: Verificando ambiente virtual...")
        verificar_ambiente_virtual()
        
        # Gestão de Pasta Temporária
        temp_dir = BASE_DIR / "temp"
        temp_dir.mkdir(exist_ok=True, parents=True)
        atexit.register(cleanup_session_log)
        atexit.register(limpar_temp_inteligente)
        
        logging.info("CHECKPOINT 5: Carregando configurações...")
        config = carregar_config()
        


        logging.info("CHECKPOINT 7: Aplicando temas...")
        from core.style_manager import StyleManager
        dark_mode = StyleManager.detect_dark_mode()
        StyleManager.apply_theme(app, dark_mode=dark_mode)

        logging.info("CHECKPOINT 8: Criando Janela Principal...")
        from ui.janela_principal import JanelaPrincipal
        caminho_inicial = sys.argv[1] if len(sys.argv) > 1 else None
        janela = JanelaPrincipal(ai_status=AI_ENGINE_STATUS, imagem_inicial=caminho_inicial)
        
        logging.info("CHECKPOINT 9: Exibindo interface...")
        janela.show()

        logging.info("Finalizado com sucesso. Entrando no loop Qt.")
        sys.exit(app.exec())
        
    except Exception as e:
        error_msg = f"ERRO FATAL NA INICIALIZAÇÃO:\n{str(e)}\n\n{traceback.format_exc()}"
        print(error_msg) # Força no console
        
        # Salva o "log do desespero"
        location = salvar_log_desespero(error_msg)
        
        msg_final = f"O iBirder encontrou um erro crítico e não pôde iniciar.\n\n"
        if location:
            msg_final += f"Um relatório foi salvo em: {location}\n\n"
        msg_final += f"Erro: {str(e)}"

        if 'app' in locals():
            QMessageBox.critical(None, "Erro Crítico iBirder", msg_final)
        else:
            # Fallback para ctypes se o app nem iniciou
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(0, msg_final, "Erro Fatal iBirder", 0x10)
            except:
                pass
            
        sys.exit(1)
