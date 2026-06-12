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
from tkinter import Tk, Label, Button, StringVar, messagebox, Canvas, PhotoImage
from tkinter import ttk


APP_TITLE = "AI罕见病助手"
BASE_DIR = Path(__file__).resolve().parent
LOG_PATH = BASE_DIR / "launcher.log"
DEFAULT_PORT = 5000
EXPECTED_BUILD_ID = "2026.06.13-v39"
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
ICON_PATH = BASE_DIR / "static" / "assets" / "app_icon.ico"
ICON_PNG_PATH = BASE_DIR / "static" / "assets" / "app_icon.png"
BG_COLOR = "#eef7f6"
CARD_COLOR = "#ffffff"
TEXT_COLOR = "#163331"
MUTED_COLOR = "#5f7774"
ACCENT_COLOR = "#22a699"


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


def read_health(port: int) -> dict:
    try:
        with urllib.request.urlopen(health_url(port), timeout=1.5) as response:
            if response.status != 200:
                return {}
            import json
            value = json.loads(response.read().decode("utf-8"))
            return value if isinstance(value, dict) else {}
    except (OSError, ValueError, urllib.error.URLError):
        return {}


def is_matching_health(port: int) -> bool:
    health = read_health(port)
    return health.get("status") == "ok" and health.get("build_id") == EXPECTED_BUILD_ID


def is_port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def choose_port() -> int:
    for port in range(DEFAULT_PORT, DEFAULT_PORT + 20):
        if is_matching_health(port):
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
        if is_matching_health(port):
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
        if not is_matching_health(port):
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


def center_window(root: Tk, width: int, height: int) -> None:
    root.update_idletasks()
    x = max(0, (root.winfo_screenwidth() - width) // 2)
    y = max(0, (root.winfo_screenheight() - height) // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")


def build_splash(root: Tk, status: StringVar) -> None:
    root.configure(bg=BG_COLOR)
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure(
        "Splash.Horizontal.TProgressbar",
        troughcolor="#d9eeeb",
        background=ACCENT_COLOR,
        bordercolor="#d9eeeb",
        lightcolor=ACCENT_COLOR,
        darkcolor=ACCENT_COLOR,
    )

    shadow = Canvas(root, width=456, height=236, bg=BG_COLOR, highlightthickness=0)
    shadow.place(x=24, y=26)
    shadow.create_rectangle(8, 8, 448, 228, fill="#dcece9", outline="")

    card = Canvas(root, width=456, height=236, bg=BG_COLOR, highlightthickness=0)
    card.place(x=18, y=18)
    card.create_rectangle(0, 0, 456, 236, fill=CARD_COLOR, outline="#d8ebe7")
    card.create_rectangle(0, 0, 456, 8, fill=ACCENT_COLOR, outline=ACCENT_COLOR)
    card.create_oval(332, -36, 476, 108, fill="#dff6f3", outline="")
    card.create_oval(378, 116, 500, 238, fill="#ffe9df", outline="")

    root._splash_icon = None
    if ICON_PNG_PATH.exists():
        try:
            root._splash_icon = PhotoImage(file=str(ICON_PNG_PATH)).subsample(18, 18)
            Label(root, image=root._splash_icon, bg=CARD_COLOR).place(x=50, y=54)
        except Exception as exc:
            log("Splash image skipped: " + repr(exc))

    Label(root, text=APP_TITLE, bg=CARD_COLOR, fg=TEXT_COLOR, font=("Microsoft YaHei UI", 18, "bold")).place(x=128, y=54)
    Label(root, text="Preparing your local medical assistant", bg=CARD_COLOR, fg=MUTED_COLOR, font=("Microsoft YaHei UI", 10)).place(x=130, y=88)
    Label(root, textvariable=status, bg=CARD_COLOR, fg=TEXT_COLOR, font=("Microsoft YaHei UI", 10, "bold")).place(x=50, y=144)

    progress = ttk.Progressbar(root, mode="indeterminate", length=356, style="Splash.Horizontal.TProgressbar")
    progress.place(x=50, y=176)
    progress.start(12)

    Button(
        root,
        text="Cancel",
        command=root.destroy,
        width=8,
        relief="flat",
        bg="#eef7f6",
        fg=TEXT_COLOR,
        activebackground="#dff6f3",
        activeforeground=TEXT_COLOR,
    ).place(x=368, y=204)


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
    center_window(root, 492, 274)
    root.resizable(False, False)
    status = StringVar(value="正在启动...")
    build_splash(root, status)
    threading.Thread(target=launch, args=(status, root), daemon=True).start()
    root.mainloop()


if __name__ == "__main__":
    main()
