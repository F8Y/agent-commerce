// Tilda: добавить товар в корзину и вернуть состояние tcart.
// Выполнять на странице товара через eval (element.click(), не CDP-клик).
(() => {
  const selectors = ["a.t-store__prod-popup__btn", "a.t-btn.js-store"];
  let button = null;

  for (const selector of selectors) {
    const candidate = document.querySelector(selector);
    if (candidate) {
      button = candidate;
      break;
    }
  }

  if (!button) {
    button = [...document.querySelectorAll("a, button")].find((el) =>
      /^\s*(в корзину|купить)\s*$/i.test((el.innerText || "").trim()),
    );
  }

  if (!button) return { ok: false, reason: "кнопка «В корзину» не найдена" };

  button.click();

  let cart = {};
  try {
    cart = JSON.parse(localStorage.getItem("tcart") || "{}");
  } catch {
    cart = {};
  }

  return {
    ok: true,
    clicked: (button.innerText || "").trim(),
    products: Array.isArray(cart.products) ? cart.products.length : 0,
    amount: cart.amount ?? null,
    total: cart.total ?? null,
  };
})();
