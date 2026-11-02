#!/usr/bin/env bash
# Запуск отдельного Chrome для агента (macOS / Linux).
# Отдельный профиль: в нём только демо-аккаунты маркетплейсов, без личных входов.
set -euo pipefail

PROFILE_DIR="${GIFT_AGENT_CHROME_PROFILE:-$HOME/.gift-agent-chrome}"
PORT=9222

# Порядок поиска: CHROME_BIN → обычный Chrome → Chrome for Testing
# (в /Applications, затем в кэше Puppeteer) → Chromium.
CHROME="${CHROME_BIN:-}"
if [[ -z "$CHROME" ]]; then
  if [[ "$(uname)" == "Darwin" ]]; then
    for app in \
      "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
      "$HOME/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
      "/Applications/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing" \
      "$HOME/Applications/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing" \
      "/Applications/Chromium.app/Contents/MacOS/Chromium"; do
      if [[ -x "$app" ]]; then CHROME="$app"; break; fi
    done
    # Chrome for Testing, скачанный Puppeteer: берём самую свежую версию из кэша.
    if [[ -z "$CHROME" ]]; then
      CHROME="$(ls -d "$HOME"/.cache/puppeteer/chrome/mac*/chrome-mac*/"Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing" 2>/dev/null \
        | sort -V | tail -n 1 || true)"
    fi
  else
    CHROME="$(command -v google-chrome || command -v google-chrome-stable || command -v chrome || command -v chromium || true)"
  fi
fi

if [[ -z "$CHROME" || ! -x "$CHROME" ]]; then
  echo "Chrome не найден. Укажите путь: CHROME_BIN=/path/to/chrome $0" >&2
  exit 1
fi

if curl -fsS "http://127.0.0.1:${PORT}/json/version" >/dev/null 2>&1; then
  echo "На порту ${PORT} уже работает CDP — второй Chrome не запускаю."
  exit 0
fi

mkdir -p "$PROFILE_DIR"
"$CHROME" \
  --remote-debugging-port="$PORT" \
  --user-data-dir="$PROFILE_DIR" \
  --no-first-run \
  --no-default-browser-check \
  >/dev/null 2>&1 &

echo "Запущен: $CHROME"
echo "Профиль: $PROFILE_DIR, CDP на 127.0.0.1:${PORT}"
