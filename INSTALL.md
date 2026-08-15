# Installation Guide

## Windows

1. Open the [latest release](https://github.com/lihao123456521/AI-for-medical-science/releases/latest).
2. Download `UroPUC-Setup-<version>.exe`.
3. Double-click the installer. It installs a self-contained desktop app; Python and Node.js are not required.
4. Start `UroPUC` from the desktop shortcut or Start menu.

The installer is currently unsigned, so Windows may show an "Unknown publisher" or SmartScreen warning. Verify that the file came from the official Releases page before continuing.

### Legacy Windows ZIP

If a release does not include the installer, download `UroPUC-windows.zip`, extract it, and double-click `UroPUC.exe`. `start_windows_local.bat` remains a fallback.

If Windows blocks script execution, open PowerShell in the extracted folder and run:

```powershell
powershell -ExecutionPolicy Bypass -File run_windows.ps1
```

The Windows launcher is `windows_launcher.pyw`. It creates or reuses `.venv`, installs dependencies if needed, starts the local Flask service, waits for `/healthz`, and opens the chat interface in an app-style browser window.

You can also double-click `install_windows_desktop_shortcut.bat`; it starts the same launcher and refreshes the desktop shortcut.

## macOS

1. Download `AI-for-medical-science-macos.tar.gz`.
2. Extract it.
3. Open Terminal in the extracted folder.
4. Run:

```bash
bash run_mac_linux.sh
```

5. Open `http://127.0.0.1:5000` in your browser.

## Linux

1. Download `AI-for-medical-science-linux.tar.gz`.
2. Extract it.
3. Open a terminal in the extracted folder.
4. Run:

```bash
bash run_mac_linux.sh
```

5. Open `http://127.0.0.1:5000` in your browser.

## Requirements

- The Windows installer has no Python or Node.js requirement.
- Legacy ZIP/TAR packages require Python 3.10 or newer and internet access for the first dependency installation.
- Optional API key if AI-generated summaries are needed.
- Runtime user data is stored outside the app folder by default at `~/.uscc_scc_flask_data`, so added cases and articles survive app updates.

## Medical Safety

This software is for research and demonstration only. It is not a clinical diagnosis, treatment, or emergency decision system.
