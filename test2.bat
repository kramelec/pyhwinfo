@echo off
chcp 866 >NUL
cd /D "%~dp0"
call run.bat memory.py mchbar
