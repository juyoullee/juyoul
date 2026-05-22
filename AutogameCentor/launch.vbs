Set fs = CreateObject("Scripting.FileSystemObject")
path = fs.GetParentFolderName(WScript.ScriptFullName)

If WScript.Arguments.Count = 0 Then
    Set shell = CreateObject("Shell.Application")
    shell.ShellExecute "wscript.exe", Chr(34) & WScript.ScriptFullName & Chr(34) & " admin", path, "runas", 1
    WScript.Quit
End If

Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = path
sh.Run "cmd /c git pull 2>&1 | findstr /V ""Already up""", 1, True
sh.Run "cmd /c pip install -r requirements.txt -q && echo [OK] packages ready", 1, True
sh.Run "cmd /c python Gui.py 2> error.log || (echo. & echo [ERROR] error.log 파일을 확인하세요 & pause)", 1, False