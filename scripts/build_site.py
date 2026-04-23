"""
Render the static site from data/portfolio.json + data/analysis.json.

Outputs:
  site/index.html
  site/assets/cards/{id}.jpg   (card images, copied from data/cards)
  site/assets/heatmaps/{id}.png (already produced by render_heatmaps.py)
  site/assets/roi_correlation.png (already produced)
"""

from __future__ import annotations

import datetime as dt
import html
import json
import shutil
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SITE_DIR = BASE_DIR / "site"
TEMPLATES_DIR = BASE_DIR / "templates"
CARDS_SRC = DATA_DIR / "cards"
CARDS_DST = SITE_DIR / "assets" / "cards"
HEATMAP_DIR = SITE_DIR / "assets" / "heatmaps"

PORTFOLIO_JSON = DATA_DIR / "portfolio.json"
ANALYSIS_JSON = DATA_DIR / "analysis.json"


# ---------------------------------------------------------------------------
# SVG chart helpers (no JS — inline SVG only)
# ---------------------------------------------------------------------------

def make_bar_chart_svg(top_corrs: list[dict], width: int = 460, row_h: int = 26) -> str:
    """Horizontal bar chart of signed Pearson r for top ROIs by |r|."""
    rows = top_corrs[:10]
    pad_l, pad_r, pad_t, pad_b = 110, 50, 16, 28
    plot_w = width - pad_l - pad_r
    height = pad_t + pad_b + row_h * len(rows)
    rmax = max(0.05, max(abs(r["r"]) for r in rows)) * 1.1
    cx = pad_l + plot_w / 2

    def x_of(r): return cx + (r / rmax) * (plot_w / 2)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="100%" style="max-width:{width}px;height:auto;">'
    ]
    # Center axis (zero line)
    parts.append(
        f'<line class="axis-line" x1="{cx}" x2="{cx}" '
        f'y1="{pad_t}" y2="{height - pad_b}"/>'
    )
    # Tick labels for r at -rmax/2, 0, rmax/2 rounded
    for tick in (-rmax * 0.8, -rmax * 0.4, 0.0, rmax * 0.4, rmax * 0.8):
        x = x_of(tick)
        parts.append(
            f'<line class="grid-line" x1="{x:.1f}" x2="{x:.1f}" '
            f'y1="{pad_t}" y2="{height - pad_b}"/>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{height - pad_b + 14}" text-anchor="middle">'
            f'{tick:+.2f}</text>'
        )
    # Bars
    for i, c in enumerate(rows):
        y = pad_t + i * row_h + 4
        x_start = cx if c["r"] >= 0 else x_of(c["r"])
        bw = abs(x_of(c["r"]) - cx)
        cls = "bar-pos" if c["r"] >= 0 else "bar-neg"
        parts.append(
            f'<rect class="{cls}" x="{x_start:.1f}" y="{y}" '
            f'width="{bw:.1f}" height="{row_h - 8}" rx="2"/>'
        )
        # ROI name (left of axis)
        parts.append(
            f'<text x="{pad_l - 10}" y="{y + (row_h - 8) / 2 + 4}" '
            f'text-anchor="end" class="bar-label">{html.escape(c["roi"])}</text>'
        )
        # r value (right of bar)
        side_x = (x_of(c["r"]) + 6) if c["r"] >= 0 else (x_of(c["r"]) - 6)
        anchor = "start" if c["r"] >= 0 else "end"
        parts.append(
            f'<text x="{side_x:.1f}" y="{y + (row_h - 8) / 2 + 4}" '
            f'text-anchor="{anchor}">r={c["r"]:+.2f}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def make_scatter_svg(per_card: list[dict], top_roi: str, width: int = 460, height: int = 360) -> str:
    pad_l, pad_r, pad_t, pad_b = 50, 16, 16, 36

    xs = [c["roi_top_value"] for c in per_card]
    ys = [c["log_actual"] for c in per_card]
    if not xs or not ys:
        return ""

    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    if xmax - xmin < 1e-9: xmax += 1e-3
    if ymax - ymin < 1e-9: ymax += 1e-3
    xmin -= (xmax - xmin) * 0.05
    xmax += (xmax - xmin) * 0.05
    ymin -= (ymax - ymin) * 0.05
    ymax += (ymax - ymin) * 0.05

    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b

    def sx(x): return pad_l + (x - xmin) / (xmax - xmin) * plot_w
    def sy(y): return pad_t + plot_h - (y - ymin) / (ymax - ymin) * plot_h

    # OLS line on (x, y)
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    den = sum((xs[i] - mx) ** 2 for i in range(n))
    slope = num / den if abs(den) > 1e-12 else 0.0
    intercept = my - slope * mx

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="100%" style="max-width:{width}px;height:auto;">'
    ]
    # Axes
    parts.append(
        f'<line class="axis-line" x1="{pad_l}" x2="{width - pad_r}" '
        f'y1="{height - pad_b}" y2="{height - pad_b}"/>'
        f'<line class="axis-line" x1="{pad_l}" x2="{pad_l}" '
        f'y1="{pad_t}" y2="{height - pad_b}"/>'
    )
    # Y ticks (3): show as actual price (exp(y))
    for frac in (0.0, 0.5, 1.0):
        y_val = ymin + (ymax - ymin) * frac
        y_pix = sy(y_val)
        parts.append(
            f'<line class="grid-line" x1="{pad_l}" x2="{width - pad_r}" '
            f'y1="{y_pix:.1f}" y2="{y_pix:.1f}"/>'
            f'<text x="{pad_l - 6}" y="{y_pix + 4:.1f}" text-anchor="end">'
            f'${pow(2.71828, y_val):.0f}</text>'
        )
    # X ticks (3)
    for frac in (0.0, 0.5, 1.0):
        x_val = xmin + (xmax - xmin) * frac
        x_pix = sx(x_val)
        parts.append(
            f'<text x="{x_pix:.1f}" y="{height - pad_b + 14}" text-anchor="middle">'
            f'{x_val:+.2f}</text>'
        )
    parts.append(
        f'<text x="{pad_l + plot_w / 2}" y="{height - 6}" text-anchor="middle">'
        f'activation in {html.escape(top_roi)}</text>'
    )
    # OLS line, clipped to plot box
    x1, x2 = xmin, xmax
    y1, y2 = intercept + slope * x1, intercept + slope * x2
    parts.append(
        f'<line class="reg-line" x1="{sx(x1):.1f}" y1="{sy(y1):.1f}" '
        f'x2="{sx(x2):.1f}" y2="{sy(y2):.1f}"/>'
    )
    # Dots
    for c in per_card:
        cx, cy = sx(c["roi_top_value"]), sy(c["log_actual"])
        parts.append(
            f'<circle class="dot" cx="{cx:.1f}" cy="{cy:.1f}" r="4">'
            f'<title>{html.escape(c["name"] or c["id"])} — ${c["actual_price"]:.2f}</title>'
            f'</circle>'
        )
    parts.append("</svg>")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def main() -> None:
    if not PORTFOLIO_JSON.exists() or not ANALYSIS_JSON.exists():
        sys.exit("Run scrape -> brains -> analyze before build_site.")

    portfolio = json.loads(PORTFOLIO_JSON.read_text())
    by_id = {c["id"]: c for c in portfolio}
    analysis = json.loads(ANALYSIS_JSON.read_text())

    # Copy card images into site/assets/cards (so the deployed site is self-contained).
    CARDS_DST.mkdir(parents=True, exist_ok=True)
    image_url_for = {}
    for c in portfolio:
        local = c.get("local_image")
        if not local:
            continue
        src = BASE_DIR / local
        if not src.exists():
            continue
        dst = CARDS_DST / src.name
        if not dst.exists():
            shutil.copy2(src, dst)
        image_url_for[c["id"]] = f"assets/cards/{src.name}"

    per_card_raw = list(analysis["per_card"])

    # Rank-based implied value — avoids log-regression-mean-compression artifact.
    # market_rank: rank by actual_price DESC (1 = most expensive)
    # brain_rank:  rank by brain's predicted log(price) DESC (1 = brain's top pick)
    # implied_price: the actual-market price at the same rank position as brain's rank
    #                → "if you trust the brain's ordering, this is what the market pays
    #                   for a card the brain rates this highly"
    market_sorted = sorted(per_card_raw, key=lambda c: -c["actual_price"])
    for i, c in enumerate(market_sorted, start=1):
        c["market_rank"] = i
    brain_sorted = sorted(per_card_raw, key=lambda c: -c["log_predicted"])
    for i, c in enumerate(brain_sorted, start=1):
        c["brain_rank"] = i

    for c in per_card_raw:
        implied_rank_idx = c["brain_rank"] - 1
        implied_rank_idx = max(0, min(len(market_sorted) - 1, implied_rank_idx))
        c["implied_price"] = float(market_sorted[implied_rank_idx]["actual_price"])
        c["rank_diff"] = c["market_rank"] - c["brain_rank"]  # +: brain > market (undervalued)
        c["implied_pct"] = (c["implied_price"] / c["actual_price"] - 1.0) * 100.0

    # Undervalued: brain ranks card much higher than market does.
    undervalued = sorted(
        [c for c in per_card_raw if c["rank_diff"] >= 30 and c["actual_price"] >= 1.0],
        key=lambda c: -c["rank_diff"],
    )[:5]
    # Overvalued: market ranks card much higher than brain does.
    overvalued = sorted(
        [c for c in per_card_raw if c["rank_diff"] <= -30 and c["actual_price"] >= 1.0],
        key=lambda c: c["rank_diff"],
    )[:5]

    def enrich(c: dict) -> dict:
        return {
            **c,
            "image_url_rel": image_url_for.get(c["id"], ""),
            "image": bool(image_url_for.get(c["id"])),
            "has_heatmap": (HEATMAP_DIR / f"{c['id']}.png").exists(),
        }

    undervalued = [enrich(c) for c in undervalued]
    overvalued = [enrich(c) for c in overvalued]

    # Grid: sort by |rank_diff| desc — biggest brain-vs-market disagreements first.
    per_card = sorted(per_card_raw, key=lambda r: -abs(r.get("rank_diff", 0)))
    cards_for_grid = [enrich(c) for c in per_card]

    # Stats for the new section
    n_total = len(per_card_raw)
    n_undervalued = sum(1 for c in per_card_raw if c["rank_diff"] >= 30)
    n_overvalued = sum(1 for c in per_card_raw if c["rank_diff"] <= -30)

    top_roi = analysis["correlations"][0]["roi"]

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    tpl = env.get_template("index.html.j2")

    html_out = tpl.render(
        verdict=html.escape(analysis["verdict"]),
        n_cards=analysis["n_cards"],
        n_rois=analysis["n_rois"],
        loo_r2_real=analysis["regression"]["loo_r2_real"],
        real_percentile_in_null=analysis["regression"]["real_percentile_in_null"],
        n_shuffles=analysis["regression"]["n_shuffles"],
        bars_svg=make_bar_chart_svg(analysis["correlations"]),
        scatter_svg=make_scatter_svg(per_card, top_roi),
        top_roi=top_roi,
        cards_sorted=cards_for_grid,
        undervalued=undervalued,
        overvalued=overvalued,
        n_undervalued=n_undervalued,
        n_overvalued=n_overvalued,
        n_total=n_total,
        generated_at=dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
    )

    out_path = SITE_DIR / "index.html"
    out_path.write_text(html_out)
    size_kb = out_path.stat().st_size / 1024
    print(f"✓ {out_path}  ({size_kb:.1f} KB)")
    print(f"  cards in grid: {len(cards_for_grid)}")
    print(f"  top ROI: {top_roi}")
    print(f"  verdict: {analysis['verdict']}")


if __name__ == "__main__":
    main()
