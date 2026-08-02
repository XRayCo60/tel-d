# آسان‌ترین راه - بدون ارور پالیسی
Write-Host "===== tel-d - آسان‌ترین راه =====" -ForegroundColor Cyan

# پاک کردن ENV پروکسی برای git clone (چون Freegate ممکنه github رو بلاک کنه)
Remove-Item Env:\HTTP_PROXY -ErrorAction SilentlyContinue
Remove-Item Env:\HTTPS_PROXY -ErrorAction SilentlyContinue
Remove-Item Env:\TELEGRAM_PROXY -ErrorAction SilentlyContinue

# اگر پوشه tel-d نیست، کلون کن
if (-not (Test-Path "tel-d")) {
  git clone --branch arena/019fc30d-tel-d https://github.com/XRayCo60/tel-d.git
}
Set-Location -Path "tel-d"

# ساخت venv اگر نیست
if (-not (Test-Path ".venv\Scripts\python.exe")) {
  py -m venv .venv
}

# نصب
& .\.venv\Scripts\python.exe -m pip install -U pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

Write-Host "`n[1] روش JSON - صفر اینترنت، 100% تضمین (پیشنهادی)" -ForegroundColor Green
Write-Host "    Telegram Desktop -> چت -> Export -> JSON -> result.json رو بذار کنار tel-d.py"
Write-Host "    بعد بزن: .\.venv\Scripts\python.exe tel-d.py -o ./out json -i result.json"

Write-Host "`n[2] روش MTProto با پروکسی Freegate" -ForegroundColor Yellow
Write-Host '    $env:TELEGRAM_PROXY="socks5://127.0.0.1:7890"'
Write-Host '    .\.venv\Scripts\python.exe tel-d.py -o ./out mtproto --list --proxy socks5://127.0.0.1:7890'

& .\.venv\Scripts\python.exe tel-d.py --api-help
