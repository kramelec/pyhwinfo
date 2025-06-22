@echo off
chcp 866 >NUL
cd /D "%~dp0"
SET PYTHONUNBUFFERED=TRUE
powershell -command "Start-Process cmd -ArgumentList '/c cd /D %~dp0 && python\python.exe meminfo.py && pause || pause' -Verb runas"
