import sys
import os
from PyInstaller.utils.hooks import collect_submodules

sys.path.append(os.path.abspath('.'))
block_cipher = None

added_files = [
    ('assets', 'assets'),
    ('config.json', '.'),
    ('guia_do_usuario.md', '.'),
]

hidden_modules = collect_submodules('modules') + collect_submodules('core') + collect_submodules('ui')

a = Analysis(
    ['main.py'],
    pathex=[os.path.abspath('.')],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'modules.step1_identity',
        'modules.step2_biology',
        'modules.step3_geography',
        'modules.step4_vocalization',
        'modules.step5_taxonomy',
        'modules.step6_persistence',
        'PIL._tkinter_finder',
        'PySide6.QtWebEngineWidgets',
        'email',
        'email.mime',
        'email.mime.multipart',
        'email.mime.text',
        'email.mime.base',
        'email.mime.application'
    ] + hidden_modules,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'pydoc'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='iBirder',
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets\\logo_ave.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='iBirder',
)
