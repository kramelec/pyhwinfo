cd /D "%~dp0"

SET PYTHONUNBUFFERED=TRUE

if not exist pslastarg.txt (
    echo File pslastarg.txt not found!
    python\python.exe -c "with open('pslastarg.txt', 'w') as file: file.write('-' + 'Ver' + 'b    r' + 'un')"
    echo "as" >> pslastarg.txt
)
FOR /F "delims=" %%i IN (pslastarg.txt) DO SET "LASTARG=%%i"

powershell -command "Start-Process cmd -ArgumentList '/c cd /D %~dp0 && python\python.exe %1 %2 && pause || pause' %LASTARG%"
