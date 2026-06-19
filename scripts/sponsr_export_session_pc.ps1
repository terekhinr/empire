# Экспорт сессии Sponsr с ПК (CaJcWJCd5T3Wuhrome, где вход уже работает).
# PowerShell:
#   cd "F:\YandexDisk\obsidian (2)\Life\tools"
#   powershell -ExecutionPolicy Bypass -File sponsr_export_session_pc.ps1
#
# Или cookies через Cookie-Editor → sponsr_cookies.json (проще, см. SPONSR_COOKIES.md)

$Out = Join-Path $PSScriptRoot "sponsr_session.json"
$Py = @'
from playwright.sync_api import sync_playwright
out = r"OUT_PATH"
with sync_playwright() as p:
    for channel in ("chrome", "msedge", None):
        try:
            kw = {"headless": False}
            if channel:
                kw["channel"] = channel
            browser = p.chromium.launch(**kw)
            break
        except Exception:
            browser = None
    if browser is None:
        raise SystemExit("Не удалось запустить Chrome/Edge/Chromium")
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://sponsr.ru/auth/signin/", timeout=60000)
    print("1) Нажмите «Войти» (email+пароль) — как в обычном Chrome")
    print("2) Откройте https://sponsr.ru/crimsonanalytics/ — полный текст статьи")
    print("3) F12 → Application → Cookies → sponsr.ru — должна быть SESS")
    input("4) Enter здесь когда готово...")
    context.storage_state(path=out)
    browser.close()
print("Saved:", out)
'@ -replace 'OUT_PATH', ($Out -replace '\\', '\\')

$Tmp = Join-Path $env:TEMP "sponsr_export_session.py"
Set-Content -Path $Tmp -Value $Py -Encoding UTF8
python $Tmp
Write-Host "Скопируйте на VPS или в vault: $Out"
