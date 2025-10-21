#!/usr/bin/env python
"""
Generate binary masks from a VI or DEM.

This version adds two new features that are useful for the
“2. Mask the ODVI & OSAVI stacks (adaptive threshold)” step of the
pipeline:

1. Per‑image adaptive thresholding (Otsu or percentile) – used with
   ``--adaptive``.
2. An optional “dead‑tissue” band – any VI ≤ ``--dead-vi`` is treated as
   plant, and is OR’ed with the live mask.
"""

import os
import argparse
import numpy as np
import rasterio
import ckwrap  # ckmeans
try:
    import cv2  # optional morphology
    _HAS_CV2 = True
except Exception:
    _HAS_CV2 = False


# ----------------------------------------------------------------------
def _write_mask_like(src, mask_array, out_path, nodata_val=0):
    """Write a 1‑band uint8 mask that preserves the source profile."""
    profile = src.profile.copy()
    profile.update(
        count=1,
        dtype="uint8",
        nodata=nodata_val,
        compress="LZW",
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(mask_array.astype(np.uint8), 1)


# ----------------------------------------------------------------------
def generate_masks_dem(image_folder, mask_folder, k=3):
    """Generate masks from a DEM using ckmeans clustering."""
    os.makedirs(mask_folder, exist_ok=True)
    for fn in os.listdir(image_folder):
        if not fn.lower().endswith(".tif"):
            continue
        in_fp = os.path.join(image_folder, fn)
        out_fp = os.path.join(mask_folder, fn)
        try:
            with rasterio.open(in_fp) as src:
                dem = src.read(1, masked=True)  # honour nodata
                dem = np.ma.masked_where(
                    (dem == -9999) | dem.mask, dem
                )
                if dem.count() == 0:
                    mask = np.zeros(dem.shape, dtype=np.uint8)
                    _write_mask_like(src, mask, out_fp)
                    continue
                vmin = dem.min()
                vmax = dem.max()
                denom = max(1e-12, float(vmax - vmin))
                scaled = (dem - vmin) / denom * 255.0  # masked array
                vals = scaled.compressed().astype(np.float32)
                if vals.size == 0:
                    mask = np.zeros(dem.shape, dtype=np.uint8)
                else:
                    k_use = max(1, min(k, vals.size))
                    km = ckwrap.ckmeans(vals, k_use)
                    center_idx = 1 if k_use >= 2 else 0
                    thresh = km.centers[center_idx]
                    mask = np.zeros(dem.shape, dtype=np.uint8)
                    valid = ~scaled.mask
                    mask[valid & (scaled >= thresh)] = 255
                _write_mask_like(src, mask, out_fp)
        except Exception as e:
            print(f"[DEM] skip {in_fp}: {e}")
    print(f"[DEM] masks saved → {mask_folder}")


# ----------------------------------------------------------------------
def _adaptive_threshold(mask_arr, method="otsu", percentile=5):
    """
    Compute a per‑image threshold.
    """
    values = mask_arr.compressed()
    if values.size == 0:
        return np.inf
    if method == "otsu":
        norm = 255.0 * (values - values.min()) / (
            values.max() - values.min() + 1e-12
        )
        norm = norm.astype(np.uint8)
        _, thr = cv2.threshold(norm, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        thr = thr / 255.0 * (values.max() - values.min()) + values.min()
    elif method == "percentile":
        thr = np.percentile(values, percentile)
    else:
        raise ValueError("Unsupported adaptive method")
    return thr


# ----------------------------------------------------------------------
def generate_masks_vi(
    image_folder,
    mask_folder,
    lower_threshold=None,
    upper_threshold=None,
    morph_close=5,
    band_index=1,
    adaptive_method=None,
    adaptive_percentile=5,
    dead_threshold=None,
    nir_band_index=5,          # ← add this optional param
    nir_bg_factor=1.5,         # factor to push the NIR threshold away from zero
):
    os.makedirs(mask_folder, exist_ok=True)

    kernel = None
    if _HAS_CV2 and morph_close and morph_close > 1:
        kernel = np.ones((morph_close, morph_close), np.uint8)

    for fn in os.listdir(image_folder):
        if not fn.lower().endswith(".tif"):
            continue
        in_fp = os.path.join(image_folder, fn)
        out_fp = os.path.join(mask_folder, fn)
        try:
            with rasterio.open(in_fp) as src:
                band = src.read(band_index, masked=True)
                # --- 1) Build a background mask with NIR -----------------
                if nir_band_index is not None:
                    nir = src.read(nir_band_index, masked=True)
                    # change “alpha” (nir_bg_factor) to push threshold
                    # that separates black plastic from anything else.
                    # The background will be the lower 5 % of the NIR values.
                    flat = nir.compressed()
                    nir_thr = np.percentile(flat, nir_bg_factor)   # e.g. 1.5 → 5th‑percentile
                    bg_mask = ~nir.mask & (nir <= nir_thr)           # True in plastic
                else:
                    bg_mask = None

                # --- 2) Build the vegetation mask ----------------------
                if adaptive_method is not None:
                    thresh = _adaptive_threshold(
                        band,
                        method=adaptive_method,
                        percentile=adaptive_percentile,
                    )
                    veg = ~band.mask & (band < thresh)
                else:
                    if lower_threshold is None:
                        veg = ~band.mask & (band <= upper_threshold)
                    elif upper_threshold is None:
                        veg = ~band.mask & (band >= lower_threshold)
                    else:
                        veg = ~band.mask & (
                            band >= lower_threshold
                            & band <= upper_threshold
                        )

                # --- 3) Add the “dead‑tissue” band --------------------
                if dead_threshold is not None:
                    dead = ~band.mask & (band <= dead_threshold)
                    veg = veg | dead

                # --- 4) Remove background --------------------------------
                if bg_mask is not None:
                    veg = veg & (~bg_mask)      # <<< plucked out

                # --- 5) Binary mask & optional closing ------------------
                mask = np.zeros(band.shape, dtype=np.uint8)
                mask[veg] = 255

                if kernel is not None:
                    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

                _write_mask_like(src, mask, out_fp)
        except Exception as e:
            print(f"[VI] skip {in_fp}: {e}")
    print(f"[VI] masks saved → {mask_folder}")

# ----------------------------------------------------------------------
def generate_masks_for_batch(
    batch_folder,
    vi_subdir="OSAVI_by_plot",
    dem_subdir="dem_by_plot",
    vi_lt=None,
    vi_ut=None,
    morph_close=5,
    adaptive_method=None,
    adaptive_percentile=5,
    dead_threshold=None,
):
    """Run mask generation across a batch of dates."""
    for folder in os.listdir(batch_folder):
        root = os.path.join(batch_folder, folder)
        if not os.path.isdir(root):
            continue

        # DEM
        dem_image_folder = os.path.join(root, dem_subdir)
        if os.path.isdir(dem_image_folder):
            dem_mask_folder = os.path.join(
                root, "masks", os.path.basename(dem_image_folder).split("_")[0] + "_mask"
            )
            generate_masks_dem(dem_image_folder, dem_mask_folder)

        # VI
        vi_image_folder = os.path.join(root, vi_subdir)
        if os.path.isdir(vi_image_folder):
            vi_mask_folder = os.path.join(
                root,
                "masks",
                os.path.basename(vi_image_folder).split("_")[0] + "_mask",
            )
            generate_masks_vi(
                vi_image_folder,
                vi_mask_folder,
                lower_threshold=vi_lt,
                upper_threshold=vi_ut,
                morph_close=morph_close,
                adaptive_method=adaptive_method,
                adaptive_percentile=adaptive_percentile,
                dead_threshold=dead_threshold,
            )


# ----------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate GeoTIFF masks for VI (flexible) and DEM (ckmeans), preserving CRS."
    )
    parser.add_argument("ipath", nargs="?", help="Path to VI/DEM folder (single mode only).")
    parser.add_argument("mpath", nargs="?", help="Output mask folder (single mode only).")
    # Single‑folder options
    parser.add_argument(
        "--mode",
        choices=["vi", "dem"],
        default=None,
        help="Force mode for single‑folder run. If omitted, inferred from folder name.",
    )
    parser.add_argument("--lt", type=float, default=None, help="Lower threshold for VI mask.")
    parser.add_argument("--ut", type=float, default=None, help="Upper threshold for VI mask.")
    parser.add_argument(
        "--morph", type=int, default=5, help="Morph closing kernel (pixels). 0=off."
    )
    parser.add_argument("--band", type=int, default=1, help="Band index to read for VI (default 1).")
    parser.add_argument(
        "--adaptive",
        type=str,
        choices=["otsu", "percentile"],
        default=None,
        help="If set, compute a per‑image threshold (default none – use static thresholds).",
    )
    parser.add_argument(
        "--adaptive-percentile",
        type=int,
        default=5,
        help="When using --adaptive percentile, use this percentile to compute the threshold.",
    )
    parser.add_argument(
        "--dead-vi",
        type=float,
        default=None,
        help="Optional: include any VI <= this value as a dead‑tissue pixel in the mask.",
    )
    # Batch options
    parser.add_argument("--batchpath", type=str, help="Batch mode: path containing multiple date folders.")
    parser.add_argument(
        "--vi-subdir",
        type=str,
        default="OSAVI_by_plot",
        help="Name of VI subfolder to use in batch (e.g., NDVI_by_plot).",
    )
    parser.add_argument(
        "--dem-subdir",
        type=str,
        default="dem_by_plot",
        help="Name of DEM subfolder to use in batch.",
    )
    parser.add_argument(
        "--vi-lt",
        type=float,
        default=None,
        help="Batch: VI lower threshold.",
    )
    parser.add_argument(
        "--vi-ut",
        type=float,
        default=None,
        help="Batch: VI upper threshold.",
    )
    parser.add_argument(
        "--vi-morph",
        type=int,
        default=5,
        help="Batch: morphology kernel (pixels). 0=off.",
    )
    args = parser.parse_args()

    if args.batchpath:
        generate_masks_for_batch(
            batch_folder=args.batchpath,
            vi_subdir=args.vi_subdir,
            dem_subdir=args.dem_subdir,
            vi_lt=args.vi_lt,
            vi_ut=args.vi_ut,
            morph_close=args.vi_morph,
            adaptive_method=args.adaptive,
            adaptive_percentile=args.adaptive_percentile,
            dead_threshold=args.dead_vi,
        )
    else:
        # single‑folder mode
        mode = args.mode
        in_lower = os.path.basename(args.ipath).lower()
        if mode is None:
            mode = "dem" if "dem" in in_lower else "vi"
        if mode == "dem":
            generate_masks_dem(args.ipath, args.mpath)
        else:
            generate_masks_vi(
                args.ipath,
                args.mpath,
                lower_threshold=args.lt,
                upper_threshold=args.ut,
                morph_close=args.morph,
                band_index=args.band,
                adaptive_method=args.adaptive,
                adaptive_percentile=args.adaptive_percentile,
                dead_threshold=args.dead_vi,
            )
