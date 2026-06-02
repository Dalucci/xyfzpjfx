@echo off
chcp 65001 >nul
cd /d %~dp0
if not exist .venv (
  python -m venv .venv
)
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.
echo 启动成功后，请在浏览器打开 http://127.0.0.1:5000
echo.
python app.py
pause
