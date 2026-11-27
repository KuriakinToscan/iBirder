import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _qsettings_temporario(tmp_path, monkeypatch):
    """
    O painel da fila guarda a última pasta e as opções no QSettings: nos testes,
    num arquivo temporário, para não mexer nas configurações de quem roda os testes.
    """
    try:
        from PySide6.QtCore import QSettings

        from ui.widgets import painel_fila
    except ImportError:
        return
    ini = str(tmp_path / "qsettings_teste.ini")
    monkeypatch.setattr(painel_fila, "QSettings", lambda *_: QSettings(ini, QSettings.IniFormat))
