"""
Run each scraped card image through TRIBE v2 and store its predicted brain
activation.

Pipeline per card:
    card.jpg -> 2-second silent MP4 -> TribeModel.predict -> (n_TRs, 20484)
              -> mean over time -> save (20484,) + ROI aggregation.

ROIs: a hand-rolled coordinate partition of the fsaverage5 mesh into ~14
anatomical regions (occipital / parietal / temporal / sensorimotor / frontal /
prefrontal / cingulate × L/R). Produces an interpretable ~14-dim feature vector
per card without requiring a surface atlas.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Feature extractors don't support MPS; force CPU to match run_comparison.py.
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

import numpy as np
from tqdm import tqdm

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CARDS_DIR = DATA_DIR / "cards"
BRAIN_DIR = DATA_DIR / "brain"
IMAGE_VIDEO_DIR = DATA_DIR / "image_videos"
CACHE_DIR = BASE_DIR / "cache"
PORTFOLIO_JSON = DATA_DIR / "portfolio.json"

sys.path.insert(0, str(BASE_DIR / "tribev2"))


# ---------------------------------------------------------------------------
# ROI partition of fsaverage5
# ---------------------------------------------------------------------------

def build_roi_labels(coords: np.ndarray) -> tuple[np.ndarray, list[str]]:
    """Assign every vertex an ROI index based on its (x, y, z) coord.

    coords: (n_vertices, 3) in MNI-ish space (FreeSurfer fsaverage5 default).
    Returns (labels[n_vertices], roi_names[n_regions]).
    """
    x = coords[:, 0]
    y = coords[:, 1]
    z = coords[:, 2]

    lobes = np.full(coords.shape[0], -1, dtype=np.int64)
    #     name              condition
    rules = [
        ("occipital",       y < -60),
        ("parietal",        (y >= -60) & (y < -10) & (z >= 25)),
        ("temporal",        (y >= -60) & (y < 10) & (z < 5)),
        ("sensorimotor",    (y >= -25) & (y < 20) & (z >= 25)),
        ("frontal",         (y >= 10) & (y < 45)),
        ("prefrontal",      y >= 45),
        ("cingulate",       (np.abs(x) < 12) & (z >= 0)),  # medial strip
    ]
    # Last rule wins if multiple match — so cingulate overrides the lobe split
    # for vertices near the midline, as intended.
    for idx, (_, mask) in enumerate(rules):
        lobes[mask] = idx
    # Any unassigned vertices -> nearest lobe by distance to (0, y midpoint).
    # Put them in "temporal" as a catch-all; this is rare.
    lobes[lobes < 0] = 2

    hemi = (x >= 0).astype(np.int64)  # 0 = L, 1 = R
    roi = lobes * 2 + hemi            # 0..13 for 7 lobes × 2 hemis

    names: list[str] = []
    for lobe_name, _ in rules:
        for side in ("L", "R"):
            names.append(f"{lobe_name}_{side}")
    return roi, names


def aggregate_by_roi(mean_act: np.ndarray, roi_labels: np.ndarray, n_rois: int) -> np.ndarray:
    """Mean activation inside each ROI."""
    out = np.zeros(n_rois, dtype=np.float32)
    for r in range(n_rois):
        m = roi_labels == r
        if m.any():
            out[r] = float(mean_act[m].mean())
    return out


# ---------------------------------------------------------------------------
# Image -> silent MP4 wrapper
# ---------------------------------------------------------------------------

def image_to_video(image_path: Path, dest_mp4: Path, duration: float = 2.0) -> Path:
    """Write a silent MP4 that holds `image_path` as a static frame for `duration` sec.

    Card images from Collectr have varying (often odd) dimensions. libx264 with
    yuv420p needs EVEN width and height, so we preprocess with PIL: convert to
    RGB, clamp to max 512 on the long side, crop to even dims.
    """
    if dest_mp4.exists():
        return dest_mp4
    from PIL import Image
    from moviepy import ImageClip

    # Normalize the source image into a temp file
    norm_path = dest_mp4.with_suffix(".norm.jpg")
    with Image.open(image_path) as im:
        im = im.convert("RGB")  # drop alpha
        w, h = im.size
        max_dim = 512
        if max(w, h) > max_dim:
            if w >= h:
                im = im.resize((max_dim, int(h * max_dim / w)), Image.LANCZOS)
            else:
                im = im.resize((int(w * max_dim / h), max_dim), Image.LANCZOS)
            w, h = im.size
        # Even dimensions for libx264
        w_e, h_e = w - (w % 2), h - (h % 2)
        if (w_e, h_e) != (w, h):
            im = im.crop((0, 0, w_e, h_e))
        im.save(norm_path, format="JPEG", quality=92)

    try:
        clip = ImageClip(str(norm_path), duration=duration)
        clip.write_videofile(
            str(dest_mp4),
            codec="libx264",
            fps=8,
            audio=False,
            logger=None,
            preset="ultrafast",
            ffmpeg_params=["-pix_fmt", "yuv420p"],
        )
        clip.close()
    finally:
        norm_path.unlink(missing_ok=True)
    return dest_mp4


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None,
                        help="Only process the first N cards (smoke test).")
    parser.add_argument("--skip-existing", action="store_true", default=True)
    parser.add_argument("--rerun", dest="skip_existing", action="store_false")
    parser.add_argument("--shard", default=None,
                        help="Partition work as I/N (e.g. --shard 0/2 for "
                             "worker 0 of 2). Processes cards where idx %% N == I.")
    args = parser.parse_args()

    BRAIN_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_VIDEO_DIR.mkdir(parents=True, exist_ok=True)

    if not PORTFOLIO_JSON.exists():
        sys.exit(f"Missing {PORTFOLIO_JSON}. Run `make scrape` first.")
    cards = json.loads(PORTFOLIO_JSON.read_text())
    cards = [c for c in cards if c.get("local_image")]
    if args.limit:
        cards = cards[: args.limit]
    shard_tag = ""
    if args.shard:
        try:
            shard_i, shard_n = (int(x) for x in args.shard.split("/"))
        except ValueError:
            sys.exit(f"--shard must look like I/N (got {args.shard!r})")
        if not (0 <= shard_i < shard_n):
            sys.exit(f"--shard index out of range (0 ≤ I < N): {args.shard}")
        cards = [c for i, c in enumerate(cards) if i % shard_n == shard_i]
        shard_tag = f"[shard {shard_i}/{shard_n}] "
    print(f"→ {shard_tag}{len(cards)} cards to process")

    # --- Load model (once) ---
    print("→ Loading TRIBE v2 (CPU) …")
    from tribev2.demo_utils import TribeModel

    model = TribeModel.from_pretrained(
        "facebook/tribev2",
        cache_folder=str(CACHE_DIR),
        device="cpu",
        config_update={
            "data.text_feature.device": "cpu",
            "data.audio_feature.device": "cpu",
            "data.video_feature.image.device": "cpu",
            "data.image_feature.image.device": "cpu",
            "data.num_workers": 0,
        },
    )

    # --- Prepare ROI labels on fsaverage5 ---
    print("→ Building ROI partition on fsaverage5 …")
    from nilearn import datasets, surface
    fs5 = datasets.fetch_surf_fsaverage(mesh="fsaverage5")
    coords_L, _ = surface.load_surf_mesh(fs5["pial_left"])
    coords_R, _ = surface.load_surf_mesh(fs5["pial_right"])
    coords = np.vstack([coords_L, coords_R])
    roi_labels, roi_names = build_roi_labels(coords)
    n_rois = len(roi_names)
    (DATA_DIR / "roi_names.json").write_text(json.dumps(roi_names, indent=2))
    np.save(DATA_DIR / "roi_labels.npy", roi_labels)
    print(f"   {n_rois} regions  (counts: "
          f"{dict(zip(*np.unique(roi_labels, return_counts=True)))})")

    # --- Run inference ---
    ok, skipped, failed = 0, 0, 0
    for card in tqdm(cards, desc="brain inference"):
        out_path = BRAIN_DIR / f"{card['id']}.npz"
        if args.skip_existing and out_path.exists():
            skipped += 1
            continue

        image_path = BASE_DIR / card["local_image"]
        if not image_path.exists():
            failed += 1
            continue

        video_path = IMAGE_VIDEO_DIR / f"{card['id']}.mp4"
        try:
            image_to_video(image_path, video_path)
        except Exception as e:  # noqa: BLE001
            tqdm.write(f"  ✗ video wrap failed for {card['id']}: {e}")
            failed += 1
            continue

        try:
            events = model.get_events_dataframe(video_path=str(video_path))
            preds, _segments = model.predict(events=events, verbose=False)
        except Exception as e:  # noqa: BLE001
            tqdm.write(f"  ✗ inference failed for {card['id']}: {e}")
            failed += 1
            continue

        if preds.size == 0 or preds.shape[0] == 0:
            tqdm.write(f"  ⚠ empty predictions for {card['id']}")
            failed += 1
            continue

        mean_act = preds.mean(axis=0).astype(np.float32)       # (n_vertices,)
        roi_act = aggregate_by_roi(mean_act, roi_labels, n_rois)

        np.savez_compressed(
            out_path,
            mean_activation=mean_act,
            roi_activation=roi_act,
            n_timesteps=preds.shape[0],
            n_vertices=preds.shape[1],
        )
        ok += 1

    print(f"\n✓ Done  ok={ok}  skipped={skipped}  failed={failed}")


if __name__ == "__main__":
    main()
