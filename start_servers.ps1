Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host "  Automated Commercial Solid Waste Segregation Optimization Dashboard" -ForegroundColor Green
Write-Host "  Municipal Recycling Plants - Greater Chennai Corporation (GCC)" -ForegroundColor Green
Write-Host "=========================================================================" -ForegroundColor Cyan

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Starting FastAPI Backend (Port 8000)..." -ForegroundColor Yellow
Start-Process cmd.exe -ArgumentList "/k", "cd /d `"$rootDir\backend`" && .\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

Write-Host "Starting Next.js Frontend (Port 3000)..." -ForegroundColor Yellow
Start-Process cmd.exe -ArgumentList "/k", "cd /d `"$rootDir\frontend`" && npm start"

Write-Host "`nSERVICES ONLINE:" -ForegroundColor Green
Write-Host "Frontend Dashboard: http://localhost:3000" -ForegroundColor White
Write-Host "Backend API Docs:   http://localhost:8000/docs" -ForegroundColor WhiteWrite-Host "=========================================================================" -ForegroundColor Cyan
Write-Host "  Automated Commercial Solid Waste Segregation Optimization Dashboard" -ForegroundColor Green
Write-Host "  Municipal Recycling Plants - Greater Chennai Corporation (GCC)" -ForegroundColor Green
Write-Host "=========================================================================" -ForegroundColor Cyan

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Starting FastAPI Backend (Port 8000)..." -ForegroundColor Yellow
Start-Process cmd.exe -ArgumentList "/k", "cd /d `"$root
321.
030Dir\backend`" && .\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

Write-Host "Starting Next.js Frontend (Port 3000)..." -ForegroundColor Yellow
Start-Process cmd.exe -ArgumentList "/k", "cd /d `"$rootDir\frontend`" && npm start"

Write-Host "`nSERVICES ONLINE:" -ForegroundColor Green
Write-Host "Frontend Dashboard: http://localhost:3000" -ForegroundColor White
Write-Host "Backend API Docs:   http://localhost:8000/docs" -ForegroundColor White