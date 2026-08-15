' Скрипт для запуска бота в полностью скрытом фоновом режиме (без окна терминала)
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\1. Work\Hisoblash_bot"
WshShell.Run "D:\1. Work\Hisoblash_bot\.venv\Scripts\pythonw.exe -m app", 0, False
Set WshShell = Nothing
