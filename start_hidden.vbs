Set WshShell = CreateObject("WScript.Shell")

' 1. Start the Flask server in the background (0 = hide window, False = don't wait)
WshShell.Run "venv\Scripts\python.exe src\web\app.py", 0, False

' 2. Wait for 3 seconds to let the server initialize and bind the port
WScript.Sleep 3000

' 3. Automatically open the default web browser to the dashboard
WshShell.Run "http://127.0.0.1:5000"
