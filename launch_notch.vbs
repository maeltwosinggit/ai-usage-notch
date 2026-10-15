' Silent VBScript Launcher for Codenotch Local
' Runs pythonw.exe completely in the background without any console or cmd window.

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

strScriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
strMainScript = fso.BuildPath(strScriptDir, "main.py")

' Run pythonw with main.py in hidden window mode (0 = hide window, False = return immediately)
WshShell.CurrentDirectory = strScriptDir
WshShell.Run "pythonw.exe """ & strMainScript & """", 0, False
