@echo off
chcp 65001 >nul
echo ===== tel-d - آسان‌ترین راه =====
echo روش پیشنهادی: JSON Export (صفر اینترنت، 100 درصد تضمین)
echo.

REM اگر پوشه out نیست بساز
if not exist out mkdir out

REM چک venv
if not exist .venv\Scripts\python.exe (
  echo ساخت محیط مجازی...
  py -m venv .venv
  .venv\Scripts\python.exe -m pip install -U pip
  .venv\Scripts\python.exe -m pip install -r requirements.txt
)

echo.
echo [1] روش JSON - آفلاین، بدون API، بدون پروکسی (پیشنهادی)
echo     Telegram Desktop -> چت -> Export chat history -> JSON -> فایل result.json رو بذار کنار tel-d.py
echo     بعد: .venv\Scripts\python.exe tel-d.py -o ./out json -i result.json
echo.
echo [2] روش MTProto با پروکسی (برای فیلتر ایران)
echo     set TELEGRAM_PROXY=socks5://127.0.0.1:7890
echo     .venv\Scripts\python.exe tel-d.py -o ./out mtproto --list --proxy socks5://127.0.0.1:7890
echo.

.\.venv\Scripts\python.exe tel-d.py --api-help
echo.
echo برای شروع، فایل result.json رو بذار اینجا و بزن:
echo .\.venv\Scripts\python.exe tel-d.py -o ./out json -i result.json
pause
