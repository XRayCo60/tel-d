# فیکس ارور Activate.ps1
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
Write-Host "ExecutionPolicy برای این ترمینال Bypass شد" -ForegroundColor Green
Write-Host "حالا می‌تونی .\.venv\Scripts\Activate.ps1 بزنی یا مستقیم از python.exe استفاده کنی"

# ست کردن پروکسی Freegate - پورت رو چک کن (8580 یا 7890 یا 1080)
# Freegate معمولا 8580 هست، Clash 7890
$env:HTTP_PROXY="http://127.0.0.1:7890"
$env:HTTPS_PROXY="http://127.0.0.1:7890"
$env:TELEGRAM_PROXY="socks5://127.0.0.1:7890"
Write-Host "پروکسی ست شد به 127.0.0.1:7890 - اگر Freegate پورتش فرق داره عوض کن" -ForegroundColor Yellow
Write-Host "برای پیدا کردن پورت Freegate: تو برنامه Freegate ببین نوشته Listening on..."
