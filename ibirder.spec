# -*- mode: python ; coding: utf-8 -*-
# Fonte única do build: usado pelo build.ps1 (local) e pelo GitHub Actions.
from PyInstaller.utils.hooks import collect_all

datas = [('assets', 'assets'), ('Geo', 'Geo'), ('guia_do_usuario.md', '.'), ('README.md', '.'), ('manual_apis_nuvem.md', '.')]
binaries = []
hiddenimports = ['PIL._tkinter_finder', 'email', 'email.mime', 'email.mime.multipart', 'email.mime.text', 'email.mime.base', 'email.mime.application']
# selenium: inclui o selenium-manager; ai_edge_litert: runtime da IA local (.pyd e dados)
for pacote in ('selenium', 'ai_edge_litert'):
    tmp_ret = collect_all(pacote)
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# ---------------------------------------------------------------- Instalador menor
# O PyInstaller leva todo o QML e as bibliotecas Qt que os plugins QML usam (3D, Charts,
# Quick Controls...), as traduções do Chromium em ~100 idiomas e as DevTools. O iBirder
# só usa Widgets, WebEngine (mapa), WebChannel e Multimedia (áudio). Lista conferida com
# as dependências reais (ldd/Dependencies) do QtWebEngineProcess e dos módulos usados;
# o autoteste (--smoke-test) do CI valida o executável gerado.
import re

QT_NAO_USADOS = re.compile(
    r'^(lib)?Qt6(3D\w*|Quick3D\w*|QuickControls2\w*|QuickDialogs2\w*|QuickTemplates2|QuickEffects|'
    r'QuickLayouts|QuickParticles|QuickShapes|QuickTest|QuickTimeline\w*|QuickVectorImage\w*|'
    r'Charts\w*|DataVisualization\w*|Graphs\w*|Labs\w*|Location|MultimediaQuick|PdfQuick|'
    r'PositioningQuick|QmlCore|QmlLocalStorage|QmlNetwork|QmlXmlListModel|RemoteObjects\w*|'
    r'Scxml\w*|Sensors\w*|ShaderTools|SpatialAudio|Sql|StateMachine\w*|Test|TextToSpeech|'
    r'WaylandCompositor|WebChannelQuick|WebEngineQuick\w*|WebSockets|WebView\w*)'
    r'(\.dll|\.so[.\d]*)$', re.IGNORECASE)
IDIOMAS_MANTIDOS = ('en-US.pak', 'pt-BR.pak', '_pt_BR.qm', '_en.qm')


# IA local: só o BioCLIP do manifesto (o MobileNetV2 fica no repositório como referência da avaliação)
ARQUIVOS_BIOCLIP = ('bioclip_imagem_int8d.tflite', 'bioclip_textos.npy', 'bioclip_especies.txt', 'bioclip_info.json')


def _descartar(destino):
    partes = destino.replace('\\', '/').split('/')
    nome = partes[-1]
    if partes[:2] == ['assets', 'models']:
        if len(partes) == 3:
            return nome not in ('bioclip_modelo.json', 'LICENCA_BIOCLIP.txt')
        return not (len(partes) == 4 and partes[2] == 'bioclip' and nome in ARQUIVOS_BIOCLIP)
    if 'PySide6' not in partes:
        return False
    if 'qml' in partes:                                   # nenhum QML no app
        return True
    if QT_NAO_USADOS.match(nome):
        return True
    if nome == 'qtwebengine_devtools_resources.pak':
        return True
    if 'translations' in partes and not nome.endswith(IDIOMAS_MANTIDOS):
        return True
    return False


antes = len(a.binaries) + len(a.datas)
a.binaries = [x for x in a.binaries if not _descartar(x[0])]
a.datas = [x for x in a.datas if not _descartar(x[0])]
print(f"[ibirder.spec] {antes - len(a.binaries) - len(a.datas)} arquivos não usados removidos (Qt e modelos)")
_faltando = [n for n in ARQUIVOS_BIOCLIP if not any(d[0].replace('\\', '/') == f'assets/models/bioclip/{n}' for d in a.datas)]
if _faltando:
    raise SystemExit(f"[ibirder.spec] BioCLIP ausente: {_faltando}. Rode antes: python -m core.model_manager")

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='iBirder',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/logo_ave.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='iBirder',
)
