@echo off
cd /d %~dp0
rem Starts the app and automatically creates/refreshes the desktop shortcut.
if exist "D:\anaconda\pythonw.exe" (
  start "" "D:\anaconda\pythonw.exe" "%~dp0windows_launcher.pyw"
) else if exist "%SystemRoot%\pyw.exe" (
  start "" "%SystemRoot%\pyw.exe" -3 "%~dp0windows_launcher.pyw"
) else (
  start "" pythonw "%~dp0windows_launcher.pyw"
)
