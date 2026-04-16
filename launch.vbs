Set fs = CreateObject("Scripting.FileSystemObject")
path = fs.GetParentFolderName(WScript.ScriptFullName)

' 관리자 권한이 없으면 UAC 요청 후 재실행
If WScript.Arguments.Length = 0 Then
    Set shell = CreateObject("Shell.Application")
    shell.ShellExecute "wscript.exe", Chr(34) & WScript.ScriptFullName & Chr(34) & " admin", path, "runas", 1
    WScript.Quit
End If

' 관리자 권한으로 실행
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = path
sh.Run "cmd /c git pull", 1, True
sh.Run "python AutogameCentor\Gui.py", 0, False
