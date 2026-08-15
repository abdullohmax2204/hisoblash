@echo off
chcp 65001 >nul
echo Остановка фонового процесса бота...
taskkill /F /IM pythonw.exe 2>nul
if %errorlevel% equ 0 (
    echo ✅ Бот успешно остановлен.
) else (
    echo ℹ️ Фоновый процесс бота не был найден.
)
timeout /t 2 >nul
