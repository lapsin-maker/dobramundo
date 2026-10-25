@echo off
rem Build Windows; Python 3.12, sem apagar outras saídas ou saves.
rem Uso: build_windows.bat [onefile] [nopause]
setlocal EnableExtensions
cd /d "%~dp0"
if errorlevel 1 goto :fail
set "BUILD_ARGS="
set "NOPAUSE=0"
for %%A in (%*) do (
    if /i "%%~A"=="onefile" set "BUILD_ARGS=--onefile"
    if /i "%%~A"=="nopause" set "NOPAUSE=1"
)
if not exist ".venv\Scripts\python.exe" py -3.12 -m venv .venv
if errorlevel 1 goto :fail
set "VENV_PY=%CD%\.venv\Scripts\python.exe"
"%VENV_PY%" -c "import sys; assert sys.version_info[:2] == (3, 12), 'O build fixado requer Python 3.12'"
if errorlevel 1 goto :fail
"%VENV_PY%" -m pip install -r requirements-webcam.txt pyinstaller -c constraints-build.txt
if errorlevel 1 goto :fail
"%VENV_PY%" tools\build_desktop.py %BUILD_ARGS%
if errorlevel 1 goto :fail
if "%BUILD_ARGS%"=="--onefile" (echo Build concluido: dist\Dobramundo.exe) else (echo Build concluido: distribua toda a pasta dist\Dobramundo)
if "%NOPAUSE%"=="0" pause
exit /b 0
:fail
echo ERRO: build nao concluido. Consulte a mensagem acima.
if "%NOPAUSE%"=="0" pause
exit /b 1
