#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan

import sys
import os
from pathlib import Path

# DETECÇÃO DE AMBIENTE (v1.0.4)
IS_FROZEN = getattr(sys, 'frozen', False)

if IS_FROZEN:
    if os.name == 'nt':
        # Prioridade 1: APPDATA/iBirder
        # Prioridade 2: USERPROFILE/AppData/Roaming/iBirder
        # Prioridade 3: Pasta do Executável (Fallback)
        appdata = os.environ.get("APPDATA")
        if not appdata:
            userprofile = os.environ.get("USERPROFILE")
            if userprofile:
                appdata = os.path.join(userprofile, "AppData", "Roaming")
        
        if appdata:
            BASE_DIR = Path(appdata) / "iBirder"
        else:
            BASE_DIR = Path(sys.executable).parent.absolute()
    else:
        BASE_DIR = Path(sys.executable).parent.absolute()
else:
    # Modo Desenvolvimento: Raiz do projeto (iBirder/)
    BASE_DIR = Path(__file__).parent.parent.absolute()

TEMP_DIR = BASE_DIR / "temp"
LOGS_DIR = BASE_DIR / "logs"
SESSION_LOG = TEMP_DIR / "session.log"

def garantir_diretorios():
    """Cria os diretórios necessários se não existirem."""
    try:
        os.makedirs(str(TEMP_DIR), exist_ok=True)
        os.makedirs(str(LOGS_DIR), exist_ok=True)
        return True
    except Exception as e:
        print(f"[FATAL] Erro ao criar diretórios de dados: {e}")
        return False
