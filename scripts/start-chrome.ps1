# Запуск отдельного Chrome для агента (Windows).
# Отдельный профиль: в нём только демо-аккаунты маркетплейсов, без личных входов.
$ErrorActionPreference = "Stop"
$port = 9222

$candidates = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)
$chrome = $candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $chrome) {
    throw "Chrome не найден. Укажите путь к chrome.exe в scripts/start-chrome.ps1"
}

try {
    Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 "http://127.0.0.1:$port/json/version" | Out-Null
    Write-Host "На порту $port уже работает CDP — второй Chrome не запускаю."
    exit 0
} catch { }

$profileDir = Join-Path $env:LOCALAPPDATA "gift-agent-chrome"
New-Item -ItemType Directory -Force -Path $profileDir | Out-Null

Start-Process -FilePath $chrome -ArgumentList @(
    "--remote-debugging-port=$port",
    "--user-data-dir=`"$profileDir`"",
    "--no-first-run",
    "--no-default-browser-check"
)
Write-Host "Chrome запущен: профиль $profileDir, CDP на 127.0.0.1:$port"
