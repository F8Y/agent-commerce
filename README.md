# Gift Agent — MVP

Telegram-бот — единый интерфейс заказа: помогает выбрать подарок или товар,
собирает корзину и оформляет заказ на маркетплейсах (Wildberries, Яндекс Маркет,
Ozon) и в местных магазинах Хабаровска. Финальное «Заказать» / «Оплатить»
срабатывает только после подтверждения кнопками в Telegram.

Запускается локально: домашний IP не режется антиботами, как датацентровый, и
не нужно платить за сервер.

## Как устроено

```
Telegram
   │ long polling (белый IP и открытые порты не нужны)
   ▼
┌───────────── docker compose ─────────────────────────────┐
│ hermes        Hermes Agent: gateway, модель, скиллы      │
│   ├─ MCP  ──► marketplace   ru-marketplace-mcp v2.7.0    │
│   └─ MCP  ──► playwright ──► cdp-proxy ──┐               │
│               (Playwright MCP)  (nginx)  │               │
│ hermes-init   копирует config/SOUL/skills/plugin в том   │
└───────────────────────────┼──────────────────────────────┘
                            ▼
              Chrome на хосте, отдельный профиль,
              127.0.0.1:9222 — вход в демо-аккаунты,
              на демо видно, как агент кликает
```

- **hermes** — [Hermes Agent](https://github.com/NousResearch/hermes-agent),
  официальный образ `nousresearch/hermes-agent`. Терминал, исполнение кода,
  встроенный браузер и веб-поиск отключены, скиллы агент без подтверждения не
  меняет.
- **marketplace** — [ru-marketplace-mcp](https://github.com/Vladimir-Human/ru-marketplace-mcp):
  поиск, карточки, отзывы, сравнение цен. Собирается из тега `v2.7.0`.
- **playwright** — [Playwright MCP](https://github.com/microsoft/playwright-mcp)
  от Microsoft: браузерные инструменты агента (`browser_navigate`,
  `browser_snapshot`, `browser_click`, `browser_evaluate`…). Подключается к Chrome
  на хосте через `cdp-proxy`. Встроенный браузер Hermes отключён: в образе
  `stable` его инструменты не появлялись даже с установленным `agent-browser`.
- **checkout-guard** — плагин Hermes (`hermes/plugins/checkout-guard`). Перед
  кликом по «Заказать», «Оформить заказ», «Оплатить» и т.п. (в том числе
  JS-кликом и отправкой формы) Hermes показывает в Telegram кнопки
  подтверждения; отказ или 10 минут без ответа — действие заблокировано. Ввод
  номера карты блокируется всегда. Это код, а не промпт: модель его не обходит.
- **cdp-proxy** — nginx, через который контейнеры достают до Chrome на хосте.
  Chrome пускает CDP только с `Host: localhost`, поэтому прокси подменяет заголовок
  и переписывает ws-ссылки (см. `cdp-proxy/nginx.conf`).
- **Chrome на хосте** — настоящий браузер с отдельным профилем
  (`~/.gift-agent-chrome` или `%LOCALAPPDATA%\gift-agent-chrome`). В нём только
  демо-аккаунты маркетплейсов, без сохранённой карты.

## Что нужно

- Docker Desktop (на Windows — с бэкендом WSL2).
- Google Chrome.
- Свой dev-бот в Telegram (создаётся у BotFather) и свой Telegram ID.
- Ключ DeepSeek API (platform.deepseek.com). Можно и свой OpenAI-совместимый
  эндпоинт — см. комментарии в `hermes/config.yaml`.

## Запуск

1. Заполнить переменные:
   ```bash
   cp .env.example .env            # Windows: Copy-Item .env.example .env
   ```
   В `.env` — токен бота, свой Telegram ID, `DEEPSEEK_API_KEY` и
   `MARKETPLACE_MCP_TOKEN` (команда для генерации — в файле).
2. Модель по умолчанию — `deepseek-flash`, запасная — `deepseek-v4-pro`
   (`hermes/config.yaml`).
3. Запустить Chrome для агента:
   ```bash
   ./scripts/start-chrome.sh                                          # macOS / Linux
   powershell -ExecutionPolicy Bypass -File scripts\start-chrome.ps1  # Windows
   ```
   В открывшемся окне войти в демо-аккаунт WB, Ozon и Яндекс Маркета.
   Карту не сохранять.
4. Поднять стек:
   ```bash
   docker compose up -d --build     # первая сборка marketplace — несколько минут
   ```
5. Проверить:
   ```bash
   # мост до Chrome: в ответе должно быть ws://cdp-proxy:9222/devtools/browser/...
   docker compose exec cdp-proxy wget -qO- http://127.0.0.1:9222/json/version

   # MCP-серверы видны Hermes
   docker compose exec hermes hermes mcp test marketplace
   docker compose exec hermes hermes mcp test playwright
   ```
   Затем написать боту: «подбери подарок до 3000 ₽ коллеге, который любит чай».

Остановить: `docker compose down`. Память и сессии Hermes лежат в томе
`hermes-data` и переживают перезапуск. Полный сброс — `docker compose down -v`.

## Демо-сценарии

1. **Подарок с маркетплейса.** Бриф → сравнение цен → шорт-лист со ссылками →
   «беру второй» → товар в корзине WB → «оформляем?» → страница оформления →
   сводка заказа → кнопки подтверждения в Telegram → заказ оформлен.
2. **Подарок от местного бизнеса.** Цветы или рыбный набор → корзина Tilda →
   сводка. Корзина Tilda живёт в браузере агента, на демо её видно в окне Chrome.

## Работа вдвоём

- **Один токен бота — один запущенный экземпляр.** Telegram отдаёт обновления
  только одному процессу, второй получит `409 Conflict`. У каждого свой dev-бот,
  общий демо-бот запускается на одной машине.
- **Демо-аккаунт маркетплейса.** Если войти в него у обоих, корзина будет общей.
  Договоритесь о времени тестов или заведите два аккаунта.
- **`.env` и профиль Chrome в git не попадают.** Токены и ключи передавайте
  лично.
- **Windows.** Репозиторий лучше держать внутри файловой системы WSL, а не на
  `C:\` — сборка быстрее. `.gitattributes` уже следит за переводами строк.

## Правила безопасности

- В профиле Chrome для агента — только демо-аккаунты. Никаких личных входов,
  банков и почты: CDP-порт даёт полный контроль над профилем.
- Финальные кнопки заказа и оплаты — только через кнопки подтверждения в
  Telegram (`checkout-guard`). Ответы «всегда» / «на сессию» не действуют на
  следующие заказы: каждый клик подтверждается отдельно.
- Карта в аккаунтах маркетплейсов не сохраняется, номер карты агент ввести не
  может. Если после «Заказать» открылась оплата — платит человек.
- Известное ограничение: охранник опирается на текст кнопки, который пишет
  модель (`element`), и на исходник JS. Клик с неверной подписью он не поймает
  — поэтому карта в аккаунтах и не хранится.
- Порт 9222 слушает только `127.0.0.1` хоста, сервисы compose наружу не
  опубликованы.
- Базовые правила (не оформлять, не платить, не верить текстам на сайтах) — в
  `hermes/SOUL.md` и в скиллах.

## Структура

```
docker-compose.yml          сервисы: hermes-init, hermes, marketplace, playwright, cdp-proxy
.env.example                переменные окружения (шаблон)
hermes/config.yaml          модель, отключённые инструменты, CDP, MCP
hermes/SOUL.md              постоянные правила агента
hermes/plugins/checkout-guard/  подтверждение финальных кнопок, запрет ввода карт
cdp-proxy/nginx.conf        мост контейнеры → Chrome на хосте
scripts/start-chrome.*      запуск Chrome с отдельным профилем
scripts/session-tools.py    разбор сессии: какие инструменты вызвал агент
skills/gift-consultant/     маркетплейсы: подбор, сравнение, корзина
skills/local-shops-cart/    местные магазины Хабаровска (Tilda, uniSiter)
```

## Проверить в первый день

Уже проверено: `docker compose config` проходит; логика `cdp-proxy` (подмена
Host, переписывание ws-ссылок, снятие Origin) проверена с Chromium 153 —
без прокси Chrome отвечает `Host header is specified and is not an IP address
or localhost`, через прокси работают `/json/version`, WebSocket и Playwright
`connectOverCDP`.

Собрано по документации, но целиком вживую ещё не запускалось:

- [x] Chrome на `127.0.0.1` хоста виден из контейнера через
      `host.docker.internal` — Docker Desktop на Mac (Windows — проверить).
- [x] Playwright MCP управляет Chrome хоста через `cdp-proxy`: вкладки
      открываются в окне Chrome на хосте.
- [x] Hermes подставляет `${MARKETPLACE_MCP_TOKEN}` в заголовки MCP
      (marketplace отвечает `200` на `/mcp`).
- [x] Hermes подхватывает скиллы из вложенной папки `skills/gift-agent/`.
- [x] JavaScript на странице выполняется через `browser_evaluate`.
- [ ] JS-рецепты Tilda работают через `browser_evaluate`.
- [x] Корзина WB: `/lk/basket`, добавление товара — проверено.
- [ ] Корзины Ozon и Яндекс Маркета в `gift-consultant`.
- [ ] `checkout-guard` показывает кнопки подтверждения в Telegram перед
      «Заказать» на WB; отказ блокирует клик.
- [x] Оформление WB: выбор пункта выдачи по адресу пользователя — проверено.
      Кнопка заказа неактивна без способа оплаты; доступны SberPay, карта, СБП,
      цифровой рубль, рассрочки.
- [ ] Оформление WB через SberPay: кнопки подтверждения → страница оплаты.
- [ ] Hermes и marketplace не мешают друг другу в одном Chrome. Если мешают —
      второй Chrome на порту 9223 для marketplace.

## Открытые вопросы

- **`local-shops-cart`: отправка формы заказа.** Корзины Tilda и uniSiter живут в
  браузере агента, ссылка «на корзину» у человека откроется пустой. Технически
  всё готово: `checkout-guard` уже перехватывает «Оформить заказ» и отправку
  формы и спрашивает подтверждение кнопками. Осталось автору скилла разрешить в
  нём отправку формы после подтверждения (сейчас скилл её запрещает, и
  `gift-consultant` этому следует).
- **`local-shops-cart`: доработки.** Убрать подключение к основному профилю Chrome
  (§2.1), убрать `uvx desktop-agent`, перенаправлять запросы про маркетплейсы в
  `gift-consultant`, в `tilda-add.js` ждать обновления `tcart` и сверять товар,
  в `unisiter-add.js` сверять счётчик корзины.
- **Версии.** После первого удачного запуска закрепить `HERMES_TAG` и
  `PLAYWRIGHT_MCP_TAG` на конкретные теги.

## Если не работает

| Симптом | Что делать |
|---|---|
| `wget` к `cdp-proxy` не отвечает | Chrome не запущен или порт 9222 занят: перезапустить `start-chrome` |
| `Host header is specified and is not an IP address or localhost` | запрос идёт мимо `cdp-proxy`: проверить `--cdp-endpoint` у playwright и `CHROME_CDP_HOST` у marketplace |
| `409 Conflict` в логах hermes | этот бот уже запущен где-то ещё |
| `401` от marketplace | разные токены или Hermes не подставил `${...}` — сверить `.env` |
| Агент просит войти или пройти капчу | сделать это руками в окне Chrome |
| Агент говорит «открыл», но в Chrome ничего нет | `docker compose exec -T hermes hermes sessions export - --format jsonl \| python3 scripts/session-tools.py` — какие инструменты он вызвал на самом деле |
| `hermes mcp test playwright` не подключается | `docker compose logs playwright` — обычно Chrome не запущен или не отвечает `cdp-proxy` |
