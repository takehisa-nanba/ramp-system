@echo off
setlocal
pushd "%~dp0" || exit /b 1
docker info >nul 2>&1
if errorlevel 1 (
  echo Start Docker Desktop, wait for the engine, and run this file again.
  pause
  exit /b 1
)
docker compose up --build --detach --wait
if errorlevel 1 (
  docker compose logs --tail 30 web
  pause
  exit /b 1
)
start "" "http://localhost:8080"
popd
