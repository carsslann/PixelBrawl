@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (set PYCMD=py) else (set PYCMD=python)
%PYCMD% -c "import pygame" >nul 2>nul
if errorlevel 1 (
    echo pygame kuruluyor...
    %PYCMD% -m pip install -r requirements.txt
)
%PYCMD% main.py
if errorlevel 1 pause
