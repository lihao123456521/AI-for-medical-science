from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from tkinter import Tk, Label, Button, StringVar, messagebox


APP_TITLE = "AI罕见病助手"
BASE_DIR = Path(__file__).resolve().parent
LOG_PATH = BASE_DIR / "launcher.log"
DEFAULT_PORT = 5000
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
ICON_PATH = BASE_DIR / "static" / "assets" / "app_icon.ico"


def set_app_user_model_id() -> None:
    if os.name != "nt":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("AI.RareDisease.Assistant")
    except Exception as exc:
        log("AppUserModelID skipped: " + repr(exc))


def log(message: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


def run_command(cmd: list[str], env: dict[str, str] | None = None) -> None:
    log("RUN " + " ".join(cmd))
    result = subprocess.run(
        cmd,
        cwd=BASE_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=CREATE_NO_WINDOW,
    )
    if result.stdout:
        log(result.stdout.strip())
    if result.returncode != 0:
        raise RuntimeError(f"命令执行失败: {' '.join(cmd)}\n\n{result.stdout}")


def find_base_python() -> Path:
    current = Path(sys.executable)
    if current.name.lower() == "pythonw.exe":
        python_exe = current.with_name("python.exe")
        if python_exe.exists():
            return python_exe
    return current


def find_pythonw() -> Path:
    current = Path(sys.executable)
    if current.name.lower() == "pythonw.exe":
        return current
    sibling = current.with_name("pythonw.exe")
    if sibling.exists():
        return sibling
    candidates = [
        Path(r"D:\anaconda\pythonw.exe"),
        Path(os.environ.get("SystemRoot", r"C:\Windows")) / "pyw.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return current


def venv_python() -> Path:
    return BASE_DIR / ".venv" / "Scripts" / "python.exe"


def ensure_env_file() -> None:
    env_path = BASE_DIR / ".env"
    example_path = BASE_DIR / ".env.example"
    if not env_path.exists() and example_path.exists():
        shutil.copy2(example_path, env_path)
        log("Created .env from .env.example")


def ensure_desktop_shortcut() -> None:
    if os.name != "nt":
        return
    desktop = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
    if not desktop.exists():
        return
    shortcut = desktop / "AI罕见病助手.lnk"
    target = find_pythonw()
    arguments = f'"{BASE_DIR / "windows_launcher.pyw"}"'
    icon = str(ICON_PATH if ICON_PATH.exists() else target)
    ps = (
        "$shell=New-Object -ComObject WScript.Shell;"
        f"$lnk=$shell.CreateShortcut('{shortcut}');"
        f"$lnk.TargetPath='{target}';"
        f"$lnk.Arguments='{arguments}';"
        f"$lnk.WorkingDirectory='{BASE_DIR}';"
        "$lnk.Description='AI罕见病助手';"
        f"$lnk.IconLocation='{icon},0';"
        "$lnk.WindowStyle=1;"
        "$lnk.Save();"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
            check=False,
        )
        log("Ensured desktop shortcut: " + str(shortcut))
    except Exception as exc:
        log("Desktop shortcut skipped: " + repr(exc))


def ensure_virtualenv(status: StringVar) -> Path:
    py = venv_python()
    if not py.exists():
        status.set("首次启动：正在创建运行环境...")
        run_command([str(find_base_python()), "-m", "venv", ".venv"])
    return py


def dependencies_ready(py: Path) -> bool:
    code = "import flask, waitress, pandas, openpyxl, docx, openai, fitz"
    result = subprocess.run(
        [str(py), "-c", code],
        cwd=BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=CREATE_NO_WINDOW,
    )
    if result.returncode != 0:
        log("Dependency check failed: " + (result.stdout or "").strip())
    return result.returncode == 0


def ensure_dependencies(py: Path, status: StringVar) -> None:
    if dependencies_ready(py):
        return
    status.set("首次启动：正在安装依赖，请稍等...")
    run_command([str(py), "-m", "pip", "install", "-r", "requirements.txt"])


def health_url(port: int) -> str:
    return f"http://127.0.0.1:{port}/healthz"


def app_url(port: int) -> str:
    return f"http://127.0.0.1:{port}"


def is_health_ok(port: int) -> bool:
    try:
        with urllib.request.urlopen(health_url(port), timeout=1.5) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def is_port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def choose_port() -> int:
    for port in range(DEFAULT_PORT, DEFAULT_PORT + 20):
        if is_health_ok(port):
            return port
        if not is_port_open(port):
            return port
    raise RuntimeError("5000-5019 端口都被占用，无法启动应用。")


def start_server(py: Path, port: int) -> subprocess.Popen:
    env = os.environ.copy()
    env.setdefault("HOST", "127.0.0.1")
    env["PORT"] = str(port)
    ensure_env_file()
    log_file = LOG_PATH.open("a", encoding="utf-8")
    process = subprocess.Popen(
        [str(py), "run_waitress.py"],
        cwd=BASE_DIR,
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        creationflags=CREATE_NO_WINDOW,
    )
    log(f"Started server pid={process.pid} port={port}")
    return process


def wait_for_server(process: subprocess.Popen | None, port: int, timeout_seconds: int = 90) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if is_health_ok(port):
            return
        if process is not None and process.poll() is not None:
            raise RuntimeError("服务启动后立即退出，请查看 launcher.log。")
        time.sleep(1)
    raise RuntimeError("服务启动超时，请查看 launcher.log。")


def find_browser() -> Path | None:
    candidates: list[Path] = []
    for key in ("ProgramFiles", "ProgramFiles(x86)", "LocalAppData"):
        base = os.environ.get(key)
        if not base:
            continue
        candidates.extend(
            [
                Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
                Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe",
            ]
        )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def open_app_window(port: int) -> None:
    url = app_url(port)
    browser = find_browser()
    if browser:
        subprocess.Popen(
            [str(browser), f"--app={url}", "--new-window"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )
    else:
        webbrowser.open(url)
    log("Opened " + url)


def launch(status: StringVar, root: Tk) -> None:
    try:
        LOG_PATH.write_text("", encoding="utf-8")
        status.set("正在准备启动...")
        ensure_desktop_shortcut()
        py = ensure_virtualenv(status)
        ensure_dependencies(py, status)
        port = choose_port()
        process = None
        if not is_health_ok(port):
            status.set("正在启动本地服务...")
            process = start_server(py, port)
        status.set("正在打开应用窗口...")
        wait_for_server(process, port)
        open_app_window(port)
        status.set("已打开 AI 罕见病助手。")
        root.after(1800, root.destroy)
    except Exception as exc:
        log("ERROR " + repr(exc))
        status.set("启动失败，请查看 launcher.log。")
        messagebox.showerror(APP_TITLE, f"{exc}\n\n日志文件：{LOG_PATH}")


def main() -> None:
    if "--check" in sys.argv:
        print(f"base_dir={BASE_DIR}")
        print(f"python={find_base_python()}")
        print(f"venv_python={venv_python()}")
        return

    set_app_user_model_id()
    root = Tk()
    root.title(APP_TITLE)
    if ICON_PATH.exists():
        try:
            root.iconbitmap(str(ICON_PATH))
        except Exception as exc:
            log("Window icon skipped: " + repr(exc))
    root.geometry("420x150")
    root.resizable(False, False)
    status = StringVar(value="正在启动...")
    Label(root, text=APP_TITLE, font=("Microsoft YaHei UI", 15, "bold")).pack(pady=(22, 8))
    Label(root, textvariable=status, font=("Microsoft YaHei UI", 10)).pack(pady=(0, 18))
    Button(root, text="关闭", command=root.destroy, width=10).pack()
    threading.Thread(target=launch, args=(status, root), daemon=True).start()
    root.mainloop()


if __name__ == "__main__":
    main()
