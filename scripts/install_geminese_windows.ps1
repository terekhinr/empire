# Установка geminese в Obsidian vault (Windows).
# Запуск: powershell -ExecutionPolicy Bypass -File scripts\install_geminese_windows.ps1
# Опционально: -VaultPath "F:\YandexDisk\obsidian (2)"

param(
    [string]$VaultPath = "F:\YandexDisk\obsidian (2)"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Src = Join-Path $RepoRoot "templates\obsidian_plugins\geminese"
$Dst = Join-Path $VaultPath ".obsidian\plugins\geminese"

$files = @("main.js", "manifest.json", "styles.css")
foreach ($f in $files) {
    $p = Join-Path $Src $f
    if (-not (Test-Path $p)) {
        Write-Error "Нет файла: $p. Сначала выполните scripts/fetch_geminese_plugin.sh или git pull."
    }
}

if (-not (Test-Path $VaultPath)) {
    Write-Error "Vault не найден: $VaultPath. Укажите -VaultPath 'путь\к\vault'."
}

New-Item -ItemType Directory -Force -Path $Dst | Out-Null
foreach ($f in $files) {
    Copy-Item -Path (Join-Path $Src $f) -Destination (Join-Path $Dst $f) -Force
    Write-Host "OK: $f -> $Dst"
}

# Включить плагин в community-plugins.json (если файл есть)
$pluginsJson = Join-Path $VaultPath ".obsidian\community-plugins.json"
if (Test-Path $pluginsJson) {
    $list = Get-Content $pluginsJson -Raw | ConvertFrom-Json
    if ($list -isnot [System.Collections.IList]) {
        $list = @($list)
    }
    if ($list -notcontains "geminese") {
        $list += "geminese"
        $list | ConvertTo-Json -Compress | Set-Content $pluginsJson -Encoding UTF8
        Write-Host "Добавлен geminese в community-plugins.json"
    }
} else {
    Write-Host "Создайте community-plugins.json вручную или включите Geminese в Settings -> Community plugins."
}

Write-Host ""
Write-Host "Дальше на ПК:"
Write-Host "  1. npm install -g @google/gemini-cli   (если ещё нет)"
Write-Host "  2. gemini   (логин Google один раз)"
Write-Host "  3. Obsidian -> Settings -> Community plugins -> включить Geminese -> Reload"
Write-Host "  4. Промпт Empire: templates/geminese_empire_system_prompt.txt"
Write-Host ""
Write-Host "Документация: docs/obsidian_geminese_setup_ru.md"
