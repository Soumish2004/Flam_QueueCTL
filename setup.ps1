# QueueCTL Setup Script for Windows PowerShell

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  QueueCTL Setup (Windows)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = & python --version 2>&1
    Write-Host "Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Install Python 3.8+ from https://www.python.org/" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Create virtual environment
Write-Host "Creating virtual environment..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "Virtual environment exists" -ForegroundColor Green
} else {
    & python -m venv venv
    Write-Host "Virtual environment created" -ForegroundColor Green
}

Write-Host ""

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
& .\venv\Scripts\pip.exe install -r requirements.txt
Write-Host "Dependencies installed" -ForegroundColor Green

Write-Host ""

# Verify
Write-Host "Verifying installation..." -ForegroundColor Yellow
& .\venv\Scripts\python.exe queuectl.py --version

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Activate venv: .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "  2. View help: python queuectl.py --help" -ForegroundColor Cyan
Write-Host "  3. Run tests: python test.py" -ForegroundColor Cyan
Write-Host ""
