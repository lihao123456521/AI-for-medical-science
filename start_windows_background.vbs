Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
projectDir = fso.GetParentFolderName(WScript.ScriptFullName)
launcher = projectDir & "\windows_launcher.pyw"
pythonw = "D:\anaconda\pythonw.exe"
If fso.FileExists(pythonw) Then
    cmd = """" & pythonw & """ """ & launcher & """"
Else
    pyw = shell.ExpandEnvironmentStrings("%SystemRoot%") & "\pyw.exe"
    If fso.FileExists(pyw) Then
        cmd = """" & pyw & """ -3 """ & launcher & """"
    Else
        cmd = "pythonw """ & launcher & """"
    End If
End If
shell.Run cmd, 1, False
