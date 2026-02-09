# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['vibration/__main__.py'],
    pathex=['vibration'],
    binaries=[],
    datas=[('icn.ico', '.')],
    hiddenimports=[
        'vibration.core.services',
        'vibration.core.domain',
        'vibration.presentation.views',
        'vibration.presentation.presenters',
        'vibration.presentation.models',
        'vibration.infrastructure',
        'vibration.optimization',
        'numpy',
        'scipy',
        'matplotlib',
        'PyQt5',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CNAVE_Analyzer',
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
    icon='icn.ico',
)
app = BUNDLE(
    exe,
    name='CNAVE_Analyzer.app',
    icon='icn.ico',
    bundle_identifier=None,
)
