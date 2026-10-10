' Скрипт для запуска бота в полностью скрытом фоновом режиме (без окна терминала)
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = scriptDir
WshShell.Run """" & scriptDir & "\.venv\Scripts\pythonw.exe"" -m app", 0, False
Set WshShell = Nothing
Set fso = Nothing
