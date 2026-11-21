@echo off
setlocal
pushd "%~dp0" || exit /b 1
docker info >nul 2>&1
if errorlevel 1 (
  echo Start Docker Desktop, wait for the engine, and run this file again.
  pause
  exit /b 1
)
set "archive=%TEMP%\ramp-build-%RANDOM%-%RANDOM%-%RANDOM%.tar"
if exist "%archive%" exit /b 1
tar.exe -cf "%archive%" --exclude "__pycache__" --exclude "*.pyc" --exclude ".env*" --exclude "*.db" -T local_demo/build-inputs.txt
if errorlevel 1 goto build_failed
docker build -f local_demo/Dockerfile -t ramp-system-local-web:latest - < "%archive%"
if errorlevel 1 goto build_failed
del "%archive%"
docker compose up --no-build --detach --wait
if errorlevel 1 (
  docker compose logs --tail 30 web
  pause
  exit /b 1
)
start "" "http://localhost:8080"
popd
exit /b 0

:build_failed
if exist "%archive%" del "%archive%"
echo Image build failed. See the first error above.
pause
popd
exit /b 1
