# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

# Force complete collection of all platform-specific and dynamically-loaded modules
# This ensures no sub-driver or plugin is missed on tester machines
hidden_imports = [
    # Application source modules
    'src',
    'src.config',
    'src.core',
    'src.core.config_manager',
    'src.core.actions.voice_output',
    'src.core.hal.audio',
    'src.core.hal.audio_worker',
    'src.core.hal.overlay',
    'src.core.hal.tray',
    'src.core.hal.vision',
    'src.core.reasoning.llm',
    'src.core.reasoning.vlm',
    # Core dependencies
    'google',
    'PIL',
    'mss',
    'cv2',
    'numpy',
    'dotenv',
    'speech_recognition',
    'vosk',
]

# Collect ALL submodules of platform-sensitive packages to prevent silent import
# failures on tester machines where specific drivers may not be auto-detected
hidden_imports += collect_submodules('google.genai')
hidden_imports += collect_submodules('plyer')
hidden_imports += collect_submodules('pyttsx3')
hidden_imports += collect_submodules('pystray')

a = Analysis(
    ['run.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=['plyer.platforms.win.notification', 'pyttsx3.drivers.sapi5', 'pystray._win32', 'speech_recognition'] + collect_submodules('plyer'),
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
    name='ScreenTaskAssistant',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
