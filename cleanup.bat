@echo off
echo ============================================
echo   Student Feedback System - Cleanup ^& Start
echo ============================================
echo.

:: Step 1: Kill processes on port 8000 (Django)
echo [1/5] Killing processes on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING 2^>nul') do (
    echo   Found PID %%a on port 8000 — killing...
    taskkill /F /PID %%a >nul 2>&1
)
echo   Port 8000 cleared.
echo.

:: Step 2: Kill processes on port 5173 (Vite)
echo [2/5] Killing processes on port 5173...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING 2^>nul') do (
    echo   Found PID %%a on port 5173 — killing...
    taskkill /F /PID %%a >nul 2>&1
)
echo   Port 5173 cleared.
echo.

:: Step 3: Kill zombie python/node processes (optional aggressive cleanup)
echo [3/5] Cleaning up zombie processes...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM node.exe >nul 2>&1
echo   Done.
echo.

:: Step 4: Start Django backend
echo [4/5] Starting Django backend on 127.0.0.1:8000...
cd /d "%~dp0feedback_system"
start "Django Backend" cmd /k "python manage.py runserver 127.0.0.1:8000"

:: Wait and verify health check
echo   Waiting for backend to initialize...
set RETRIES=0
:healthcheck
timeout /t 2 /nobreak >nul
set /a RETRIES+=1
curl -s http://127.0.0.1:8000/api/health/ | findstr "ok" >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo   Backend is ONLINE and healthy!
) else (
    if %RETRIES% LSS 10 (
        echo   Attempt %RETRIES%/10 — backend not ready yet...
        goto healthcheck
    ) else (
        echo   WARNING: Backend did not respond after 10 attempts.
        echo   Check the Django terminal for errors.
    )
)
echo.

:: Step 5: Start Vite frontend
echo [5/5] Starting Vite frontend on port 5173...
cd /d "%~dp0frontend"
start "Vite Frontend" cmd /k "npm run dev"

echo.
echo ============================================
echo   Both servers are starting!
echo   Backend: http://127.0.0.1:8000/api/health/
echo   Frontend: http://127.0.0.1:5173/
echo ============================================
echo.
pause
