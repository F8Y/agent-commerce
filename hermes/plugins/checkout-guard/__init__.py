"""checkout-guard: code-level human-in-the-loop for the gift agent.

The model cannot skip this: Hermes runs pre_tool_call before every tool call.

* Final order/payment buttons ("Заказать", "Оформить заказ", "Оплатить", ...) ->
  {"action": "approve"}: Hermes asks the user with inline buttons in Telegram;
  deny or timeout blocks the call.
* Card numbers in typed or evaluated text -> {"action": "block"}.
* browser_click without a human-readable `element` -> {"action": "block"} with a
  hint, so every click states what it presses and the phrase check above works.
* browser_evaluate reading document.cookie or calling an absolute external URL
  (fetch, XHR, sendBeacon, WebSocket, image beacons, navigation) -> block.

Site-specific rules (which page is the real checkout, which link is a trap) live
in the skill, not here: the guard stays a generic mechanism.

Known limitation: the check trusts the `element` text the model writes and the
JS source it sends; a mislabeled click is not caught. Covered by the skill rules
and by keeping no saved card in the accounts.
"""
from __future__ import annotations

import re
import uuid
from typing import Any, Iterator, Optional

# Playwright MCP tool names arrive prefixed (e.g. "mcp__playwright__browser_click").
GUARDED_SUFFIXES = (
    "browser_click",
    "browser_press_key",
    "browser_evaluate",
    "browser_fill_form",
    "browser_type",
    "browser_select_option",
)

# Lowercase fragments of final order/payment controls. "К оформлению" (go to the
# checkout page) intentionally does not match: opening the checkout page is safe.
FINAL_ACTION_PHRASES = (
    "оформить заказ",
    "оформить",
    "подтвердить заказ",
    "отправить заказ",
    "отправить",
    "заказать",
    "оплатить",
    "перейти к оплате",
    "купить сейчас",
    "купить в 1 клик",
    "купить в один клик",
    "place order",
    "confirm order",
    "submit order",
    "pay now",
)

# JS that submits a form is treated as a final action regardless of wording.
FORM_SUBMIT_MARKERS = (".submit(", "requestsubmit(")

CARD_CANDIDATE = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")

# Page JS must not talk to the outside world: from a logged-in marketplace page
# that is how cookies or personal data leak (and how a prompt injection would
# exfiltrate them). Same-origin relative requests (fetch('/shop/cart.php')) stay allowed.
NETWORK_CALL = re.compile(
    r"(fetch\s*\(|xmlhttprequest|sendbeacon|new\s+websocket|new\s+eventsource|"
    r"new\s+image\s*\(|\.src\s*=|window\.open\s*\(|location(\.href)?\s*=)",
    re.IGNORECASE,
)
ABSOLUTE_URL = re.compile(r"(https?:)?//[a-z0-9.-]+\.[a-z]{2,}", re.IGNORECASE)
SECRET_ACCESS = re.compile(r"document\s*\.\s*cookie", re.IGNORECASE)


def _strings(value: Any) -> Iterator[str]:
    """Every string inside nested args (dicts, lists)."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _strings(item)


def _luhn_ok(digits: str) -> bool:
    total, parity = 0, len(digits) % 2
    for index, char in enumerate(digits):
        number = int(char)
        if index % 2 == parity:
            number *= 2
            if number > 9:
                number -= 9
        total += number
    return total % 10 == 0


def _has_card_number(text: str) -> bool:
    for match in CARD_CANDIDATE.finditer(text):
        digits = re.sub(r"\D", "", match.group())
        if 13 <= len(digits) <= 19 and _luhn_ok(digits):
            return True
    return False


def _matched_phrase(text: str) -> Optional[str]:
    lowered = text.lower()
    for phrase in FINAL_ACTION_PHRASES:
        if phrase in lowered:
            return phrase
    if any(marker in lowered.replace(" ", "") for marker in FORM_SUBMIT_MARKERS):
        return "отправка формы"
    return None


def _on_pre_tool_call(tool_name: str = "", args: Any = None, **_: Any) -> Optional[dict]:
    suffix = next((s for s in GUARDED_SUFFIXES if tool_name.endswith(s)), None)
    if suffix is None:
        return None
    args = args if isinstance(args, dict) else {}
    text = "\n".join(_strings(args))

    if _has_card_number(text):
        return {
            "action": "block",
            "message": "checkout-guard: ввод номера банковской карты запрещён. "
                       "Оплату проводит человек — сообщи пользователю, что нужно оплатить самому.",
        }

    if suffix == "browser_evaluate":
        source = str(args.get("function") or "")
        if SECRET_ACCESS.search(source):
            return {
                "action": "block",
                "message": "checkout-guard: доступ к document.cookie из JavaScript запрещён.",
            }
        if NETWORK_CALL.search(source) and ABSOLUTE_URL.search(source):
            return {
                "action": "block",
                "message": "checkout-guard: JavaScript на странице не должен обращаться к внешним "
                           "адресам. Пользуйся данными самой страницы или инструментами marketplace.",
            }

    if suffix == "browser_click" and not str(args.get("element") or "").strip():
        return {
            "action": "block",
            "message": "checkout-guard: укажи в `element` видимый текст кнопки или ссылки "
                       "(например «В корзину») и повтори клик.",
        }

    phrase = _matched_phrase(text)
    if phrase is None:
        return None

    label = str(args.get("element") or "").strip() or phrase
    return {
        "action": "approve",
        "message": f"Агент хочет нажать «{label[:80]}». Это может оформить заказ или списать деньги. "
                   "Подтвердить?",
        # Unique per call: "always"/"session" answers cannot pre-approve future orders.
        "rule_key": f"checkout-guard:{uuid.uuid4().hex}",
    }


def register(ctx) -> None:
    ctx.register_hook("pre_tool_call", _on_pre_tool_call)
