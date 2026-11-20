@echo off
title R.U.B.I. Core Boot Sequence
color 0B

echo ===================================================
echo       R.U.B.I. SYSTEM INITIALIZATION
echo ===================================================
echo.
echo [SYS] Starting Python Backend Server...

:: Navigate to backend and start uvicorn silently in the background
cd backend
start /b python -m uvicorn main:app --reload

echo [SYS] Core online.
echo [SYS] Waiting for WebSocket endpoints to secure...

:: Wait for 3 seconds to ensure the server is fully running
timeout /t 3 /nobreak >nul

echo [SYS] Launching Holographic Terminal...

:: Navigate to frontend and open the dashboard in the default browser
cd ../frontend
start index.html

echo.
echo [SYS] Boot sequence complete. You can close this black window if you wish.
pause