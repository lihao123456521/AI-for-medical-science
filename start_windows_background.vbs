Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
projectDir = fso.GetParentFolderName(WScript.ScriptFullName)
cmd = "cmd /c cd /d """ & projectDir & """ && if not exist .venv\Scripts\python.exe python -m venv .venv && call .venv\Scripts\activate.bat && python -m pip install -r requirements.txt && if not exist .env copy .env.example .env && start """" http://127.0.0.1:5000 && python run_waitress.py"
shell.Run cmd, 0, False
