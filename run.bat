cd /D "%~dp0"
SET PYTHONUNBUFFERED=TRUE

FOR /F "delims=" %%i IN ('python\python.exe run.py') DO SET LASTARG=%%i
powershell -command "Start-Process cmd -ArgumentList '/c cd /D %~dp0 && python\python.exe %1 %2 && pause || pause' %LASTARG%"
