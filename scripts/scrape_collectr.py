"""
Scrape the user's Collectr portfolio -> data/portfolio.json + data/cards/*.jpg.

Strategy:
1. Launch Chromium. Reuse data/storage_state.json if it exists; else run headed
   so the user can log in interactively, then persist storage state.
2. Navigate to the portfolio page. Capture every /api/* XHR response.
3. Recurse through captured JSON to find card-shaped objects (heuristic:
   objects with >=3 of {name, set, card_number, price, image_url} fields).
4. If no usable XHRs are captured, fall back to DOM scrape.
5. Download each card's catalog image to data/cards/{id}.jpg.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CARDS_DIR = DATA_DIR / "cards"
STORAGE_STATE = DATA_DIR / "storage_state.json"
PORTFOLIO_URL = "https://app.getcollectr.com/portfolio/products"
PORTFOLIO_JSON = DATA_DIR / "portfolio.json"
RAW_XHRS = DATA_DIR / "raw_xhrs.json"


# ---------------------------------------------------------------------------
# XHR -> card extraction
# ---------------------------------------------------------------------------

CARD_KEY_HINTS = {
    "name", "cardname", "title",
    "set", "setcode", "setname", "setid",
    "number", "cardnumber", "card_number",
    "price", "marketprice", "market_price", "currentprice", "current_price",
    "image", "imageurl", "image_url", "imagesrc", "thumbnail",
}


def looks_like_card(item: dict) -> bool:
    if not isinstance(item, dict):
        return False
    lower_keys = {str(k).lower() for k in item.keys()}
    hits = sum(1 for k in CARD_KEY_HINTS if k in lower_keys)
    return hits >= 3


def extract_card_items(data, depth: int = 0) -> list[dict]:
    """Recursive scan for list-of-dict structures whose elements look like cards."""
    if depth > 8:
        return []
    if isinstance(data, list):
        if data and isinstance(data[0], dict) and looks_like_card(data[0]):
            return [x for x in data if isinstance(x, dict)]
        out: list[dict] = []
        for item in data:
            out.extend(extract_card_items(item, depth + 1))
        return out
    if isinstance(data, dict):
        out = []
        for v in data.values():
            out.extend(extract_card_items(v, depth + 1))
        return out
    return []


def _get(item: dict, keys: list[str], default=None):
    for k in keys:
        for ik, v in item.items():
            if str(ik).lower() == k.lower() and v is not None:
                return v
    return default


def normalize_card(item: dict, fallback_index: int) -> dict | None:
    # Collectr's real schema uses product_name / catalog_group / market_price /
    # image_url / product_id. Generic fallbacks let this keep working if they
    # rename fields later.
    name = _get(item, ["product_name", "productName", "name", "cardName", "title"])
    if not name:
        return None
    raw_id = _get(item, ["product_id", "productId", "id", "_id", "sku"])
    card_id = str(raw_id) if raw_id else f"card-{fallback_index:04d}"
    # Prefer market_price; fall back to user's price_override if they set one
    price = _get(item, ["market_price", "marketPrice", "currentPrice", "current_price", "price", "value"])
    if price is None:
        price = _get(item, ["price_override", "priceOverride"])
    return {
        "id": card_id,
        "name": str(name).strip(),
        "set_code": _get(item, ["catalog_group", "catalogGroup", "setCode", "set_code", "set", "setId", "setName"]),
        "set_id": _get(item, ["catalog_group_id", "catalogGroupId"]),
        "category": _get(item, ["catalog_category_name", "catalogCategoryName"]),  # Pokemon / YuGiOh / etc
        "card_number": _get(item, ["card_number", "cardNumber", "number"]),
        "condition": _get(item, ["card_condition", "cardCondition", "condition", "grade"]),
        "rarity": _get(item, ["rarity"]),
        "product_sub_type": _get(item, ["product_sub_type", "productSubType"]),
        "quantity": _get(item, ["quantity", "count", "qty"], 1),
        "purchase_price": _get(
            item,
            ["purchasePrice", "purchase_price", "costBasis", "cost", "acquiredPrice"],
        ),
        "current_market_price": float(price) if price is not None else None,
        "image_url": _get(
            item,
            ["image_url", "imageUrl", "image", "thumbnail", "imageSrc", "cardImage"],
        ),
        "user_owned_product_id": _get(item, ["user_owned_product_id", "userOwnedProductId"]),
    }


def parse_from_xhrs(captured: list[dict]) -> list[dict]:
    seen: set[str] = set()
    cards: list[dict] = []
    for cap in captured:
        for item in extract_card_items(cap["data"]):
            card = normalize_card(item, len(cards))
            if card and card["id"] not in seen:
                seen.add(card["id"])
                cards.append(card)
    return cards


# ---------------------------------------------------------------------------
# DOM fallback
# ---------------------------------------------------------------------------

DOM_SCRAPE_JS = r"""
() => {
  const results = [];
  const nodes = document.querySelectorAll(
    '[class*="card"], [class*="Card"], [class*="product"], [class*="Product"], li, article'
  );
  const seen = new Set();
  for (const el of nodes) {
    const img = el.querySelector('img');
    if (!img || !img.src) continue;
    if (seen.has(img.src)) continue;
    const text = el.innerText || "";
    const priceMatch = text.match(/\$\s*([0-9]+(?:[,.][0-9]{2})?)/);
    if (!priceMatch) continue;
    const titleEl = el.querySelector(
      '[class*="name"], [class*="Name"], [class*="title"], [class*="Title"], h2, h3, h4'
    );
    const name = (titleEl ? titleEl.innerText : text.split('\n')[0]).trim();
    if (!name) continue;
    seen.add(img.src);
    results.push({
      name: name.slice(0, 140),
      image_url: img.src,
      current_market_price: parseFloat(priceMatch[1].replace(',', '.')),
      raw_text: text.slice(0, 400),
    });
  }
  return results;
}
"""


def parse_from_dom(page) -> list[dict]:
    print("→ XHR capture yielded nothing usable. Falling back to DOM scrape.")
    items = page.evaluate(DOM_SCRAPE_JS)
    for i, it in enumerate(items):
        it["id"] = f"dom-{i:04d}"
    return items


# ---------------------------------------------------------------------------
# Image download
# ---------------------------------------------------------------------------

def download_image(url: str, dest: Path) -> bool:
    if dest.exists():
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            if resp.status != 200:
                return False
            dest.write_bytes(resp.read())
        return True
    except Exception as e:  # noqa: BLE001
        print(f"  ✗ {url}: {e}")
        return False


def safe_suffix(url: str) -> str:
    path = urlparse(url).path.lower()
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        if path.endswith(ext):
            return ".jpg" if ext == ".jpeg" else ext
    return ".jpg"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def scroll_to_bottom(page, max_rounds: int = 60) -> None:
    """Lazy-load everything by scrolling until page stops growing."""
    last_height = 0
    stable_rounds = 0
    for _ in range(max_rounds):
        height = page.evaluate("document.body.scrollHeight")
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(800)
        if height == last_height:
            stable_rounds += 1
            if stable_rounds >= 3:
                break
        else:
            stable_rounds = 0
        last_height = height


def main() -> None:
    CARDS_DIR.mkdir(parents=True, exist_ok=True)
    captured: list[dict] = []

    with sync_playwright() as p:
        # Always headed: Collectr serves /service-unavailable to headless
        # chromium. Viewing a window is cheap; the login poll is a no-op if
        # the saved storage state is still valid.
        headless = False
        browser = p.chromium.launch(headless=headless)
        ctx_kwargs = {
            "viewport": {"width": 1400, "height": 900},
            "user_agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        }
        if STORAGE_STATE.exists():
            ctx_kwargs["storage_state"] = str(STORAGE_STATE)
        context = browser.new_context(**ctx_kwargs)
        page = context.new_page()

        def on_response(resp):
            # Capture every JSON response, not just /api/* — Collectr might use a
            # different path convention (/graphql, /v1/, subdomain, …).
            url = resp.url
            ct = (resp.headers.get("content-type") or "").lower()
            if "application/json" not in ct and not url.endswith(".json"):
                return
            try:
                data = resp.json()
            except Exception:
                return
            # Only keep payloads that are reasonably sized (skip tiny 401s etc.)
            captured.append({"url": url, "status": resp.status, "data": data})

        page.on("response", on_response)

        print(f"→ Navigating to {PORTFOLIO_URL}")
        page.goto(PORTFOLIO_URL, wait_until="domcontentloaded")

        # Let the SPA settle (client-side auth redirect, hydration, etc).
        try:
            page.wait_for_load_state("networkidle", timeout=15_000)
        except PlaywrightTimeout:
            pass
        page.wait_for_timeout(2500)
        print(f"   landed at: {page.url}")

        # Detect login state by hostname. Collectr uses Stytch magic-code (no
        # password input), so DOM checks are unreliable — but the hostname
        # pattern is clean: app.getcollectr.com = logged in, auth.* = login page.
        def is_logged_in() -> bool:
            try:
                url = (page.url or "").lower()
            except Exception:
                return False
            # Anywhere on the auth subdomain = not logged in.
            if "auth.getcollectr" in url:
                return False
            # Need to be on app.getcollectr.com with /portfolio in the path.
            return url.startswith("https://app.getcollectr.com/portfolio")

        if not headless and not is_logged_in():
            import time
            print(
                "\n→ Not logged in. Sign in via the browser window — I'll auto-detect "
                "when you reach the portfolio (up to 10 min)."
            )
            deadline = time.time() + 600
            last_url = page.url
            while not is_logged_in():
                if page.url != last_url:
                    print(f"   url: {page.url}")
                    last_url = page.url
                if time.time() > deadline:
                    sys.exit("✗ Login timeout. Re-run after signing in.")
                page.wait_for_timeout(2000)
            print(f"   → logged in, now at {page.url}")
            # Drive back to portfolio after login
            if "portfolio/products" not in page.url.lower():
                page.goto(PORTFOLIO_URL, wait_until="domcontentloaded")
                try:
                    page.wait_for_load_state("networkidle", timeout=15_000)
                except PlaywrightTimeout:
                    pass
                page.wait_for_timeout(2500)

        page.wait_for_timeout(1500)
        print("→ Scrolling to trigger lazy-load …")
        scroll_to_bottom(page)
        page.wait_for_timeout(2500)

        # Dump the final page HTML + URL for offline debugging.
        (DATA_DIR / "page.html").write_text(page.content(), encoding="utf-8")
        (DATA_DIR / "final_url.txt").write_text(page.url)
        print(f"   dumped DOM -> data/page.html  (final url: {page.url})")

        context.storage_state(path=str(STORAGE_STATE))
        print(f"→ Storage state saved to {STORAGE_STATE}")

        RAW_XHRS.write_text(json.dumps(captured, indent=2, default=str))
        print(f"→ Captured {len(captured)} JSON responses  (dumped to {RAW_XHRS.name})")
        # Sample of captured URLs to stdout for quick inspection
        seen_hosts = {}
        for cap in captured:
            from urllib.parse import urlparse
            host = urlparse(cap["url"]).netloc
            seen_hosts[host] = seen_hosts.get(host, 0) + 1
        for host, n in sorted(seen_hosts.items(), key=lambda kv: -kv[1]):
            print(f"     · {n:3d}  {host}")

        cards = parse_from_xhrs(captured)
        if not cards:
            cards = parse_from_dom(page)

        browser.close()

    if not cards:
        print("\n❌ No cards extracted. Inspect data/raw_xhrs.json or adjust DOM_SCRAPE_JS.")
        sys.exit(1)

    print(f"\n→ Extracted {len(cards)} cards. Downloading catalog images …")
    for i, card in enumerate(cards):
        url = card.get("image_url")
        if not url:
            continue
        dest = CARDS_DIR / f"{card['id']}{safe_suffix(url)}"
        if download_image(url, dest):
            card["local_image"] = str(dest.relative_to(BASE_DIR))
        if (i + 1) % 20 == 0:
            print(f"  … {i + 1}/{len(cards)}")

    PORTFOLIO_JSON.write_text(json.dumps(cards, indent=2, default=str))
    with_price = sum(1 for c in cards if c.get("current_market_price") is not None)
    with_image = sum(1 for c in cards if c.get("local_image"))
    print(
        f"\n✓ Saved {PORTFOLIO_JSON.name} "
        f"({with_price}/{len(cards)} with price, {with_image}/{len(cards)} with image)"
    )


if __name__ == "__main__":
    main()
