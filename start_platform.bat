@echo off
title HireIQ Recruiter OS Starter
echo =======================================================
echo           Starting HireIQ Recruiter OS...
echo =======================================================
echo.

echo [1/3] Starting FastAPI Backend on Port 8000...
start "HireIQ Backend" cmd /k "cd backend && python main.py"

echo.
echo [2/3] Starting React Frontend...
start "HireIQ Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo [3/3] Starting Ngrok Tunnel (External Sharing)...
start "HireIQ Ngrok Tunnel" cmd /k "ngrok http --url=lively-cortex-obstacle.ngrok-free.dev 5173"

echo.
echo =======================================================
echo   All systems started in separate windows!
echo   - Backend: http://127.0.0.1:8000
echo   - Frontend: http://localhost:5173
echo   - Public Sharing Link: https://lively-cortex-obstacle.ngrok-free.dev
echo.
echo   To shut down the platform, close the terminal windows.
echo =======================================================
pause
