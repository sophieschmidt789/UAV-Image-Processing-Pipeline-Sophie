import os
import argparse
import numpy as np
import rasterio
import ckwrap  # ckmeans
try:
    import cv2  # for optional morphology (closing)
    _HAS_CV2 = True
except Exception:
    _HAS_CV2 = False

def _write_mask_like(src, mask_array, out_path, nodata_val=0):
    qgis_python = r'"C:\Program Files\QGIS 3.44.3\bin\python-qgis.bat"'
    profile = src.profile.copy()
    profile.update({
        "count": 1,
        "dtype": "uint8",
        "nodata": nodata_val,
        "compress": "LZW"
    })
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(mask_array.astype(np.uint8), 1)

def generate_masks_dem(image_folder, mask_folder, k=3):
    os.makedirs(mask_folder, exist_ok=True)
    for fn in os.listdir(image_folder):
        if not fn.lower().endswith(".tif"):
            continue
        in_fp = os.path.join(image_folder, fn)
        out_fp = os.path.join(mask_folder, fn)
        try:
            with rasterio.open(in_fp) as src:
                dem = src.read(1, masked=True)  # honor nodata
                # also mask legacy -9999 if present
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

def generate_masks_vi(image_folder, mask_folder,
                      lower_threshold=None, upper_threshold=None,
                      morph_close=5, band_index=1):
    if lower_threshold is None and upper_threshold is None:
        raise ValueError("Provide at least one of lower_threshold or upper_threshold.")
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
                band = src.read(band_index, masked=True)  # masked array

                # build binary mask (uint8) on valid pixels only
                mask = np.zeros(band.shape, dtype=np.uint8)
                valid = ~band.mask
                if lower_threshold is None:
                    sel = valid & (band <= upper_threshold)
                elif upper_threshold is None:
                    sel = valid & (band >= lower_threshold)
                else:
                    sel = valid & (band >= lower_threshold) & (band <= upper_threshold)
                mask[sel] = 255

                # optional morphology closing to fill small holes
                if kernel is not None:
                    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

                _write_mask_like(src, mask, out_fp)
        except Exception as e:
            print(f"[VI] skip {in_fp}: {e}")
    print(f"[VI] masks saved → {mask_folder}")

def generate_masks_for_batch(batch_folder,
                             vi_subdir='OSAVI_by_plot',
                             dem_subdir='dem_by_plot',
                             vi_lt=None, vi_ut=None,
                             morph_close=5):
    for folder in os.listdir(batch_folder):
        root = os.path.join(batch_folder, folder)
        if not os.path.isdir(root):
            continue

        dem_image_folder = os.path.join(root, dem_subdir)
        if os.path.isdir(dem_image_folder):
            dem_mask_folder = os.path.join(root, "masks",
                                           os.path.basename(dem_image_folder).split("_")[0] + "_mask")
            generate_masks_dem(dem_image_folder, dem_mask_folder)

        vi_image_folder = os.path.join(root, vi_subdir)
        if os.path.isdir(vi_image_folder):
            vi_mask_folder = os.path.join(root, "masks",
                                          os.path.basename(vi_image_folder).split("_")[0] + "_mask")
            generate_masks_vi(vi_image_folder, vi_mask_folder,
                              lower_threshold=vi_lt, upper_threshold=vi_ut,
                              morph_close=morph_close)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate GeoTIFF masks for VI (flexible) and DEM (ckmeans), preserving CRS.")
    parser.add_argument("ipath", nargs="?", help="Path to VI/DEM folder (single mode only).")
    parser.add_argument("mpath", nargs="?", help="Output mask folder (single mode only).")

    # Single-folder options
    parser.add_argument("--mode", choices=["vi", "dem"], default=None,
                        help="Force mode for single-folder run. If omitted, inferred from folder name.")
    parser.add_argument("--lt", type=float, default=None, help="Lower threshold for VI mask.")
    parser.add_argument("--ut", type=float, default=None, help="Upper threshold for VI mask.")
    parser.add_argument("--morph", type=int, default=5, help="Morph closing kernel (pixels). 0=off.")
    parser.add_argument("--band", type=int, default=1, help="Band index to read for VI (default 1).")

    # Batch options
    parser.add_argument("--batchpath", type=str, help="Batch mode: path containing multiple date folders.")
    parser.add_argument("--vi-subdir", type=str, default="OSAVI_by_plot",
                        help="Name of VI subfolder to use in batch (e.g., NDVI_by_plot).")
    parser.add_argument("--dem-subdir", type=str, default="dem_by_plot",
                        help="Name of DEM subfolder to use in batch.")
    parser.add_argument("--vi-lt", type=float, default=None, help="Batch: VI lower threshold.")
    parser.add_argument("--vi-ut", type=float, default=None, help="Batch: VI upper threshold.")
    parser.add_argument("--vi-morph", type=int, default=5, help="Batch: morphology kernel (pixels). 0=off.")

    args = parser.parse_args()

    if args.batchpath:
        generate_masks_for_batch(
            batch_folder=args.batchpath,
            vi_subdir=args.vi_subdir,
            dem_subdir=args.dem_subdir,
            vi_lt=args.vi_lt,
            vi_ut=args.vi_ut,
            morph_close=args.vi_morph
        )
    else:
        # infer mode if not provided
        mode = args.mode
        in_lower = os.path.basename(args.ipath).lower()
        if mode is None:
            mode = "dem" if "dem" in in_lower else "vi"

        if mode == "dem":
            generate_masks_dem(args.ipath, args.mpath)
        else:
            generate_masks_vi(args.ipath, args.mpath,
                              lower_threshold=args.lt,
                              upper_threshold=args.ut,
                              morph_close=args.morph,
                              band_index=args.band)
