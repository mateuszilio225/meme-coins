@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m meme_research run %*
) else (
  py -3 -m meme_research run %*
)
set "research_exit=%errorlevel%"
echo.
echo Codigo de saida: %research_exit%
pause
exit /b %research_exit%
