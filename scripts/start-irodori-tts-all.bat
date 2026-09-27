@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "NORMAL_SCRIPT=%ROOT_DIR%start-irodori-tts.bat"
set "VOICEDESIGN_SCRIPT=%ROOT_DIR%start-irodori-tts-voicedesign.bat"

title Irodori-TTS Gradio UIs

if not exist "%NORMAL_SCRIPT%" (
  echo Missing script:
  echo   %NORMAL_SCRIPT%
  pause
  exit /b 1
)

if not exist "%VOICEDESIGN_SCRIPT%" (
  echo Missing script:
  echo   %VOICEDESIGN_SCRIPT%
  pause
  exit /b 1
)

echo Starting Irodori-TTS normal UI on http://localhost:7860
echo Starting Irodori-TTS VoiceDesign UI on http://localhost:7861
echo.

start "Irodori-TTS 7860" "%NORMAL_SCRIPT%"
start "Irodori-TTS VoiceDesign 7861" "%VOICEDESIGN_SCRIPT%"

echo Both startup windows were opened.
echo Close each server window to stop that server.
pause
