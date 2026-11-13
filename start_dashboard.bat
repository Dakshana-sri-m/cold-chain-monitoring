@echo off
title Boomerang Cold Chain Monitoring Dashboard - Team 3
color 0B

echo ===============================================================================
echo   BOOMERANG LOGISTICS - COLD CHAIN REAL-TIME MONITORING & EXCURSION DASHBOARD
echo   Team 3 - Dakshana Sri M (Dashboard & IoT Pipeline)
echo ===============================================================================
echo.
echo [1/3] Checking Python installation...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH! Please install Python.
    pause
    exit /b
)

echo [2/3] Installing required packages (Flask, Flask-CORS, Pandas, Openpyxl)...
python -m pip install flask flask-cors pandas openpyxl >nul 2>&1

echo [3/3] Starting Cold Chain Dashboard Server on port 5050...
echo.
echo -------------------------------------------------------------------------------
echo   Dashboard URL:  http://127.0.0.1:5050
echo   Hardware API:   http://127.0.0.1:5050/api/telemetry
echo -------------------------------------------------------------------------------
echo.
echo Opening browser in 3 seconds...
start "" http://127.0.0.1:5050

python app.py
pause

