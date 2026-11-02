#!/usr/bin/env bash
# Запуск отдельного Chrome для агента (macOS / Linux).
# Отдельный профиль: в нём только демо-аккаунты маркетплейсов, без личных входов.
set -euo pipefail

PROFILE_DIR="${GIFT_AGENT_CHROME_PROFILE:-$HOME/.gift-agent-chrome}"
PORT=9222

if [[ -n "${CHROME_BIN:-}" ]]; then
  CHROME="$CHROME_BIN"
elif [[ "$(uname)" == "Darwin" ]]; then
  CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
else
  CHROME="$(command -v google-chrome || command -v chromium || true)"
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

echo "Chrome запущен: профиль $PROFILE_DIR, CDP на 127.0.0.1:${PORT}"
