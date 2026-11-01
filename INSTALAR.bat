@echo off
setlocal
cd /d "%~dp0"
py -3 -c "import sys; assert sys.version_info >= (3,11), 'Use Python 3.11 ou superior'"
if errorlevel 1 goto fail
if not exist ".venv\Scripts\python.exe" py -3 -m venv .venv
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m meme_research --version
if errorlevel 1 goto fail
echo Instalacao local pronta. Dependencias de execucao: somente biblioteca padrao.
echo Leia LEIA_PRIMEIRO.md antes de inicializar a coleta.
pause
exit /b 0
:fail
echo Falha. Instale Python 3.11 ou superior com o launcher py.
pause
exit /b 1
