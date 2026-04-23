"""
Render per-card brain heatmap PNGs + a summary ROI-correlation overlay.

Per-card: small dual-hemisphere lateral PNG, no colorbar -> grid thumbnails.
Summary:  larger 4-view PNG colored by per-ROI |r| with price (the "what your
          brain cares about" map).
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
import numpy as np
from tqdm import tqdm

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
BRAIN_DIR = DATA_DIR / "brain"
SITE_DIR = BASE_DIR / "site"
HEATMAP_DIR = SITE_DIR / "assets" / "heatmaps"
PORTFOLIO_JSON = DATA_DIR / "portfolio.json"
ANALYSIS_JSON = DATA_DIR / "analysis.json"
ROI_LABELS_NPY = DATA_DIR / "roi_labels.npy"
ROI_NAMES_JSON = DATA_DIR / "roi_names.json"

sys.path.insert(0, str(BASE_DIR / "tribev2"))


def make_plotter():
    from tribev2.plotting import PlotBrainNilearn
    return PlotBrainNilearn(mesh="fsaverage5")


def render_card_heatmap(plotter, mean_act: np.ndarray, out_path: Path) -> None:
    if out_path.exists():
        return
    fig, axes = plt.subplots(
        1, 2,
        figsize=(3.6, 1.9),
        subplot_kw={"projection": "3d"},
        gridspec_kw={"wspace": 0.0},
    )
    for ax, view in zip(axes, ("left", "right")):
        plotter.plot_surf(
            mean_act,
            axes=ax,
            views=view,
            cmap="hot",
            norm_percentile=99,
            vmin=0.6,
            alpha_cmap=(0, 0.2),
        )
        ax.set_axis_off()
    fig.patch.set_alpha(0)
    fig.savefig(out_path, dpi=110, bbox_inches="tight",
                pad_inches=0.02, transparent=True)
    plt.close(fig)


def render_roi_overlay(
    plotter,
    roi_labels: np.ndarray,
    roi_names: list[str],
    correlations: list[dict],
    out_path: Path,
) -> None:
    """Color every vertex by the |r| of its containing ROI's correlation with price."""
    by_name = {c["roi"]: c["r"] for c in correlations}
    r_per_roi = np.array([by_name.get(name, 0.0) for name in roi_names])
    vertex_values = np.abs(r_per_roi[roi_labels]).astype(np.float32)

    views = ("left", "right", "medial_left", "medial_right")
    fig, axes = plt.subplots(
        1, len(views),
        figsize=(3.0 * len(views), 3.2),
        subplot_kw={"projection": "3d"},
        gridspec_kw={"wspace": 0.02},
    )
    vmax = max(0.05, float(vertex_values.max()))
    for ax, view in zip(axes, views):
        plotter.plot_surf(
            vertex_values,
            axes=ax,
            views=view,
            cmap="hot",
            norm_percentile=100,
            vmin=0.0,
            alpha_cmap=(0, 0.2),
        )
        ax.set_axis_off()
        ax.set_title(view.replace("_", " ").title(), fontsize=10, pad=-4)
    fig.suptitle(
        f"|Pearson r|  with  log(price)   (max |r| = {vmax:.2f})",
        fontsize=11, y=0.95,
    )
    fig.savefig(out_path, dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    HEATMAP_DIR.mkdir(parents=True, exist_ok=True)
    if not PORTFOLIO_JSON.exists() or not ANALYSIS_JSON.exists():
        sys.exit("Missing portfolio.json or analysis.json — run earlier stages first.")
    cards = json.loads(PORTFOLIO_JSON.read_text())
    analysis = json.loads(ANALYSIS_JSON.read_text())
    roi_labels = np.load(ROI_LABELS_NPY)
    roi_names = json.loads(ROI_NAMES_JSON.read_text())

    print("→ Loading brain plotter (fsaverage5) …")
    plotter = make_plotter()

    rendered = 0
    for card in tqdm(cards, desc="card heatmaps"):
        npz_path = BRAIN_DIR / f"{card['id']}.npz"
        if not npz_path.exists():
            continue
        mean_act = np.load(npz_path)["mean_activation"].astype(np.float32)
        render_card_heatmap(plotter, mean_act, HEATMAP_DIR / f"{card['id']}.png")
        rendered += 1

    print(f"→ Rendering ROI-correlation overlay …")
    render_roi_overlay(
        plotter,
        roi_labels,
        roi_names,
        analysis["correlations"],
        SITE_DIR / "assets" / "roi_correlation.png",
    )

    print(f"\n✓ {rendered} per-card heatmaps + 1 summary overlay  -> {HEATMAP_DIR}")


if __name__ == "__main__":
    main()
