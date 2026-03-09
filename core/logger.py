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

import logging
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime

# Importação central de Caminhos (v1.0.4)
from core.paths import BASE_DIR, TEMP_DIR, LOGS_DIR, SESSION_LOG, IS_FROZEN, garantir_diretorios

def setup_logger():
    """Configura o sistema de logging do Python para o iBirder."""
    # Garante novamente que existem (double-check antes de abrir o handler)
    TEMP_DIR.mkdir(exist_ok=True, parents=True)
    LOGS_DIR.mkdir(exist_ok=True, parents=True)
    
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
