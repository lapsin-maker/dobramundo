@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem Roda o Dobramundo pelo codigo-fonte. Na primeira vez instala o pygame e o
rem controle pela webcam (MediaPipe e OpenCV); sem a webcam o jogo usa teclado e mouse.
where py >nul 2>nul && (set PY=py -3) || (set PY=python)
%PY% -c "import pygame" >nul 2>nul || (
    echo Instalando as dependencias, isso so acontece na primeira vez...
    %PY% -m pip install -r requirements-webcam.txt || %PY% -m pip install -r requirements.txt
)
%PY% run_dobramundo.py
if errorlevel 1 (
    echo.
    echo O jogo encerrou com erro. Verifique se o Python 3.8 ou mais novo esta instalado.
    pause
)
