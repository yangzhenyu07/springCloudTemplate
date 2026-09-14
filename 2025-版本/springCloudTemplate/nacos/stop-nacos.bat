@echo off
setlocal enabledelayedexpansion
rem ============================================================
rem  stop-nacos.bat - Stop Nacos Server 3.0.3
rem  1) kill java process(es) whose command line has nacos-server.jar
rem  2) fallback: kill whatever still LISTENING on port 18848
rem ============================================================

set FOUND=0

for /f "usebackq delims=" %%p in (`powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*nacos-server.jar*' } | Select-Object -ExpandProperty ProcessId"`) do (
    echo [stop] Killing Nacos process PID %%p ...
    taskkill /F /PID %%p >nul 2>&1
    set FOUND=1
)

if !FOUND! equ 0 echo [stop] No nacos-server.jar process found.

rem ping-based sleep (timeout /nobreak aborts when stdin is redirected)
ping -n 3 127.0.0.1 >nul
netstat -ano | findstr ":18848" | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    echo [stop] OK: port 18848 released.
    exit /b 0
)

echo [stop] Port 18848 still occupied, killing by PID ...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":18848" ^| findstr "LISTENING"') do (
    echo [stop] taskkill PID %%p
    taskkill /F /PID %%p >nul 2>&1
)
ping -n 3 127.0.0.1 >nul
netstat -ano | findstr ":18848" | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    echo [stop] OK: port 18848 released.
    exit /b 0
)
echo [stop] WARN: port 18848 still listening. Check manually with: netstat -ano ^| findstr 18848
pause
exit /b 1
