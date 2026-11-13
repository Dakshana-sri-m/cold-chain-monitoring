# Boomerang Cold Chain Dashboard Launcher (PowerShell)
# Team 3 - Dakshana Sri M
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host "  BOOMERANG LOGISTICS - COLD CHAIN REAL-TIME MONITORING & EXCURSION DASHBOARD" -ForegroundColor Yellow
Write-Host "  Team 3 - Dakshana Sri M (Dashboard & IoT Pipeline)" -ForegroundColor Green
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/3] Checking dependencies..." -ForegroundColor Gray
python -m pip install flask flask-cors pandas openpyxl | Out-Null

Write-Host "[2/3] Launching web browser at http://127.0.0.1:5050..." -ForegroundColor Gray
Start-Process "http://127.0.0.1:5050"

Write-Host "[3/3] Starting Flask application server..." -ForegroundColor Green
Write-Host "Dashboard Local URL:   http://127.0.0.1:5050" -ForegroundColor White
Write-Host "Hardware Ingest API:   http://127.0.0.1:5050/api/telemetry" -ForegroundColor White
Write-Host "Press Ctrl+C to stop the server.`n" -ForegroundColor DarkGray

python app.py

