@echo off
cd /d "%~dp0"
python scripts\access_demo.py
if errorlevel 1 pause
