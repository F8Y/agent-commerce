// uniSiter (shop.fcska.ru): add the current product and confirm through the cart counter.
// Pass the whole text as `function` to browser_evaluate on a product page.
// The main "Купить" button lives inside form[action$="ajax_buy.php"]; "similar products"
// blocks have their own buy buttons earlier in the DOM and must not be clicked.
async () => {
  const cartCount = async () => {
    try {
      const response = await fetch("/shop/ajax_cart.php", { credentials: "same-origin" });
      const data = JSON.parse(await response.text());
      return Number(data.count) || 0;
    } catch {
      return null;
    }
  };

  const button = document.querySelector('form[action$="ajax_buy.php"] #buy_btn_cont input[type=submit]');
  if (!button) return { ok: false, reason: "основная кнопка «Купить» не найдена" };

  const before = await cartCount();
  button.click();

  // Poll gently: at most 10 same-origin requests over ~5 s.
  for (let i = 0; i < 10; i += 1) {
    await new Promise((resolve) => setTimeout(resolve, 500));
    const after = await cartCount();
    if (before !== null && after !== null && after > before) {
      return { ok: true, before, after, cart: "/shop/cart/" };
    }
  }
  return { ok: false, reason: "счётчик корзины не изменился", before };
}
