@echo off
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
  echo Install Node.js 22 LTS from nodejs.org first.
  pause
  exit /b 1
)
call npm ci
if errorlevel 1 goto fail
call npm test
if errorlevel 1 goto fail
call npm run build:win
if errorlevel 1 goto fail
start "" "%~dp0release"
exit /b 0
:fail
 echo Build failed. See the error above.
 pause
 exit /b 1
