// Tilda: add the open product to the cart and confirm through localStorage.tcart.
// Pass the whole text as `function` to browser_evaluate on a product page or popup.
async () => {
  const readCart = () => {
    try { return JSON.parse(localStorage.getItem("tcart") || "{}"); } catch { return {}; }
  };
  const qty = (cart) => (cart.products || []).reduce((sum, p) => sum + (Number(p.quantity) || 1), 0);
  const clean = (text) => (text || "").replace(/\s+/g, " ").trim();

  // Scope to the open product card so recommendation blocks are never clicked.
  const card =
    document.querySelector(".t-store__prod-popup__container") ||
    document.querySelector(".t-store__product-snippet") ||
    document.querySelector(".js-store-product") ||
    document;
  const expected = clean(card.querySelector(".js-store-prod-name, .js-product-name, h1")?.innerText);
  const button =
    card.querySelector("a.t-store__prod-popup__btn, a.t-btn.js-store, .js-store-prod-btn") ||
    [...card.querySelectorAll("a, button")].find((el) => /^(в корзину|купить)$/i.test(clean(el.innerText)));
  if (!button) return { ok: false, reason: "кнопка «В корзину» не найдена в карточке товара", expected };

  const before = qty(readCart());
  button.click();

  // Tilda writes tcart asynchronously: wait up to ~4 s.
  for (let i = 0; i < 20; i += 1) {
    await new Promise((resolve) => setTimeout(resolve, 200));
    const cart = readCart();
    if (qty(cart) > before) {
      const last = (cart.products || []).at(-1) || {};
      const name = clean(last.name);
      return {
        ok: true,
        added: name,
        expected,
        matchesPage: !!expected && name.toLowerCase().includes(expected.toLowerCase().slice(0, 20)),
        items: qty(cart),
        total: cart.prodamount ?? cart.amount ?? cart.total ?? null,
        price: last.amount ?? null,
        options: last.options || [],
      };
    }
  }
  return { ok: false, reason: "корзина не изменилась за 4 с", expected };
}
