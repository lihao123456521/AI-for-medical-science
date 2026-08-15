# -*- mode: python ; coding: utf-8 -*-
# PyInstaller onedir spec for the UroPUC backend (entry: run_waitress.py).
# 只打包只读资源：templates/static/公开种子数据。
# 用户数据（病例、文章、uploads、api_config）始终位于 ~/.uscc_scc_flask_data，
# 不进入安装包；.env 与任何私密文件也一律不打包。
import sys
from pathlib import Path

root = Path(SPECPATH).resolve().parent

# 白名单式资源清单：只有列在这里的内容才会进入安装包。
# 用户数据（病例、文章、uploads、api_config）位于 ~/.uscc_scc_flask_data，
# .env 与任何私密文件一律不打包。
datas = [
    (str(root / "templates"), "templates"),
    (str(root / "static"), "static"),
    (str(root / "data" / "seed"), "data/seed"),
    (str(root / "data" / "knowledge_base.xlsx"), "data"),
    (str(root / "data" / "knowledge_base_manifest.json"), "data"),
]

a = Analysis(
    [str(root / "run_waitress.py")],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="UroPUCBackend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # console=False：安装运行时不出现命令行黑框
    console=False,
    icon=str(root / "static" / "assets" / "app_icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="UroPUCBackend",
)
