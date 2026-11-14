@echo off
chcp 65001 >nul
cd /d "%~dp0"
title PoseWear Metadata Editor
set PY="C:/AI/ComfyUI-aki-v3/python/python.exe"
if not exist %PY% (
  echo Python not found at %PY%, trying system python...
  set PY=python
)
echo Launching PoseWear Metadata Editor...
%PY% app.py
if errorlevel 1 (
  echo.
  echo [ERROR] The app exited unexpectedly. See message above.
  pause
)
