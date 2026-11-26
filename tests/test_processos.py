"""Programas externos rodam sem janela de console no Windows (core/processos.py)."""
import re
import subprocess
from pathlib import Path

from core import processos

RAIZ = Path(__file__).resolve().parent.parent


def test_executar_passa_create_no_window(monkeypatch):
    recebidos = {}
    monkeypatch.setattr(processos, "SEM_JANELA", 0x08000000)
    monkeypatch.setattr(subprocess, "run", lambda args, **kw: recebidos.update(kw) or "ok")
    assert processos.executar(["exiftool", "-ver"], capture_output=True) == "ok"
    assert recebidos["creationflags"] & 0x08000000
    assert recebidos["capture_output"] is True


def test_executar_fora_do_windows_nao_mexe_nos_flags(monkeypatch):
    recebidos = {}
    monkeypatch.setattr(processos, "SEM_JANELA", 0)
    monkeypatch.setattr(subprocess, "run", lambda args, **kw: recebidos.update(kw))
    processos.executar(["x"])
    assert "creationflags" not in recebidos


def test_app_nao_chama_subprocess_direto():
    """Toda chamada do app passa por core.processos (senão a janela cmd volta a piscar)."""
    proibido = re.compile(r"\bsubprocess\.(run|Popen|call|check_call|check_output)\(")
    achados = []
    for pasta in ("core", "modules", "ui"):
        for arquivo in (RAIZ / pasta).rglob("*.py"):
            if arquivo.name == "processos.py":
                continue
            for n, linha in enumerate(arquivo.read_text(encoding="utf-8").splitlines(), 1):
                if proibido.search(linha):
                    achados.append(f"{arquivo.relative_to(RAIZ)}:{n}")
    assert not achados, achados
