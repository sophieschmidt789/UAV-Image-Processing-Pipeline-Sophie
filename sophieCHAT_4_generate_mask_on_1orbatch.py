#!/usr/bin/env python
"""
sophieCHAT_4_generate_mask_on_1orbatch.py

Core mask‑generation script for the UVA‑image‑processing‑pipeline.
Features:
  • DEM masks via ck‑means (k=3 by default)
  • VI masks via a user‑supplied band (default 1) with:
      – static or adaptive (otsu/percentile) threshold
      – optional dead‑tissue band (<= dead‑vi)
      – optional morphology closing
  • Background removal using:
      – per‑plot NIR file (folder NIR_by_plot) if provided
      – otherwise the NIR band (index 5) from the raster itself
  • Output masks are written to <date>/masks/{mask_prefix}{VI}_mask/
  • Batch processing of multi‑date folders
"""

import argparse
import os
import sys

import numpy as np
import rasterio
import ckwrap  # ckmeans clustering for DEM masks

try:
    import cv2  # optional for morphology
    _HAS_CV2 = True
except Exception:
    _HAS_CV2 = False

# ----------------------------------------------------------------------
def _write_mask_like(src, mask_array, out_path, nodata_val=0):
    """Write a 1‑band uint8 mask that retains the input profile."""
    out_profile = src.profile.copy()
    out_profile.update(
        count=1, dtype="uint8", nodata=nodata_val, compress="LZW"
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with rasterio.open(out_path, "w", **out_profile) as dst:
        dst.write(mask_array.astype(np.uint8), 1)


# ----------------------------------------------------------------------
def generate_masks_dem(image_folder, mask_folder, k=3):
    """Generate DEM masks by ck‑means (k clusters)."""
    os.makedirs(mask_folder, exist_ok=True)
    for fn in os.listdir(image_folder):
        if not fn.lower().endswith(".tif"):
            continue
        in_fp = os.path.join(image_folder, fn)
        out_fp = os.path.join(mask_folder, fn)
        try:
            with rasterio.open(in_fp) as src:
                dem = src.read(1, masked=True)
                dem = np.ma.masked_where((dem == -9999) | dem.mask, dem)

                if dem.count() == 0:
                    mask = np.zeros(dem.shape, dtype=np.uint8)
                    _write_mask_like(src, mask, out_fp)
                    continue

                vmin, vmax = dem.min(), dem.max()
                denom = max(1e-12, float(vmax - vmin))
                scaled = (dem - vmin) / denom * 255.0  # 0‑255, mask still maintained
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
def _adaptive_threshold(band_arr, method="otsu", percentile=5):
    """Return a per‑image threshold for the VI band."""
    vals = band_arr.compressed()
    if vals.size == 0:
        return np.inf
    if method == "otsu":
        norm = 255.0 * (vals - vals.min()) / (vals.max() - vals.min() + 1e-12)
        norm = norm.astype(np.uint8)
        _, thr_bin = cv2.threshold(
            norm, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
        thr = thr_bin / 255.0 * (vals.max() - vals.min()) + vals.min()
    elif method == "percentile":
        thr = np.percentile(vals, percentile)
    else:
        raise ValueError("unsupported adaptive method")
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
    nir_folder=None,
    nir_band_index=5,
    nir_bg_factor=1.5,
):
    """Generate plant masks from a single VI band."""
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
                # ---- VI band ----
                band = src.read(band_index, masked=True)

                # ---- background mask (black plastic) ----
                bg_mask = None

                # 1) try per‑plot NIR file if directory supplied
                if nir_folder:
                    nir_fp = os.path.join(nir_folder, fn)
                    if os.path.exists(nir_fp):
                        with rasterio.open(nir_fp) as nir_src:
                            nir = nir_src.read(1, masked=True)
                            thr_val = np.percentile(nir.compressed(), nir_bg_factor)
                            bg_mask = ~nir.mask & (nir <= thr_val)

                # 2) fallback to orthomosaic NIR band
                if bg_mask is None and src.count >= nir_band_index:
                    nir = src.read(nir_band_index, masked=True)
                    thr_val = np.percentile(nir.compressed(), nir_bg_factor)
                    bg_mask = ~nir.mask & (nir <= thr_val)

                # ---- primary vegetation mask ----
                if adaptive_method is not None:
                    threshold = _adaptive_threshold(
                        band, method=adaptive_method, percentile=adaptive_percentile
                    )
                    veg = ~band.mask & (band < threshold)
                else:
                    if lower_threshold is None:
                        veg = ~band.mask & (band <= upper_threshold)
                    elif upper_threshold is None:
                        veg = ~band.mask & (band >= lower_threshold)
                    else:
                        veg = ~band.mask & (
                            band >= lower_threshold and band <= upper_threshold
                        )

                # ---- dead‑tissue band (optional) ----
                if dead_threshold is not None:
                    dead = ~band.mask & (band <= dead_threshold)
                    veg = veg | dead

                # ---- remove background ----
                if bg_mask is not None:
                    veg = veg & (~bg_mask)

                # ---- build binary mask ----
                mask = np.zeros(band.shape, dtype=np.uint8)
                mask[veg] = 255

                # ---- optional morphology close ----
                if kernel is not None:
                    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

                _write_mask_like(src, mask, out_fp)
        except Exception as e:
            print(f"[VI] skip {in_fp}: {e}")

    print(f"[VI] masks saved → {mask_folder}")


# ----------------------------------------------------------------------
def _determine_mask_dir(root, vi_subdir, mask_prefix="chat"):
    """Return the output directory for a VI mask."""
    vi_name = os.path.basename(vi_subdir).split("_")[0]  # e.g. NDVI or OSAVI
    return os.path.join(root, "masks", f"{mask_prefix}{vi_name}_mask")


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
    mask_prefix="chat",
    nir_folder=None,
):
    """Run mask generation in batch mode over multiple date folders."""
    for folder in os.listdir(batch_folder):
        root = os.path.join(batch_folder, folder)
        if not os.path.isdir(root):
            continue

        # DEM masks (unchanged naming)
        dem_img = os.path.join(root, dem_subdir)
        if os.path.isdir(dem_img):
            dem_mask = os.path.join(
                root, "masks", os.path.basename(dem_subdir).split("_")[0] + "_mask"
            )
            generate_masks_dem(dem_img, dem_mask)

        # VI masks
        vi_img = os.path.join(root, vi_subdir)
        if os.path.isdir(vi_img):
            vi_mask = _determine_mask_dir(root, vi_subdir, mask_prefix)
            generate_masks_vi(
                vi_img,
                vi_mask,
                lower_threshold=vi_lt,
                upper_threshold=vi_ut,
                morph_close=morph_close,
                adaptive_method=adaptive_method,
                adaptive_percentile=adaptive_percentile,
                dead_threshold=dead_threshold,
                nir_folder=nir_folder,
            )


# ----------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate GeoTIFF masks for VI (optionally adaptive) and DEM."
    )
    # generic
    parser.add_argument("ipath", nargs="?", help="Path to a single VI/DEM folder.")
    parser.add_argument("mpath", nargs="?", help="Output mask folder for single mode.")
    parser.add_argument(
        "--mode", choices=["vi", "dem"], default=None, help="Force single‑folder mode."
    )
    parser.add_argument("--lt", type=float, default=None, help="Lower VI threshold.")
    parser.add_argument("--ut", type=float, default=None, help="Upper VI threshold.")
    parser.add_argument("--morph", type=int, default=5, help="Morph closing kernel.")
    parser.add_argument("--band", type=int, default=1, help="VI band index.")
    parser.add_argument(
        "--adaptive",
        type=str,
        choices=["otsu", "percentile"],
        default=None,
        help="Per‑image adaptive method.",
    )
    parser.add_argument(
        "--adaptive-percentile",
        type=int,
        default=5,
        help="Percentile value when using adaptive percentile.",
    )
    parser.add_argument(
        "--dead-vi",
        type=float,
        default=None,
        help="Include VI <= this value as dead tissue.",
    )
    parser.add_argument(
        "--nir-folder",
        type=str,
        default=None,
        help="Folder that contains per‑plot NIR files (same names as VI files).",
    )
    parser.add_argument(
        "--mask-prefix",
        type=str,
        default="chat",
        help="Prefix for mask folders (e.g. chatNDVI_mask).",
    )

    # batch
    parser.add_argument(
        "--batchpath",
        type=str,
        help="Path containing multiple date folders for batch mode.",
    )
    parser.add_argument(
        "--vi-subdir",
        type=str,
        default="OSAVI_by_plot",
        help="Name of the VI subfolder inside each date folder.",
    )
    parser.add_argument(
        "--dem-subdir",
        type=str,
        default="dem_by_plot",
        help="Name of the DEM subfolder inside each date folder.",
    )
    parser.add_argument(
        "--vi-lt",
        type=float,
        default=None,
        help="Lower VI threshold for batch mode.",
    )
    parser.add_argument(
        "--vi-ut",
        type=float,
        default=None,
        help="Upper VI threshold for batch mode.",
    )
    parser.add_argument(
        "--vi-morph",
        type=int,
        default=5,
        help="Morph closing kernel for batch mode.",
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
            mask_prefix=args.mask_prefix,
            nir_folder=args.nir_folder,
        )
    else:
        mode = args.mode
        input_name = os.path.basename(args.ipath).lower() if args.ipath else ""
        if mode is None:
            mode = "dem" if "dem" in input_name else "vi"
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
                nir_folder=args.nir_folder,
            )
