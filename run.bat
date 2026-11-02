@echo off
setlocal enabledelayedexpansion

echo ====================================================================
echo  Electricity Theft & Distribution Loss Detection
echo  AI-Based Electricity Theft and Distribution Loss Detection Using ML
echo  Sri Shakthi Institute of Engineering and Technology
echo ====================================================================

:: Step 1: Detect Python
where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set PYTHON_CMD=python
) else (
    if exist "C:\laragon\bin\python\python-3.13\python.exe" (
        set PYTHON_CMD="C:\laragon\bin\python\python-3.13\python.exe"
    ) else (
        echo [ERROR] Python 3.11+ is not found on your system or in Laragon.
        echo Please ensure Python is installed and added to your PATH.
        pause
        exit /b 1
    )
)

echo [OK] Using Python: %PYTHON_CMD%

:: Step 2: Virtual Environment
if not exist "venv\Scripts\python.exe" (
    echo [INFO] Creating Python virtual environment in .\venv...
    %PYTHON_CMD% -m venv venv --system-site-packages
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: Step 3: Activate Virtual Environment
call venv\Scripts\activate.bat

:: Step 4: Verify / Install requirements
echo [INFO] Checking dependencies...
python -c "import flask, scikit_learn, pandas, numpy, joblib" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [INFO] Installing required packages from requirements.txt...
    pip install -r requirements.txt
)

:: Step 5: Initialize Database, Dataset and Models (if not already generated)
echo [INFO] Verifying grid database and machine learning models...
python -c "from src.utils.helpers import ensure_initialized; ensure_initialized(force_regenerate=False)"

:: Step 6: Start Flask Server
echo ====================================================================
echo  System Initialized Successfully!
echo  Access Dashboard at: http://127.0.0.1:5000
echo  Press Ctrl+C to stop the server.
echo ====================================================================

python app.py

pause

