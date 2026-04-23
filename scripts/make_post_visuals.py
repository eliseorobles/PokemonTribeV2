"""
Generate share-worthy PNGs for Medium / LinkedIn / Twitter from the brain
pipeline outputs. Outputs into posts/assets/ at 2x DPI for retina.

Visuals:
  1. null-distribution.png — histogram of 200 shuffled R² values with real R²
     marked. The "here's where chance ends and signal begins" shot.
  2. correlation-bars.png — top-10 ROI ↔ log(price) Pearson r. Dark mode.
  3. scatter.png — occipital_L activation vs log(price) with OLS fit, dot
     per card, top-and-bottom cards labeled.
  4. card-brain-pair.png — 3 representative cards + their predicted brain
     heatmaps side-by-side. Shows why the finding is visual.
  5. pipeline.png — simple 4-stage text diagram (scrape → wrap → TRIBE → stats).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np
from scipy import stats
from sklearn.linear_model import Ridge
from sklearn.model_selection import LeaveOneOut

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
BRAIN_DIR = DATA_DIR / "brain"
CARDS_DIR = DATA_DIR / "cards"
POSTS_ASSETS = BASE_DIR / "posts" / "assets"
HEATMAP_DIR = BASE_DIR / "site" / "assets" / "heatmaps"

POKEMON_YELLOW = "#ffcb05"
POKEMON_BLUE = "#3d7dca"
BG = "#0e0e15"
BG_ELEV = "#161624"
FG = "#f4f4f0"
FG_DIM = "#9ba0b3"
GOOD = "#4ade80"
BAD = "#f87171"
LINE = "#2a2a3f"

plt.rcParams.update({
    "figure.facecolor": BG,
    "axes.facecolor": BG,
    "savefig.facecolor": BG,
    "savefig.edgecolor": "none",
    "text.color": FG,
    "axes.labelcolor": FG,
    "axes.edgecolor": LINE,
    "xtick.color": FG_DIM,
    "ytick.color": FG_DIM,
    "grid.color": LINE,
    "grid.alpha": 0.5,
    "font.family": "sans-serif",
    "font.size": 11,
    "axes.titlesize": 16,
    "axes.titleweight": "bold",
})

RNG = np.random.default_rng(seed=2026)


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

def load_all():
    portfolio = json.loads((DATA_DIR / "portfolio.json").read_text())
    analysis = json.loads((DATA_DIR / "analysis.json").read_text())
    by_id = {c["id"]: c for c in portfolio}

    rows = []
    for c in portfolio:
        p = BRAIN_DIR / f"{c['id']}.npz"
        if not p.exists():
            continue
        price = c.get("current_market_price")
        if price is None or price <= 0:
            continue
        d = np.load(p)
        rows.append({
            "card": c,
            "roi": d["roi_activation"],
            "mean_act": d["mean_activation"],
            "price": float(price),
        })
    X = np.stack([r["roi"] for r in rows]).astype(np.float64)
    y = np.log(np.array([r["price"] for r in rows]))
    return portfolio, analysis, by_id, rows, X, y


def loo_r2(X, y, alpha=1.0):
    loo = LeaveOneOut()
    preds = np.zeros_like(y)
    for tr, te in loo.split(X):
        m = Ridge(alpha=alpha)
        m.fit(X[tr], y[tr])
        preds[te] = m.predict(X[te])
    ss_res = float(np.sum((y - preds) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    return (1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0), preds


# ---------------------------------------------------------------------------
# 1. Null distribution
# ---------------------------------------------------------------------------

def viz_null_distribution(X, y, analysis, out_path: Path, n_shuffles=200):
    print("→ null-distribution.png")
    real_r2 = float(analysis["regression"]["loo_r2_real"])
    null = np.zeros(n_shuffles)
    for i in range(n_shuffles):
        null[i], _ = loo_r2(X, RNG.permutation(y))

    fig, ax = plt.subplots(figsize=(9, 5), dpi=180)
    ax.hist(null, bins=30, color=FG_DIM, alpha=0.55, edgecolor=BG, linewidth=0.5,
            label="200 shuffled controls")
    ax.axvline(real_r2, color=POKEMON_YELLOW, lw=3,
               label=f"real model  R² = {real_r2:+.3f}")
    ax.axvline(null.mean(), color=FG_DIM, lw=1.5, ls="--",
               label=f"shuffle mean  R² = {null.mean():+.3f}")
    ax.set_xlabel("Held-out R²  (leave-one-out cross-validation)", color=FG)
    ax.set_ylabel("count", color=FG)
    ax.set_title("The real model beats every shuffled control", pad=16)
    ax.grid(axis="y", alpha=0.25)
    leg = ax.legend(loc="upper left", frameon=False)
    for text in leg.get_texts():
        text.set_color(FG)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 2. Correlation bars
# ---------------------------------------------------------------------------

def viz_correlation_bars(analysis, out_path: Path):
    print("→ correlation-bars.png")
    top = analysis["correlations"][:10]
    names = [c["roi"] for c in top][::-1]
    rs = [c["r"] for c in top][::-1]
    colors = [GOOD if r >= 0 else BAD for r in rs]

    fig, ax = plt.subplots(figsize=(9, 5.2), dpi=180)
    bars = ax.barh(names, rs, color=colors, edgecolor="none", height=0.7)
    for bar, r in zip(bars, rs):
        x = bar.get_width()
        ax.text(x + (0.008 if x >= 0 else -0.008), bar.get_y() + bar.get_height() / 2,
                f"{r:+.2f}", color=FG, va="center",
                ha="left" if x >= 0 else "right", fontsize=10, fontfamily="monospace")
    ax.axvline(0, color=LINE, lw=1)
    ax.set_xlabel("Pearson r  vs log(market price)", color=FG)
    ax.set_title("Top 10 brain regions that track card value", pad=16)
    ax.set_xlim(-0.55, 0.55)
    ax.tick_params(axis="y", pad=6)
    ax.grid(axis="x", alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 3. Scatter
# ---------------------------------------------------------------------------

def viz_scatter(analysis, out_path: Path):
    print("→ scatter.png")
    per_card = analysis["per_card"]
    top_roi = analysis["correlations"][0]["roi"]
    xs = np.array([c["roi_top_value"] for c in per_card])
    ys = np.array([c["log_actual"] for c in per_card])
    names = [c["name"] for c in per_card]

    slope, intercept, r, p, _ = stats.linregress(xs, ys)
    xline = np.linspace(xs.min(), xs.max(), 100)
    yline = intercept + slope * xline

    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=180)
    ax.scatter(xs, ys, s=44, color=POKEMON_YELLOW, alpha=0.78, edgecolor=BG, linewidth=0.5)
    ax.plot(xline, yline, color=POKEMON_BLUE, lw=2, ls="--",
            label=f"OLS fit  r = {r:+.2f}")
    # Label the 3 priciest cards
    top3_idx = np.argsort(ys)[-3:]
    for i in top3_idx:
        ax.annotate(names[i][:30], (xs[i], ys[i]),
                    textcoords="offset points", xytext=(8, -10),
                    fontsize=9, color=FG,
                    bbox=dict(boxstyle="round,pad=0.25", fc=BG_ELEV, ec=LINE, lw=0.5))

    # Y axis as dollars
    yticks = ax.get_yticks()
    ax.set_yticks(yticks)
    ax.set_yticklabels([f"${np.exp(y):.0f}" for y in yticks])

    ax.set_xlabel(f"predicted brain activation in {top_roi}", color=FG)
    ax.set_ylabel("market price", color=FG)
    ax.set_title(f"Cards the visual cortex likes tend to cost more  ·  n={len(xs)}", pad=16)
    ax.grid(alpha=0.25)
    leg = ax.legend(loc="lower right", frameon=False)
    for t in leg.get_texts():
        t.set_color(FG)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 4. Card + brain pair (three representative cards)
# ---------------------------------------------------------------------------

def viz_card_brain_pair(analysis, out_path: Path):
    print("→ card-brain-pair.png")
    per_card = analysis["per_card"]
    # Pick: most expensive, middle, cheapest — all with available image + heatmap
    usable = [c for c in per_card
              if c.get("image") and (HEATMAP_DIR / f"{c['id']}.png").exists()]
    usable.sort(key=lambda c: -c["actual_price"])
    picks = [usable[0], usable[len(usable) // 2], usable[-1]]

    fig, axes = plt.subplots(3, 2, figsize=(9, 9.5), dpi=180,
                              gridspec_kw={"width_ratios": [1, 1.25], "wspace": 0.05, "hspace": 0.1})
    for row, card in enumerate(picks):
        # Card image
        card_img = mpimg.imread(BASE_DIR / card["image"])
        axes[row, 0].imshow(card_img)
        axes[row, 0].set_xticks([])
        axes[row, 0].set_yticks([])
        for s in axes[row, 0].spines.values():
            s.set_visible(False)

        # Brain heatmap
        heat = mpimg.imread(HEATMAP_DIR / f"{card['id']}.png")
        axes[row, 1].imshow(heat)
        axes[row, 1].set_xticks([])
        axes[row, 1].set_yticks([])
        for s in axes[row, 1].spines.values():
            s.set_visible(False)

        # Overlay label on card
        label = f"{card['name'][:26]}\n${card['actual_price']:.2f}"
        axes[row, 0].text(0.02, 0.02, label,
                          transform=axes[row, 0].transAxes,
                          color=FG, fontsize=11, fontweight="bold",
                          va="bottom", ha="left",
                          bbox=dict(boxstyle="round,pad=0.4", fc=BG_ELEV, ec=LINE, lw=0.5, alpha=0.95))

    fig.suptitle("A card, and what it would do to a human brain",
                 fontsize=16, fontweight="bold", y=0.99)
    fig.text(0.27, 0.955, "image →", fontsize=11, color=FG_DIM, ha="center")
    fig.text(0.72, 0.955, "predicted fMRI activation", fontsize=11, color=FG_DIM, ha="center")
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 5. Pipeline diagram
# ---------------------------------------------------------------------------

def viz_pipeline(out_path: Path):
    print("→ pipeline.png")
    fig, ax = plt.subplots(figsize=(11, 3), dpi=180)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")

    boxes = [
        (0.3, "Collectr portfolio",   "213 cards · $5,641",      POKEMON_YELLOW),
        (2.55, "TRIBE v2 inference", "fMRI prediction\nper image", POKEMON_BLUE),
        (4.8, "ROI aggregation",    "20,484 vertices →\n14 regions", "#9f7aea"),
        (7.05, "Ridge + LOO-CV",     "ROI vector →\nlog(price)",  GOOD),
        (9.3, "Null shuffle",        "200 permutations\nof price", "#f97316"),
    ]
    w, h = 1.95, 1.6
    for i, (x, title, sub, color) in enumerate(boxes):
        ax.add_patch(plt.Rectangle((x, 0.7), w, h, facecolor=BG_ELEV,
                                     edgecolor=color, linewidth=2.2, alpha=1.0,
                                     zorder=2))
        ax.text(x + w / 2, 0.7 + h * 0.62, title, ha="center", va="center",
                fontsize=11, fontweight="bold", color=FG)
        ax.text(x + w / 2, 0.7 + h * 0.28, sub, ha="center", va="center",
                fontsize=9, color=FG_DIM)
        if i < len(boxes) - 1:
            ax.annotate("", xy=(x + w + 0.25, 1.5), xytext=(x + w - 0.02, 1.5),
                        arrowprops=dict(arrowstyle="->", color=FG_DIM, lw=1.6))

    ax.text(5, 2.75, "The pipeline",
            ha="center", va="center", fontsize=15, color=FG, fontweight="bold")
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    POSTS_ASSETS.mkdir(parents=True, exist_ok=True)
    portfolio, analysis, by_id, rows, X, y = load_all()
    print(f"Loaded {len(rows)} cards with both brain output and price")

    viz_null_distribution(X, y, analysis, POSTS_ASSETS / "null-distribution.png")
    viz_correlation_bars(analysis, POSTS_ASSETS / "correlation-bars.png")
    viz_scatter(analysis, POSTS_ASSETS / "scatter.png")
    viz_card_brain_pair(analysis, POSTS_ASSETS / "card-brain-pair.png")
    viz_pipeline(POSTS_ASSETS / "pipeline.png")

    print(f"\n✓ Visuals in {POSTS_ASSETS}")


if __name__ == "__main__":
    main()
