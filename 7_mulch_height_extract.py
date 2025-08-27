"""
7_mulch_height_extract.py
-------------------------
Extract mulch height stats from DEM using binary masks.

Usage examples:
  # Single folder
  python 7_mulch_height_extract.py --ipath F:\2023_Swb_Cl_maps\20240509_test\20231111_Swb_Cl

  # Batch, default pattern (*AS_S2*)
  python 7_mulch_height_extract.py --batchpath F:\AS\batch1

  # Batch with custom pattern (auto-wildcards, case-insensitive)
  python 7_mulch_height_extract.py --batchpath C:\...\23_24_GC_SB_CL_RP --folder-pattern "_Swb_Cl"

  # Multiple patterns (comma or semicolon separated)
  python 7_mulch_height_extract.py --batchpath C:\...\root --folder-pattern "*_Swb_Cl*,*AS_S2*"

  # Different mask subfolder name
  python 7_mulch_height_extract.py --batchpath C:\...\root --mask-subdir masks_overlapping_mulch
"""

import os
import cv2
import numpy as np
import pandas as pd
import argparse
import fnmatch

def process_image(dem_image_path, final_mask_path, output_dict):
    # Date derived from parent name: <date>_...
    date_component = os.path.basename(os.path.dirname(os.path.dirname(dem_image_path))).split('_')[0]

    imarray_dem = cv2.imread(dem_image_path, cv2.IMREAD_UNCHANGED)
    imarray_mask = cv2.imread(final_mask_path, cv2.IMREAD_UNCHANGED)

    if imarray_dem is None or imarray_mask is None:
        print(f"[WARN] Missing DEM or mask for {dem_image_path} (mask at {final_mask_path}). Skipping.")
        return

    # Convert DEM nodata to NaN
    imarray_dem = imarray_dem.astype(np.float32, copy=False)
    imarray_dem[imarray_dem == -9999] = np.nan

    # Align shapes if needed
    if imarray_dem.shape != imarray_mask.shape:
        min_rows = min(imarray_dem.shape[0], imarray_mask.shape[0])
        min_cols = min(imarray_dem.shape[1], imarray_mask.shape[1])
        imarray_dem = imarray_dem[:min_rows, :min_cols]
        imarray_mask = imarray_mask[:min_rows, :min_cols]

    # Ensure mask is uint8 for OpenCV
    if imarray_mask.dtype != np.uint8:
        imarray_mask = imarray_mask.astype(np.uint8, copy=False)

    # Apply mask
    masked_dem = cv2.bitwise_and(imarray_dem, imarray_dem, mask=imarray_mask)
    # Pixels unselected by mask become 0; set to NaN explicitly
    masked_dem[masked_dem == 0] = np.nan

    # Use central 90% ROI (5–95% in both axes)
    h, w = masked_dem.shape[:2]
    r0, r1 = int(h * 0.05), int(h * 0.95)
    c0, c1 = int(w * 0.05), int(w * 0.95)
    roi = masked_dem[r0:r1, c0:c1]

    # Flatten and compute mid-40% mean (robust to tails)
    flat = roi.reshape(-1)
    valid = flat[~np.isnan(flat)]
    if valid.size == 0:
        avg_val = np.nan
    else:
        valid.sort()
        lo = int(0.30 * valid.size)
        hi = int(0.70 * valid.size)
        mid = valid[lo:hi]
        avg_val = float(np.nanmean(mid)) if mid.size else np.nan

    # Collect row
    dem_data = {
        'Date': date_component,
        'Image ID': os.path.basename(dem_image_path),
        'Average Height (5%-95%)': avg_val
    }
    output_dict.setdefault(dem_data['Date'], []).append(dem_data)

def trait_extract_dem(input_folder, mask_subdir="masks_overlapping_mulch"):
    # Results go next to the input folder
    output_folder = os.path.join(os.path.dirname(input_folder), "mulch_height")
    os.makedirs(output_folder, exist_ok=True)

    output_data = {}
    found_any = False

    for root, _, files in os.walk(input_folder):
        if os.path.basename(root).endswith('dem_by_plot'):
            for file in files:
                if file.lower().endswith('.tif'):
                    found_any = True
                    dem_image_path = os.path.join(root, file)
                    image_name = os.path.basename(dem_image_path)
                    final_mask_path = os.path.join(input_folder, mask_subdir, image_name)
                    process_image(dem_image_path, final_mask_path, output_data)

    if not found_any:
        print(f"[WARN] No .tif under {input_folder}\\**\\dem_by_plot — nothing to do.")
        return

    # Write one Excel per date
    for date, data_list in output_data.items():
        df = pd.DataFrame(data_list)
        out_xlsx = os.path.join(output_folder, f"{date}.xlsx")
        df.to_excel(out_xlsx, index=False)
        print(f"[OK] Saved mulch height → {out_xlsx}")

def _normalize_patterns(pattern_str):
    """
    Accept comma/semicolon-separated patterns.
    Make matching case-insensitive.
    If a token has no wildcard, wrap it as *token*.
    """
    if not pattern_str:
        return ['*AS_S2*']  # default
    raw = [p.strip() for p in pattern_str.replace(';', ',').split(',') if p.strip()]
    norms = []
    for p in raw:
        if not any(ch in p for ch in '*?['):
            p = f"*{p}*"
        norms.append(p.lower())
    return norms

def _matches_any(name, patterns):
    n = name.lower()
    return any(fnmatch.fnmatch(n, pat) for pat in patterns)

def trait_extract_dem_batch(batch_folder, folder_pattern="*AS_S2*", mask_subdir="masks_overlapping_mulch"):
    patterns = _normalize_patterns(folder_pattern)
    processed = 0
    for folder in os.listdir(batch_folder):
        input_folder = os.path.join(batch_folder, folder)
        if os.path.isdir(input_folder) and _matches_any(folder, patterns):
            print(f"[INFO] Processing: {input_folder}")
            trait_extract_dem(input_folder, mask_subdir=mask_subdir)
            processed += 1
    if processed == 0:
        print(f"[WARN] No subfolders matched pattern(s): {patterns} under {batch_folder}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mulch DEM extraction from images with masks.")
    parser.add_argument("--ipath", type=str, help="Path to one date folder (e.g. 20231111_Swb_Cl_AS_S2).")
    parser.add_argument("--batchpath", type=str, help="Path to the folder containing multiple date folders.")
    parser.add_argument("--folder-pattern", type=str, default="*AS_S2*",
                        help="Glob pattern(s) for batch subfolders. Example: '*_Swb_Cl*' or multiple: '*_Swb_Cl*,*AS_S2*'.")
    parser.add_argument("--mask-subdir", type=str, default="masks_overlapping_mulch",
                        help="Name of mask subfolder (default='masks_overlapping_mulch').")

    args = parser.parse_args()

    if args.batchpath:
        trait_extract_dem_batch(args.batchpath, folder_pattern=args.folder_pattern, mask_subdir=args.mask_subdir)
    elif args.ipath:
        trait_extract_dem(args.ipath, mask_subdir=args.mask_subdir)
    else:
        raise SystemExit("Provide either --ipath or --batchpath")
