@echo off
chcp 65001 > nul
echo ===================================
echo      ControlCentor 실행기
echo ===================================
echo.
echo [1/2] 최신 버전 확인 중...
git pull
echo.
echo [2/2] ControlCentor 실행 중...
start "" pythonw AutogameCentor/Gui.py
