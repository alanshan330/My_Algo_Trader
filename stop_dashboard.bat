@echo off
echo Stopping Antigravity Web Dashboard...

:: This command looks for any python.exe process that was started with "src\web\app.py" and terminates it
wmic process where "name='python.exe' and commandline like '%%src\\\\web\\\\app.py%%'" call terminate >nul 2>&1

echo Dashboard successfully stopped.
pause
