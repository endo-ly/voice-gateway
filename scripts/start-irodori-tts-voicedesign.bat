@echo off
setlocal

set "IRODORI_DIR=%~dp0..\.vendor\Irodori-TTS"
set "PORT=7861"

title Irodori-TTS VoiceDesign Gradio UI :%PORT%

if not exist "%IRODORI_DIR%\gradio_app_voicedesign.py" (
  echo Irodori-TTS VoiceDesign app was not found:
  echo   %IRODORI_DIR%
  pause
  exit /b 1
)

cd /d "%IRODORI_DIR%"

echo Starting Irodori-TTS VoiceDesign Gradio UI on http://localhost:%PORT%
echo.

where uv >nul 2>nul
if %errorlevel%==0 (
  uv run --no-sync python gradio_app_voicedesign.py --server-name 0.0.0.0 --server-port %PORT%
) else if exist ".venv\Scripts\python.exe" (
  .venv\Scripts\python.exe gradio_app_voicedesign.py --server-name 0.0.0.0 --server-port %PORT%
) else (
  echo Neither uv nor .venv\Scripts\python.exe was found.
  echo Install dependencies or run the Irodori-TTS setup first.
  pause
  exit /b 1
)

echo.
echo Irodori-TTS VoiceDesign stopped.
pause
