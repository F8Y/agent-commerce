#!/usr/bin/env node
// CLI локальных магазинов: реестр, карточка магазина, диагностика.
// Браузерные действия (open/eval/click) выполняет agent-browser или инструмент
// самого агента — этот CLI только читает реестр и ничего не отправляет на сайты.

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const HERE = dirname(fileURLToPath(import.meta.url));
const REGISTRY = join(HERE, "..", "references", "shops.json");

function loadRegistry() {
  return JSON.parse(readFileSync(REGISTRY, "utf8"));
}

function parseArgs(argv) {
  const positional = [];
  const opts = {};
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg.startsWith("--")) {
      const key = arg.slice(2);
      const next = argv[i + 1];
      if (next !== undefined && !next.startsWith("--")) {
        opts[key] = next;
        i += 1;
      } else {
        opts[key] = true;
      }
    } else {
      positional.push(arg);
    }
  }
  return { positional, opts };
}

function doctor() {
  const report = { ok: true, checks: [] };
  const add = (name, ok, detail, required = true) => {
    report.checks.push({ name, ok, detail, required });
    if (!ok && required) report.ok = false;
  };

  const major = Number(process.versions.node.split(".")[0]);
  add("node", major >= 20, process.versions.node);

  try {
    const registry = loadRegistry();
    add("registry", true, `${registry.shops.length} магазинов, обновлён ${registry.updated}`);
  } catch (error) {
    add("registry", false, error.message);
  }

  // agent-browser нужен только для режима B; если у агента свой браузер — не критично.
  const bin = process.env.AGENT_BROWSER_BIN || "agent-browser";
  const result = spawnSync(bin, ["--version"], { encoding: "utf8", shell: true });
  const version = `${result.stdout || ""}${result.stderr || ""}`.trim();
  add(
    "agent-browser",
    result.status === 0,
    version || "не найден (нужен только для режима B: npm i -g agent-browser)",
    false,
  );

  report.modes = {
    A: "свой браузер агента: open / eval / click по селекторам из shops.json",
    B: "agent-browser: постоянный профиль, open / eval / click / state save",
  };
  return report;
}

function filterShops(registry, opts) {
  let list = registry.shops;

  if (opts.can) {
    const can = String(opts.can);
    if (!["add", "order", "browse"].includes(can)) {
      throw new Error("--can: add | order | browse");
    }
    list = list.filter((shop) => {
      if (can === "add") return shop.capabilities.addToCart;
      if (can === "order") return ["guest", "form"].includes(shop.capabilities.checkout);
      return shop.capabilities.browse;
    });
  }

  if (opts.platform) {
    const platform = String(opts.platform).toLowerCase();
    list = list.filter((shop) => shop.platform.toLowerCase().includes(platform));
  }

  const category = String(opts.category || "").toLowerCase();
  if (category) {
    list = list.filter((shop) =>
      [...(shop.categories || []), ...(shop.keywords || [])].some((term) =>
        term.toLowerCase().includes(category),
      ),
    );
  }

  return list;
}

function brief(shop) {
  return {
    id: shop.id,
    name: shop.name,
    url: shop.url,
    platform: shop.platform,
    status: shop.status,
    categories: shop.categories,
    keywords: shop.keywords || [],
    giftFor: shop.giftFor || [],
    priceHint: shop.priceHint,
    canAddToCart: shop.capabilities.addToCart,
    checkout: shop.capabilities.checkout,
    cart: shop.cart,
    checkoutFields: shop.checkoutFields,
    constraints: shop.constraints,
    notes: shop.notes,
  };
}

const [, , cmd = "shops", ...rest] = process.argv;
const { positional, opts } = parseArgs(rest);

try {
  if (cmd === "doctor") {
    console.log(JSON.stringify(doctor(), null, 2));
  } else if (cmd === "shops") {
    const registry = loadRegistry();
    const list = filterShops(registry, opts);
    console.log(
      JSON.stringify(
        {
          updated: registry.updated,
          city: registry.city,
          scope: registry.scope,
          note: registry.assortmentNote,
          orderPolicy: registry.orderPolicy,
          count: list.length,
          shops: list.map(brief),
        },
        null,
        2,
      ),
    );
  } else if (cmd === "show") {
    const id = positional[0];
    if (!id) throw new Error("использование: show <id>");
    const registry = loadRegistry();
    const shop = registry.shops.find((item) => item.id === id);
    if (!shop) throw new Error(`магазин не найден: ${id}`);
    console.log(JSON.stringify(shop, null, 2));
  } else if (cmd === "platforms") {
    const registry = loadRegistry();
    const counts = {};
    for (const shop of registry.shops) counts[shop.platform] = (counts[shop.platform] || 0) + 1;
    console.log(JSON.stringify({ count: registry.shops.length, platforms: counts }, null, 2));
  } else {
    throw new Error(
      `неизвестная команда: ${cmd || "(пусто)"}\n` +
        "doctor | shops | shops --can add|order|browse | shops --category <текст> | shops --platform <движок> | show <id> | platforms",
    );
  }
} catch (error) {
  console.error(JSON.stringify({ ok: false, error: error.message }, null, 2));
  process.exitCode = 1;
}
