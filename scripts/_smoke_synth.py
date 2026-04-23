"""
Synthesize fake portfolio + brain outputs for end-to-end testing of
analyze -> heatmaps -> build_site (without burning real TRIBE v2 inference).

NOT part of the user-facing pipeline. Run once to validate plumbing, then
delete data/cards/synth_*, data/brain/synth_*, data/portfolio.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CARDS_DIR = DATA_DIR / "cards"
BRAIN_DIR = DATA_DIR / "brain"
VIDEOS_DIR = BASE_DIR / "videos"

sys.path.insert(0, str(BASE_DIR / "tribev2"))
sys.path.insert(0, str(BASE_DIR / "scripts"))

from run_brain_inference import build_roi_labels, aggregate_by_roi
from nilearn import datasets, surface

N = 12
SEED = 42

CARD_NAMES = [
    ("Charizard ex 199/197", "OBF",   "199/197", 380.00),
    ("Pikachu ex 238/091",   "PAL",   "238/091", 145.00),
    ("Mewtwo VSTAR 086/078", "PGO",   "086/078", 92.50),
    ("Gengar V 109/198",     "CRZ",   "109/198", 23.00),
    ("Greninja Star 187/175","SHF",   "187/175", 41.00),
    ("Eevee 188/091",        "PAF",   "188/091", 18.00),
    ("Snorlax 144/131",      "FST",   "144/131", 8.50),
    ("Bulbasaur 001/165",    "MEW",   "001/165", 4.25),
    ("Vaporeon 197/091",     "PAF",   "197/091", 33.00),
    ("Lugia V 138/195",      "SIT",   "138/195", 12.00),
    ("Mew 232/091",          "PAF",   "232/091", 28.00),
    ("Rayquaza VMAX 218/203","EVS",   "218/203", 64.00),
]


def synth() -> None:
    BRAIN_DIR.mkdir(parents=True, exist_ok=True)
    CARDS_DIR.mkdir(parents=True, exist_ok=True)

    print("→ Building fsaverage5 ROI partition …")
    fs5 = datasets.fetch_surf_fsaverage(mesh="fsaverage5")
    coords_L, _ = surface.load_surf_mesh(fs5["pial_left"])
    coords_R, _ = surface.load_surf_mesh(fs5["pial_right"])
    coords = np.vstack([coords_L, coords_R])
    roi_labels, roi_names = build_roi_labels(coords)
    n_rois = len(roi_names)
    (DATA_DIR / "roi_names.json").write_text(json.dumps(roi_names, indent=2))
    np.save(DATA_DIR / "roi_labels.npy", roi_labels)

    rng = np.random.default_rng(SEED)
    n_vertices = coords.shape[0]
    portfolio = []
    print("→ Generating fake card brain outputs …")
    for i, (name, set_code, num, price) in enumerate(CARD_NAMES[:N]):
        cid = f"synth_{i:03d}"
        # Build a fake activation map. Visual cortex (occipital) gets a real
        # signal proportional to log(price) — so the test should find a real
        # correlation in occipital_L/R.
        base = rng.normal(0, 0.05, size=n_vertices).astype(np.float32)
        log_p = np.log(price)
        # Boost occipital (lobe 0) by a price-dependent amount + small noise
        occip_mask = (roi_labels == 0) | (roi_labels == 1)
        base[occip_mask] += 0.015 * log_p + rng.normal(0, 0.02, size=occip_mask.sum())
        # Add small anti-correlation in cingulate just to have a negative bar
        cing_mask = (roi_labels == 12) | (roi_labels == 13)
        base[cing_mask] -= 0.01 * log_p + rng.normal(0, 0.015, size=cing_mask.sum())

        roi_act = aggregate_by_roi(base, roi_labels, n_rois)
        np.savez_compressed(
            BRAIN_DIR / f"{cid}.npz",
            mean_activation=base,
            roi_activation=roi_act,
            n_timesteps=2,
            n_vertices=n_vertices,
        )

        # Use a frame from the existing demo videos as the placeholder card image.
        # Just point at a placeholder PNG; we'll create one if missing.
        img_path = CARDS_DIR / f"{cid}.png"
        if not img_path.exists():
            from PIL import Image, ImageDraw, ImageFont
            img = Image.new("RGB", (245, 340), color=(20 + i * 7 % 200, 30 + i * 13 % 200, 80 + i * 17 % 175))
            d = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("/System/Library/Fonts/SFNS.ttf", 14)
            except OSError:
                font = ImageFont.load_default()
            d.multiline_text((10, 10), name, fill="white", font=font)
            d.multiline_text((10, 300), f"${price:.2f}", fill="white", font=font)
            img.save(img_path, format="PNG")

        portfolio.append({
            "id": cid,
            "name": name,
            "set_code": set_code,
            "card_number": num,
            "condition": "NM",
            "quantity": 1,
            "purchase_price": None,
            "current_market_price": price,
            "image_url": None,
            "local_image": str(img_path.relative_to(BASE_DIR)),
        })

    (DATA_DIR / "portfolio.json").write_text(json.dumps(portfolio, indent=2))
    print(f"✓ Synthesized {len(portfolio)} fake cards in data/portfolio.json + data/brain/")


if __name__ == "__main__":
    synth()
