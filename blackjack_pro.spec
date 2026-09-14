# blackjack_pro.spec
# ---------------------------------------------------------------------
# Genera BlackjackPro.exe (Windows, un solo archivo, sin ventana de
# consola). Se corre con:
#
#     python -m PyInstaller blackjack_pro.spec --noconfirm
#
# (ver build_exe.bat, que hace esto automaticamente con el .venv del
# proyecto). El resultado queda en dist/BlackjackPro.exe.
#
# Notas de empaquetado:
#   - Todos los graficos (cartas, fichas) y el audio son PROCEDURALES
#     -- se generan en memoria con pygame.draw / numpy, no hay archivos
#     de assets que empaquetar (assets/cards, assets/chips, etc. estan
#     vacios salvo un .gitkeep). Si en el futuro se agregan imagenes o
#     sonidos reales ahi, hay que sumarlos a `datas` mas abajo.
#   - saves/ (perfiles SQLite) NO se empaqueta: se crea solo, al lado
#     del .exe, la primera vez que se juega (ver engine/profile_store.py
#     -- usa una ruta relativa, no depende de donde este el .exe).
#   - numpy se declara como hiddenimport explicito porque el motor de
#     sonido (ui/sounds.py) lo importa de forma un poco indirecta y
#     PyInstaller a veces no lo detecta solo en modo --onefile.
# ---------------------------------------------------------------------

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['numpy'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='BlackjackPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',
)
