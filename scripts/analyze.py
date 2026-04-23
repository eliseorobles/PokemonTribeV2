"""
Correlate per-card ROI brain activations with log(price). Output data/analysis.json.

What we compute
---------------
1. Pearson r between each ROI's activation and log(market_price), with two-sided p.
2. Ridge regression on all ROIs -> log(price), held-out R^2 via leave-one-out CV.
3. Shuffle control: re-run (2) with the price column randomly permuted N times.
   Real R^2's percentile against the null distribution is the headline finding.
4. Per-card: held-out predicted log(price) -> predicted price + delta vs actual.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats
from sklearn.linear_model import Ridge
from sklearn.model_selection import LeaveOneOut

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
BRAIN_DIR = DATA_DIR / "brain"
PORTFOLIO_JSON = DATA_DIR / "portfolio.json"
ROI_NAMES_JSON = DATA_DIR / "roi_names.json"
OUT_JSON = DATA_DIR / "analysis.json"

N_SHUFFLES = 200
RIDGE_ALPHA = 1.0
RNG = np.random.default_rng(seed=2026)


def coerce_price(v) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v) if v > 0 else None
    s = str(v).strip().lstrip("$").replace(",", "")
    if not s:
        return None
    try:
        f = float(s)
    except ValueError:
        return None
    return f if f > 0 else None


def loo_r2(X: np.ndarray, y: np.ndarray, alpha: float = RIDGE_ALPHA) -> tuple[float, np.ndarray]:
    """Return (held-out R^2, per-sample held-out predictions)."""
    loo = LeaveOneOut()
    preds = np.zeros_like(y)
    for train_idx, test_idx in loo.split(X):
        m = Ridge(alpha=alpha)
        m.fit(X[train_idx], y[train_idx])
        preds[test_idx] = m.predict(X[test_idx])
    ss_res = float(np.sum((y - preds) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return r2, preds


def main() -> None:
    if not PORTFOLIO_JSON.exists():
        sys.exit(f"Missing {PORTFOLIO_JSON}.")
    if not ROI_NAMES_JSON.exists():
        sys.exit(f"Missing {ROI_NAMES_JSON}. Run brain inference first.")

    cards = json.loads(PORTFOLIO_JSON.read_text())
    roi_names: list[str] = json.loads(ROI_NAMES_JSON.read_text())

    rows = []
    for c in cards:
        npz_path = BRAIN_DIR / f"{c['id']}.npz"
        price = coerce_price(c.get("current_market_price"))
        if not npz_path.exists() or price is None:
            continue
        data = np.load(npz_path)
        roi_act = data["roi_activation"]
        if roi_act.shape[0] != len(roi_names):
            print(
                f"  ⚠ {c['id']}: roi vector length {roi_act.shape[0]} != "
                f"{len(roi_names)} (skipping)"
            )
            continue
        rows.append({"card": c, "roi": roi_act, "price": price})

    if len(rows) < 5:
        sys.exit(f"Need ≥5 cards with both brain output and price; got {len(rows)}.")

    n = len(rows)
    X = np.stack([r["roi"] for r in rows]).astype(np.float64)
    y = np.log(np.array([r["price"] for r in rows], dtype=np.float64))
    print(f"→ {n} cards × {X.shape[1]} ROIs")

    # --- Per-ROI correlations ---
    correlations = []
    for i, name in enumerate(roi_names):
        col = X[:, i]
        if col.std() < 1e-9 or y.std() < 1e-9:
            r, p = 0.0, 1.0
        else:
            r, p = stats.pearsonr(col, y)
        correlations.append({"roi": name, "r": float(r), "p": float(p)})
    correlations.sort(key=lambda d: abs(d["r"]), reverse=True)
    for rank, c in enumerate(correlations, 1):
        c["rank"] = rank

    # --- Real held-out R^2 ---
    real_r2, real_preds_log = loo_r2(X, y)
    print(f"→ Real LOO R^2 = {real_r2:+.3f}")

    # --- Shuffle control ---
    null_r2 = np.zeros(N_SHUFFLES)
    for k in range(N_SHUFFLES):
        y_shuf = RNG.permutation(y)
        null_r2[k], _ = loo_r2(X, y_shuf)
    null_mean = float(null_r2.mean())
    null_p95 = float(np.percentile(null_r2, 95))
    pct = float((null_r2 < real_r2).mean() * 100)
    print(f"→ Null LOO R^2: mean={null_mean:+.3f}, p95={null_p95:+.3f}; "
          f"real is at the {pct:.1f}th percentile")

    # --- Per-card predictions ---
    real_preds_price = np.exp(real_preds_log)
    actual_price = np.exp(y)
    per_card = []
    for r, ph, pa in zip(rows, real_preds_price, actual_price):
        per_card.append({
            "id": r["card"]["id"],
            "name": r["card"].get("name"),
            "set_code": r["card"].get("set_code"),
            "image": r["card"].get("local_image"),
            "actual_price": float(pa),
            "predicted_price": float(ph),
            "delta": float(ph - pa),
            "log_actual": float(np.log(pa)),
            "log_predicted": float(np.log(ph)),
            "roi_top": correlations[0]["roi"],
            "roi_top_value": float(r["roi"][roi_names.index(correlations[0]["roi"])]),
        })

    # --- Headline summary ---
    top = correlations[0]
    if pct >= 95 and real_r2 > 0:
        verdict = (
            f"Real signal: brain-predicted price beats {pct:.0f}% of shuffled controls "
            f"(R²={real_r2:.2f}). Strongest single region: {top['roi']} "
            f"(r={top['r']:+.2f}, p={top['p']:.3f})."
        )
    else:
        verdict = (
            f"No reliable signal: held-out R²={real_r2:.2f} sits at the "
            f"{pct:.0f}th percentile of shuffled controls (mean {null_mean:.2f}). "
            f"For your collection, image-derived brain activation does not predict price."
        )

    OUT_JSON.write_text(json.dumps({
        "n_cards": n,
        "n_rois": len(roi_names),
        "roi_names": roi_names,
        "correlations": correlations,
        "regression": {
            "loo_r2_real": real_r2,
            "loo_r2_shuffled_mean": null_mean,
            "loo_r2_shuffled_p95": null_p95,
            "real_percentile_in_null": pct,
            "n_shuffles": N_SHUFFLES,
            "ridge_alpha": RIDGE_ALPHA,
        },
        "per_card": per_card,
        "verdict": verdict,
    }, indent=2))
    print(f"\n✓ {OUT_JSON}")
    print(f"   verdict: {verdict}")


if __name__ == "__main__":
    main()
