# -*- mode: python ; coding: utf-8 -*-
"""
Hermes Relay - PyInstaller 打包配置
"""

import sys
from pathlib import Path

block_cipher = None

# 项目根目录
root_dir = Path(SPECPATH)

# 数据文件
datas = [
    (str(root_dir / 'config'), 'config'),
    (str(root_dir / 'relay_server' / 'nlp'), 'relay_server/nlp'),
]

# 隐藏导入
hiddenimports = [
    'websockets',
    'websockets.legacy',
    'websockets.legacy.client',
    'websockets.legacy.server',
    'yaml',
    'psutil',
    'lark_oapi',
    'lark_oapi.api',
    'lark_oapi.api.im',
    'lark_oapi.event',
    'lark_oapi.ws',
    'qrcode',
    'PIL',
    'mss',
    'pyautogui',
    'pygetwindow',
    'pytweening',
    'mouseinfo',
    'cv2',
    'numpy',
]

# 排除模块
excludes = [
    'tkinter',
    'matplotlib',
    'scipy',
    'pandas',
]

a = Analysis(
    ['hermes_relay.py'],
    pathex=[str(root_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 服务端可执行文件
server_exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='hermes-relay-server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    icon=None,
)

# Agent 可执行文件
agent_exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='hermes-relay-agent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    icon=None,
)

# 设置向导
setup_exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='hermes-relay-setup',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    icon=None,
)

coll = COLLECT(
    server_exe,
    agent_exe,
    setup_exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='hermes-relay',
)
