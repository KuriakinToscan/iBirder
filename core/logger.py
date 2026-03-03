import logging
import os
import shutil
from pathlib import Path
from datetime import datetime

# Configuração de Caminhos
BASE_DIR = Path(__file__).parent.parent
TEMP_DIR = BASE_DIR / "temp"
LOGS_DIR = BASE_DIR / "logs"
# Arquivo de log temporário da sessão ativa
SESSION_LOG = TEMP_DIR / "session.log"

def setup_logger():
    """
    Configura o sistema de logging do Python para o iBirder.
    - Grava logs detalhados (DEBUG) em temp/session.log para auditoria.
    - Exibe mensagens amigáveis (INFO) no console/terminal.
    - Suporta UTF-8 para nomes de espécies com acentuação.
    """
    TEMP_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)
    
    # Limpa log anterior se existir (nova sessão)
    if SESSION_LOG.exists():
        try:
            os.remove(SESSION_LOG)
        except:
            pass

    # Configuração do formatador
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # Handler para Arquivo (session.log)
    file_handler = logging.FileHandler(str(SESSION_LOG), encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    # Handler para Console (Stream)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO) # Console mostra apenas INFO pra cima

    # Configuração Global
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    
    logging.info("[BOOT] Sistema de Logging iBirder inicializado em modo UTF-8")
    return logger

def save_crash_log():
    """Copia o log da sessão atual para a pasta logs/ com timestamp."""
    if not SESSION_LOG.exists():
        return
        
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"error_{timestamp}.txt"
    dest_path = LOGS_DIR / filename
    
    try:
        shutil.copy(SESSION_LOG, dest_path)
        logging.info(f"[CRASH] Log salvo em: {dest_path}")
    except Exception as e:
        sys.stderr.write(f"Falha ao salvar crash log: {e}\n")

def cleanup_session_log():
    """Remove o log da sessão se não houve erros graves (chamado no atexit)."""
    # A lógica de remover ou não será controlada por uma flag no main
    # Mas aqui oferecemos a função de remoção
    if SESSION_LOG.exists():
        try:
            os.remove(SESSION_LOG)
        except:
            pass
