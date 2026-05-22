@echo off
cd /d "%~dp0"
echo === AutogameCentor null bytes fix push ===

git remote -v
git add Core/action_base.py games/actions/L2m.py games/actions/NightCrow.py
git commit -m "fix: remove null bytes from action_base, L2m, NightCrow"
git push origin main

echo === Done ===
pause
