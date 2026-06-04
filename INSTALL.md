# Installation Guide

## Windows

1. Download `AI-for-medical-science-windows.zip`.
2. Extract the zip file.
3. Double-click `start_windows_local.bat`.
4. The launcher opens the app window automatically; no manual URL entry is needed.

If Windows blocks script execution, open PowerShell in the extracted folder and run:

```powershell
powershell -ExecutionPolicy Bypass -File run_windows.ps1
```

The Windows launcher is `windows_launcher.pyw`. It creates or reuses `.venv`, installs dependencies if needed, starts the local Flask service, waits for `/healthz`, and opens the chat interface in an app-style browser window.

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

- Python 3.10 or newer.
- Internet access for the first dependency installation.
- Optional API key if AI-generated summaries are needed.
- Runtime user data is stored outside the app folder by default at `~/.uscc_scc_flask_data`, so added cases and articles survive app updates.

## Medical Safety

This software is for research and demonstration only. It is not a clinical diagnosis, treatment, or emergency decision system.
