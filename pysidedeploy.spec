[app]
title = Hermes Relay
project_dir = .
input_file = desktop_app.py
exec_directory = .
icon = app.ico

[python]
python_path = .venv\Scripts\python.exe
packages = PySide6,websockets,pyyaml,psutil,lark_oapi,qrcode,Pillow,mss,pyautogui,requests

[qt]
modules = Core,Gui,Widgets
plugins = platforms,styles,imageformats,iconengines
excluded_qml_plugins = all
qml_files = 

[nuitka]
mode = onefile
extra_args = --quiet
	--noinclude-qt-translations
	--lto=yes
	--windows-console-mode=disable
	--windows-icon-from-ico=app.ico
	--company-name=Hermes
	--product-name=Hermes Relay
	--file-version=1.0.0
	--product-version=1.0.0
	--file-description=Hermes Relay Remote Control
