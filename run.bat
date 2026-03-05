@echo off
REM De-Identification App Launcher (Windows)
REM One-command launcher that builds and runs the Docker container

setlocal enabledelayedexpansion

set APP_NAME=deidentify-app
set IMAGE_NAME=deidentify-app
set PORT=8501

echo ================================================================
echo      De-Identification App - Local PII Removal Tool
echo ================================================================
echo.

REM Get the directory where this script lives
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM Step 1: Check if Docker is installed
echo [1/5] Checking Docker installation...
where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Docker is not installed.
    echo.
    echo Please install Docker Desktop for Windows:
    echo   https://docs.docker.com/desktop/install/windows-install/
    echo.
    echo After installing, run this script again.
    pause
    exit /b 1
)
echo       [OK] Docker is installed

REM Step 2: Check if Docker is running
echo [2/5] Checking if Docker is running...
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Docker is not running.
    echo.
    echo Please start Docker Desktop and run this script again.
    echo.
    pause
    exit /b 1
)
echo       [OK] Docker is running

REM Step 3: Create output directories if needed
echo [3/5] Ensuring output directories exist...
if not exist "%SCRIPT_DIR%data" mkdir "%SCRIPT_DIR%data"
if not exist "%SCRIPT_DIR%output" mkdir "%SCRIPT_DIR%output"
if not exist "%SCRIPT_DIR%audit" mkdir "%SCRIPT_DIR%audit"
echo       [OK] Directories ready

REM Step 4: Build the Docker image if it doesn't exist or if --rebuild is passed
echo [4/5] Checking Docker image...

set BUILD_NEEDED=0

if "%1"=="--rebuild" set BUILD_NEEDED=1
if "%1"=="-r" set BUILD_NEEDED=1

if !BUILD_NEEDED!==0 (
    docker image inspect %IMAGE_NAME% >nul 2>&1
    if !errorlevel! neq 0 (
        echo       Image not found, building...
        set BUILD_NEEDED=1
    )
)

if !BUILD_NEEDED!==1 (
    echo.
    echo Building Docker image (this may take 5-10 minutes on first run)...
    echo The SpaCy language model (~560MB) will be downloaded during build.
    echo.
    docker build -t %IMAGE_NAME% .
    if !errorlevel! neq 0 (
        echo.
        echo ERROR: Docker build failed.
        pause
        exit /b 1
    )
    echo.
    echo       [OK] Image built successfully
) else (
    echo       [OK] Image already exists (use --rebuild to force rebuild)
)

REM Step 5: Stop any existing container and start a new one
echo [5/5] Starting the application...

REM Stop existing container if running
docker ps -q -f name=%APP_NAME% >nul 2>&1
if !errorlevel!==0 (
    echo       Stopping existing container...
    docker stop %APP_NAME% >nul 2>&1
)

REM Remove existing container if it exists
docker rm %APP_NAME% >nul 2>&1

REM Run the container with network isolation
docker run -d ^
    --name %APP_NAME% ^
    --network none ^
    -p %PORT%:8501 ^
    -v "%SCRIPT_DIR%data:/workspace/data:ro" ^
    -v "%SCRIPT_DIR%output:/workspace/output" ^
    -v "%SCRIPT_DIR%audit:/workspace/audit" ^
    --memory=4g ^
    --cpus=2.0 ^
    %IMAGE_NAME% >nul

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to start container.
    pause
    exit /b 1
)

echo       [OK] Application started

REM Done!
echo.
echo ================================================================
echo                     App is running!
echo ================================================================
echo.
echo Open your browser to: http://localhost:%PORT%
echo.
echo Usage:
echo   * Place input files in: %SCRIPT_DIR%data\
echo   * De-identified files saved to: %SCRIPT_DIR%output\
echo   * Audit logs saved to: %SCRIPT_DIR%audit\
echo.
echo Commands:
echo   * Stop the app:    docker stop %APP_NAME%
echo   * View logs:       docker logs %APP_NAME%
echo   * Rebuild:         run.bat --rebuild
echo.

REM Try to open the browser
timeout /t 2 /nobreak >nul
start http://localhost:%PORT%

endlocal
