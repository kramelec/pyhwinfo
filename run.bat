@echo off
chcp 866 >NUL
cd /D "%~dp0"
SET PYTHONUNBUFFERED=TRUE
powershell -command "Start-Process cmd -ArgumentList '/c cd /D %~dp0 && python\python.exe %1 %2 && pause || pause' <X1><X2><X3>"
