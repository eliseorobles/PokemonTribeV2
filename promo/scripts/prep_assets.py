"""
Copy curated assets into promo/public/ and write stats.json.

Picks the top N cards that have BOTH a card image and a heatmap, sorted by
price desc. Output:
    promo/public/cards/{id}.jpg
    promo/public/heatmaps/{id}.png
    promo/public/stats/null-distribution.png
    promo/public/stats/correlation-bars.png
    promo/public/stats/scatter.png
    promo/public/stats.json
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent  # tribev2 demo/
PROMO = Path(__file__).resolve().parent.parent        # tribev2 demo/promo/

DATA = REPO / "data"
SITE_HEATMAPS = REPO / "site" / "assets" / "heatmaps"
POSTS_ASSETS = REPO / "posts" / "assets"

PUB = PROMO / "public"
PUB_CARDS = PUB / "cards"
PUB_HEAT = PUB / "heatmaps"
PUB_STATS_DIR = PUB / "stats"

N_CARDS = 7


def main() -> None:
    PUB_CARDS.mkdir(parents=True, exist_ok=True)
    PUB_HEAT.mkdir(parents=True, exist_ok=True)
    PUB_STATS_DIR.mkdir(parents=True, exist_ok=True)

    analysis = json.loads((DATA / "analysis.json").read_text())
    portfolio = {c["id"]: c for c in json.loads((DATA / "portfolio.json").read_text())}

    # Pick cards: sort per_card by actual_price desc, keep only those with both
    # a real image on disk + a heatmap on disk, take first N.
    per_card = sorted(analysis["per_card"], key=lambda c: -c["actual_price"])
    picked = []
    for c in per_card:
        if len(picked) >= N_CARDS:
            break
        pid = c["id"]
        heat_src = SITE_HEATMAPS / f"{pid}.png"
        full = portfolio.get(pid, {})
        local_img = full.get("local_image")
        card_src = REPO / local_img if local_img else None
        if not heat_src.exists():
            continue
        if not card_src or not card_src.exists():
            continue
        picked.append({
            "id": pid,
            "name": c["name"],
            "price": c["actual_price"],
            "card_src": card_src,
            "heat_src": heat_src,
            "card_dst": PUB_CARDS / f"{pid}{card_src.suffix.lower()}",
            "heat_dst": PUB_HEAT / f"{pid}.png",
        })

    print(f"→ picked {len(picked)} cards:")
    for p in picked:
        print(f"   {p['id']:>8s}  ${p['price']:>7.2f}  {p['name']}")

    # Copy cards + heatmaps
    for p in picked:
        shutil.copy2(p["card_src"], p["card_dst"])
        shutil.copy2(p["heat_src"], p["heat_dst"])

    # Copy pre-rendered stat PNGs
    for name in ("null-distribution.png", "correlation-bars.png", "scatter.png"):
        src = POSTS_ASSETS / name
        if src.exists():
            shutil.copy2(src, PUB_STATS_DIR / name)
            print(f"→ copied stats/{name}")
        else:
            print(f"   ⚠ missing {src}")

    # Stats JSON for scenes to consume
    reg = analysis["regression"]
    top = analysis["correlations"][0]
    total_value = sum(
        float(c.get("current_market_price") or 0)
        for c in portfolio.values()
    )
    stats = {
        "n_cards": analysis["n_cards"],
        "n_rois": analysis["n_rois"],
        "r2_real": reg["loo_r2_real"],
        "r2_null_mean": reg["loo_r2_shuffled_mean"],
        "r2_null_p95": reg["loo_r2_shuffled_p95"],
        "percentile_in_null": reg["real_percentile_in_null"],
        "top_roi": top["roi"],
        "top_roi_r": top["r"],
        "total_value": total_value,
        "cards": [
            {
                "id": p["id"],
                "name": p["name"],
                "price": p["price"],
                "card_path": f"cards/{p['card_dst'].name}",
                "heatmap_path": f"heatmaps/{p['id']}.png",
            }
            for p in picked
        ],
    }
    (PUB / "stats.json").write_text(json.dumps(stats, indent=2))
    print(f"\n✓ stats.json: n={stats['n_cards']}, R²={stats['r2_real']:+.3f}, "
          f"top={stats['top_roi']} (r={stats['top_roi_r']:+.2f}), "
          f"total=${stats['total_value']:,.2f}")


if __name__ == "__main__":
    main()
