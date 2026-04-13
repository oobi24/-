@echo off
echo ============================================
echo A-Share Quant Backtest System Launcher
echo ============================================
echo.

REM Set Anaconda Environment
set ANACONDA_PATH=C:\ProgramData\Anaconda3
set USER_SITE=%USERPROFILE%\AppData\Roaming\Python\Python39\site-packages

REM Add to PATH
set PATH=%ANACONDA_PATH%;%ANACONDA_PATH%\Library\bin;%ANACONDA_PATH%\Scripts;%PATH%

REM Set Python Path
set PYTHONPATH=%USER_SITE%;%ANACONDA_PATH%\Lib\site-packages;%PYTHONPATH%

REM Disable proxy for Tushare
set NO_PROXY=*
set no_proxy=*

echo Python: %ANACONDA_PATH%\python.exe
echo.

REM Start GUI
echo Starting GUI...
"%ANACONDA_PATH%\python.exe" gui_backtest.py

if errorlevel 1 (
    echo.
    echo GUI failed to start
    pause
)
