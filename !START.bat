@echo off
chcp 866 >NUL
cd /D "%~dp0"
set FN=run.bat
if not exist %FN% (
    echo File %FN% not found!
    exit 1
)
find "<X1>" "%FN%" >nul
if %errorlevel% equ 0 (
    powershell -Command "(gc %FN%) -replace '<X1>', '-V' | sc %FN%"
    powershell -Command "(gc %FN%) -replace '<X2>', 'erb ru' | sc %FN%"
    powershell -Command "(gc %FN%) -replace '<X3>', 'nas' | sc %FN%"
)
call %FN% meminfo.py
