// uniSiter (shop.fcska.ru): добавить товар в корзину.
// Важно: не брать первую кнопку «Купить» — в DOM раньше идут блоки «похожих товаров».
(() => {
  const button = document.querySelector(
    'form[action$="ajax_buy.php"] #buy_btn_cont input[type=submit]',
  );
  if (!button) return { ok: false, reason: "основная кнопка «Купить» не найдена" };

  button.click();
  return {
    ok: true,
    clicked: button.value || "Купить",
    note: "проверить /shop/cart/ и количество позиции",
  };
})();
