@echo off
setlocal
rem ============================================================
rem  start-nacos.bat - Start Nacos Server 3.0.3 (standalone)
rem  Ports: 18848 main(HTTP /nacos) / 8080 console / 19848 gRPC
rem ============================================================

set "JAVA_EXE=C:\Program Files\Java\jdk-17.0.19.10-hotspot\bin\java.exe"
set "NACOS_HOME=E:\nacos-server-3.0.3\nacos"

rem CRITICAL: Boot relaxed-binding would read SERVER__PORT as server.port=0
rem (random ports). Clear it for this script's process tree.
set "SERVER__PORT="

if not exist "%JAVA_EXE%" (
    echo [start] ERROR: JDK17 not found at "%JAVA_EXE%"
    exit /b 1
)
if not exist "%NACOS_HOME%\target\nacos-server.jar" (
    echo [start] ERROR: nacos-server.jar not found under "%NACOS_HOME%\target\"
    exit /b 1
)

rem Already running?
netstat -ano | findstr ":18848" | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo [start] Nacos already running on port 18848. Nothing to do.
    exit /b 0
)

echo [start] Starting Nacos 3.0.3 standalone ...
if not exist "%NACOS_HOME%\logs" mkdir "%NACOS_HOME%\logs"
rem Launch java directly via start (its own console session, minimized).
rem NOTE 1: conf path must end with '/' (not '\') - a trailing backslash before the
rem         closing quote gets mangled by cmd argument parsing and Spring then treats
rem         it as a file, failing with "File extension is not known to any PropertySourceLoader".
rem NOTE 2: do NOT wrap java in `cmd /c "... > file 2>&1"` - under job-object based
rem         launchers the whole child tree gets killed when the caller exits.
rem         Console output goes to the minimized window; file logs live in logs\.
start "nacos-server-3.0.3" /D "%NACOS_HOME%" /MIN "%JAVA_EXE%" -Dnacos.standalone=true -Dnacos.home="%NACOS_HOME%" -jar "%NACOS_HOME%\target\nacos-server.jar" --spring.config.additional-location="file:%NACOS_HOME%/conf/"

echo [start] Waiting for port 18848 (max ~90s) ...
set /a TRIES=0
:waitloop
rem ping-based sleep: works in both interactive and redirected (non-interactive) consoles,
rem unlike `timeout /nobreak` which aborts when stdin is redirected.
ping -n 4 127.0.0.1 >nul
netstat -ano | findstr ":18848" | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 goto started
set /a TRIES+=1
if %TRIES% lss 30 goto waitloop
echo [start] FAILED: port 18848 not listening after ~90s. See "%NACOS_HOME%\logs\console.out"
exit /b 1

:started
echo [start] OK: Nacos 3.0.3 is up.
echo         main    : http://127.0.0.1:18848/nacos
echo         console : http://127.0.0.1:8080
echo         gRPC    : 19848
pause
exit /b 0
