#!/usr/bin/env python
"""
sophieCHAT_4_generate_mask_on_1orbatch.py
------------------------------------------
Generate binary masks from a VI or DEM.
The script now writes masks into a sub‑folder that reflects the VI type,
e.g. CHAT_NDVI_mask for NDVI and CHAT_OSAVI_mask for OSAVI.
"""
import os
import argparse
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
import ckwrap  # ckmeans clustering for DEM masks
try:
    import cv2  # for optional morphology (closing)
    _HAS_CV2 = True
except Exception:
    _HAS_CV2 = False


# ----------------------------------------------------------------------
def _write_mask_like(src, mask_array, out_path, nodata_val=0):
    """Write a 1‑band uint8 mask that keeps the source profile."""
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
    """Generate DEM masks by ck‑means (k clusters)."""
    os.makedirs(mask_folder, exist_ok=True)
    for fn in os.listdir(image_folder):
        if not fn.lower().endswith(".tif"):
            continue
        in_fp = os.path.join(image_folder, fn)
        out_fp = os.path.join(mask_folder, fn)
        try:
            with rasterio.open(in_fp) as src:
                dem = src.read(1, masked=True)  # honor nodata
                dem = np.ma.masked_where((dem == -9999) | dem.mask, dem)
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
def generate_masks_vi(
    image_folder,
    mask_folder,
    lower_threshold=None,
    upper_threshold=None,
    morph_close=5,
    band_index=1,
    background_image=None,
    ref_offset=0.0,
):
    """
    Generate plant masks from a single VI band.

    If a background_image is supplied and its shape does not match the
    shape of the current tile, the background is resized (nearest‑neighbour)
    to the tile’s dimensions before the comparison is performed.
    """
    if lower_threshold is None and upper_threshold is None and background_image is None:
        raise ValueError(
            "Provide at least one of lower_threshold, upper_threshold, or a background image."
        )

    os.makedirs(mask_folder, exist_ok=True)

    # optional morphological closing kernel
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
                # -----------------------------------------------------------------
                # 1. read the VI band (masked array)
                band = src.read(band_index, masked=True)

                # 2. build the basic threshold mask (lower/upper or one‑sided)
                mask = np.zeros(band.shape, dtype=np.uint8)
                valid = ~band.mask

                if lower_threshold is None:
                    sel = valid & (band <= upper_threshold)
                elif upper_threshold is None:
                    sel = valid & (band >= lower_threshold)
                else:
                    sel = valid & (band >= lower_threshold) & (band <= upper_threshold)

                # -----------------------------------------------------------------
                # 3. background‑mask handling (new part)
                if background_image is not None:
                    # If the background array shape differs from the tile shape,
                    # resize it to the tile’s dimensions.
                    if background_image.shape != band.shape:
                        # -----------------------------------------------------------------
                        # Resize with OpenCV (fast nearest‑neighbour).  If you prefer
                        # pure‑numpy you could use scipy.ndimage.zoom; OpenCV is already
                        # an optional dependency for the morphology step, so it is safe.
                        # -----------------------------------------------------------------
                        bg_resized = cv2.resize(
                            background_image.astype(np.float32),
                            (band.shape[1], band.shape[0]),   # (width, height)
                            interpolation=cv2.INTER_NEAREST,
                        )
                        bg_arr = bg_resized
                    else:
                        bg_arr = background_image

                    # Keep pixels that are NOT brighter than the background (+ offset)
                    bg_sel = band <= (bg_arr + ref_offset)
                    sel = sel & bg_sel   # combine with the VI threshold mask

                # -----------------------------------------------------------------
                # 4. write the final mask
                mask[sel] = 255

                if kernel is not None:
                    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

                _write_mask_like(src, mask, out_fp)

        except Exception as e:
            print(f"[VI] skip {in_fp}: {e}")

    print(f"[VI] masks saved → {mask_folder}")

# ----------------------------------------------------------------------
def _build_background_image(ref_folder, date_subdir, method="max"):
    """
    Build a background reference image for a single date folder.
    All background rasters are re‑projected on‑the‑fly to the geometry
    of the first raster encountered, guaranteeing identical shape.
    """
    date_path = os.path.join(ref_folder, date_subdir)
    if not os.path.isdir(date_path):
        return None

    # collect tif paths
    ref_files = [
        os.path.join(date_path, fn)
        for fn in os.listdir(date_path)
        if fn.lower().endswith('.tif')
    ]
    if not ref_files:
        return None

    # ------------------------------------------------------------------
    # 1️⃣ read the *first* file – it becomes the master geometry
    with rasterio.open(ref_files[0]) as master_src:
        master_arr = master_src.read(1, masked=True)
        master_shape = master_arr.shape
        master_transform = master_src.transform
        master_crs = master_src.crs
        master_nodata = master_src.nodata

    # ------------------------------------------------------------------
    # 2️⃣ read every other file and, if needed, re‑project it
    ref_arrays = [master_arr]                     # first array already matches master
    for fp in ref_files[1:]:
        with rasterio.open(fp) as src:
            arr = src.read(1, masked=True)

            # If shape, transform or CRS differ, re‑project onto master grid
            if (arr.shape != master_shape
                or src.transform != master_transform
                or src.crs != master_crs):
                # Destination buffer that has the master shape
                dst = np.zeros(master_shape, dtype=arr.dtype)

                reproject(
                    source=arr,
                    destination=dst,
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=master_transform,
                    dst_crs=master_crs,
                    resampling=Resampling.nearest,
                    src_nodata=src.nodata,
                    dst_nodata=master_nodata,
                )
                # Convert the re‑projected array back into a masked array
                arr = np.ma.masked_where(dst == master_nodata, dst)

            ref_arrays.append(arr)

    # ------------------------------------------------------------------
    # 3️⃣ now all arrays share the same shape → safe to stack
    stacked = np.ma.stack(ref_arrays, axis=0)   # shape (N, H, W)

    # ------------------------------------------------------------------
 # 4️⃣ aggregate
    if method == "max":
        buf = stacked.max(axis=0)
    elif method == "mean":
        buf = stacked.mean(axis=0)
    elif method == "median":
        buf = np.ma.median(stacked, axis=0)
    else:
        raise ValueError(f"Unknown aggregation method: {method}")

    # Return a regular (filled) numpy array – the mask routine expects that.
    return buf.filled(0.0)


# ----------------------------------------------------------------------
def generate_masks_for_batch(
    batch_folder,
    vi_subdir="OSAVI_by_plot",
    dem_subdir="dem_by_plot",
    vi_lt=None,
    vi_ut=None,
    morph_close=5,
    ref_dir=None,
    ref_method="max",
    ref_offset=0.0,
):
    """Run mask generation across multiple date folders."""
    for folder in os.listdir(batch_folder):
        root = os.path.join(batch_folder, folder)
        if not os.path.isdir(root):
            continue

        # DEM masks ---------------------------------------------------
        dem_image_folder = os.path.join(root, dem_subdir)
        if os.path.isdir(dem_image_folder):
            dem_mask_folder = os.path.join(
                root,
                "masks",
                os.path.basename(dem_image_folder).split("_")[0] + "_mask",
            )
            generate_masks_dem(dem_image_folder, dem_mask_folder)

        # VI masks ---------------------------------------------------
        vi_image_folder = os.path.join(root, vi_subdir)
        if os.path.isdir(vi_image_folder):
            # Derive the correct output folder name from the VI sub‑folder.
            # Example: vi_subdir == "NDVI_by_plot" -> "CHAT_NDVI_mask"
            vi_prefix = vi_subdir.split("_")[0].upper()
            vi_mask_folder = os.path.join(root, "masks", f"CHAT_{vi_prefix}_mask")

            # build a background image from the reference folder, if present
            background_image = None
            if ref_dir:
                background_image = _build_background_image(ref_dir, folder, method=ref_method)
                if background_image is None:
                    print(f"[WARN] No reference images for date {folder}")

            generate_masks_vi(
                vi_image_folder,
                vi_mask_folder,
                lower_threshold=vi_lt,
                upper_threshold=vi_ut,
                morph_close=morph_close,
                background_image=background_image,
                ref_offset=ref_offset,
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
    parser.add_argument("--morph", type=int, default=5, help="Morph closing kernel (pixels). 0=off.")
    parser.add_argument("--band", type=int, default=1, help="Band index to read for VI (default 1).")

    # Reference image options (global for batch)
    parser.add_argument(
        "--ref-dir",
        type=str,
        default=None,
        help="Root folder containing reference (background) images.",
    )
    parser.add_argument(
        "--ref-method",
        choices=["max", "mean", "median"],
        default="max",
        help="How to aggregate multiple references per date.",
    )
    parser.add_argument(
        "--ref-offset",
        type=float,
        default=0.0,
        help="Small offset added to the reference value when deciding background.",
    )

    # Batch options
    parser.add_argument(
        "--batchpath",
        type=str,
        help="Batch mode: path containing multiple date folders.",
    )
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
        "--vi-lt", type=float, default=None, help="Batch: VI lower threshold."
    )
    parser.add_argument(
        "--vi-ut", type=float, default=None, help="Batch: VI upper threshold."
    )
    parser.add_argument(
        "--vi-morph", type=int, default=5, help="Batch: morphology kernel (pixels). 0=off."
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
            ref_dir=args.ref_dir,
            ref_method=args.ref_method,
            ref_offset=args.ref_offset,
        )
    else:
        # infer mode if not provided
        if not args.ipath or not args.mpath:
            raise SystemExit("Provide both ipath and mpath for single mode.")
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
                background_image=None,
                ref_offset=args.ref_offset,
            )
