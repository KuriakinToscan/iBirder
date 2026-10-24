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


"""
Logs do iBirder (v1.2).

- Cada execução grava em logs/sessao_AAAA-MM-DD_HH-MM-SS.log (limite de 2 MB por arquivo).
- Ficam apenas os MANTER_LOGS logs de sessão e os MANTER_LOGS relatórios de erro mais recentes.
- Chaves de API e tokens são mascarados antes de qualquer gravação.
- gerar_diagnostico() monta o texto do botão "Copiar diagnóstico" (Ajuda).
"""

import logging
import logging.handlers
import platform
import re
import shutil
import sys
from datetime import datetime

from core.paths import BASE_DIR, APP_DIR, TEMP_DIR, LOGS_DIR, IS_FROZEN

MANTER_LOGS = 5
TAMANHO_MAX = 2 * 1024 * 1024

ARQUIVO_SESSAO = None  # caminho do log da execução atual

# Padrões de segredos que podem aparecer em URLs/cabeçalhos registrados pelas bibliotecas
_PADROES_SEGREDO = [
    (re.compile(r"(key=)[^&\s\"']+", re.I), r"\1***"),
    (re.compile(r"(Bearer\s+)[A-Za-z0-9._\-]+", re.I), r"\1***"),
    (re.compile(r"AIza[0-9A-Za-z_\-]{20,}"), "AIza***"),
    (re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]+"), "***JWT***"),
]


_SEGREDOS = set()  # valores das chaves configuradas (mantidos só em memória)


def atualizar_segredos(cfg=None):
    """Recarrega as chaves configuradas para mascaramento (início e ao salvar configurações)."""
    try:
        if cfg is None:
            from core.config import carregar_config
            cfg = carregar_config()
        _SEGREDOS.clear()
        for campo in ("xc_api_key", "inat_api_token", "google_vision_api_key", "inat_oauth_token"):
            valor = (cfg.get(campo) or "").strip()
            if len(valor) >= 8:
                _SEGREDOS.add(valor)
    except Exception:
        pass


def mascarar_segredos(texto):
    """Remove chaves de API e tokens de um texto (logs e diagnóstico)."""
    for padrao, troca in _PADROES_SEGREDO:
        texto = padrao.sub(troca, texto)
    for valor in _SEGREDOS:
        texto = texto.replace(valor, "***")
    return texto


class FiltroSegredos(logging.Filter):
    def filter(self, record):
        try:
            mensagem = record.getMessage()
        except Exception:
            return True
        limpa = mascarar_segredos(mensagem)
        if limpa != mensagem:
            record.msg, record.args = limpa, None
        return True


def _podar(padrao, manter=MANTER_LOGS):
    """Apaga os arquivos mais antigos que casam com o padrão, mantendo os `manter` mais recentes."""
    arquivos = sorted(LOGS_DIR.glob(padrao), key=lambda p: p.stat().st_mtime, reverse=True)
    for antigo in arquivos[manter:]:
        try:
            antigo.unlink()
        except OSError:
            pass


def setup_logger():
    """Configura o logging do iBirder (arquivo da sessão + console)."""
    global ARQUIVO_SESSAO
    TEMP_DIR.mkdir(exist_ok=True, parents=True)
    LOGS_DIR.mkdir(exist_ok=True, parents=True)

    logger = logging.getLogger()
    if ARQUIVO_SESSAO is not None:
        return logger  # já configurado

    atualizar_segredos()
    ARQUIVO_SESSAO = LOGS_DIR / f"sessao_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    filtro = FiltroSegredos()

    file_handler = logging.handlers.RotatingFileHandler(
        str(ARQUIVO_SESSAO), maxBytes=TAMANHO_MAX, backupCount=1, encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    file_handler.addFilter(filtro)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO)
    stream_handler.addFilter(filtro)

    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    # Bibliotecas muito verbosas (e que registram URLs completas) só a partir de WARNING
    for nome in ("urllib3", "selenium", "WDM", "PIL", "geopy"):
        logging.getLogger(nome).setLevel(logging.WARNING)

    _podar("sessao_*.log")
    logging.info("[BOOT] Sistema de Logging iBirder inicializado em modo UTF-8")
    return logger


def save_crash_log():
    """Copia o log da sessão atual para logs/error_<data>.txt (mantém os 5 mais recentes)."""
    if not ARQUIVO_SESSAO or not ARQUIVO_SESSAO.exists():
        return
    dest_path = LOGS_DIR / f"error_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
    try:
        shutil.copy(ARQUIVO_SESSAO, dest_path)
        logging.info(f"[CRASH] Log salvo em: {dest_path}")
        _podar("error_*.txt")
    except Exception as e:
        sys.stderr.write(f"Falha ao salvar crash log: {e}\n")


def cleanup_session_log():
    """Chamado no atexit: mantém o log da sessão (histórico) e poda os antigos."""
    try:
        _podar("sessao_*.log")
        _podar("sessao_*.log.1")
    except Exception:
        pass


def gerar_diagnostico(linhas_log=300):
    """Texto para suporte: versões, caminhos, configuração (sem segredos) e fim do log atual."""
    from core.config import APP_VERSION, carregar_config
    partes = [
        "=== Diagnóstico iBirder ===",
        f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        f"Versão do app: {APP_VERSION} | Executável: {IS_FROZEN}",
        f"Sistema: {platform.platform()} | Python {platform.python_version()}",
        f"Pasta do app: {APP_DIR}",
        f"Pasta de dados: {BASE_DIR}",
    ]
    try:
        import json
        meta = json.loads((APP_DIR / "assets" / "models" / "model_meta.json").read_text(encoding="utf-8"))
        partes.append(f"Modelo de IA: {meta.get('model_type')} v{meta.get('version')}")
    except Exception as e:
        partes.append(f"Modelo de IA: metadados indisponíveis ({e})")
    try:
        cfg = carregar_config()
        chaves = {c: ("configurada" if (cfg.get(c) or "").strip() else "vazia")
                  for c in ("inat_api_token", "google_vision_api_key", "xc_api_key")}
        partes.append(f"Chaves de API: {chaves}")
    except Exception:
        pass
    for modulo in ("PySide6", "selenium", "ai_edge_litert", "PIL", "numpy"):
        try:
            mod = __import__(modulo)
            partes.append(f"{modulo}: {getattr(mod, '__version__', 'ok')}")
        except Exception as e:
            partes.append(f"{modulo}: AUSENTE ({e.__class__.__name__})")

    partes.append(f"\n=== Últimas {linhas_log} linhas do log ({ARQUIVO_SESSAO.name if ARQUIVO_SESSAO else '-'}) ===")
    try:
        with open(ARQUIVO_SESSAO, encoding="utf-8", errors="replace") as f:
            partes.extend(line.rstrip("\n") for line in f.readlines()[-linhas_log:])
    except Exception as e:
        partes.append(f"(log indisponível: {e})")
    return mascarar_segredos("\n".join(partes))
