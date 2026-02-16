import logging
import os
import shutil
from pathlib import Path
from datetime import datetime

# Configuração de Caminhos
BASE_DIR = Path(__file__).parent.parent
TEMP_DIR = BASE_DIR / "temp"
LOGS_DIR = BASE_DIR / "logs"
SESSION_LOG = TEMP_DIR / "session.log"

def setup_logger():
    """Configura o logger para gravar em temp/session.log com nível DEBUG."""
    TEMP_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)
    
    # Limpa log anterior se existir (nova sessão)
    if SESSION_LOG.exists():
        try:
            os.remove(SESSION_LOG)
        except:
            pass

    logging.basicConfig(
        filename=str(SESSION_LOG),
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        encoding='utf-8'
    )
    
    logging.info("[INIT] Sessão iniciada")
    return logging.getLogger()

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
        print(f"Falha ao salvar crash log: {e}")

def cleanup_session_log():
    """Remove o log da sessão se não houve erros graves (chamado no atexit)."""
    # A lógica de remover ou não será controlada por uma flag no main
    # Mas aqui oferecemos a função de remoção
    if SESSION_LOG.exists():
        try:
            os.remove(SESSION_LOG)
        except:
            pass
