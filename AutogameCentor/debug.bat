@echo off
cd /d "%~dp0"
echo === Python 버전 확인 ===
python --version
echo.
echo === 패키지 설치 ===
pip install -r requirements.txt
echo.
echo === Gui.py 실행 ===
python Gui.py
echo.
echo === 종료됨 ===
pause
