Set fs = CreateObject("Scripting.FileSystemObject")
path = fs.GetParentFolderName(WScript.ScriptFullName)

If WScript.Arguments.Count = 0 Then
    Set shell = CreateObject("Shell.Application")
    shell.ShellExecute "wscript.exe", Chr(34) & WScript.ScriptFullName & Chr(34) & " admin", path, "runas", 1
    WScript.Quit
End If

Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = path
sh.Run "cmd /c git pull", 1, True
sh.Run "python AutogameCentor\Gui.py", 0, False