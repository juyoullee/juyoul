Set sh = CreateObject("WScript.Shell")
Set fs = CreateObject("Scripting.FileSystemObject")
path = fs.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = path
sh.Run "cmd /c git pull", 1, True
sh.Run "python AutogameCentor\Gui.py", 0, False
