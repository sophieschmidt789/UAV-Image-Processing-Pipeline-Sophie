import os
import cv2
import numpy as np
import pandas as pd
import argparse
import fnmatch

# ---------- helpers ----------
def _normalize_patterns(pattern_str):
    """Comma/semicolon separated; add wildcards if missing; case-insensitive."""
    if not pattern_str:
        return ['*AS_S2*']
    raw = [p.strip() for p in pattern_str.replace(';', ',').split(',') if p.strip()]
    norm = []
    for p in raw:
        if not any(ch in p for ch in '*?['):
            p = f"*{p}*"
        norm.append(p.lower())
    return norm

def _matches_any(name, patterns):
    n = name.lower()
    return any(fnmatch.fnmatch(n, pat) for pat in patterns)

def _safe_get_ref_height(reference_df, image_id):
    if reference_df is None:
        return np.nan
    s = reference_df.loc[reference_df['Image ID'] == image_id, 'Average Height (5%-95%)']
    return float(s.values[0]) if not s.empty else np.nan

def _safe_get_gsd_mm(gsd_df, date_component):
    if gsd_df is None:
        return np.nan
    s = gsd_df.loc[gsd_df['filename'].astype(str) == str(date_component), 'GSD(mm/pix)']
    return float(s.values[0]) if not s.empty else np.nan

# ---------- core ----------
def process_image(dem_image_path, final_mask_path, date_component,
                  reference_df, gsd_df, keep_absolute, output_dict):
    image_id = os.path.basename(dem_image_path)

    # read rasters
    im_dem = cv2.imread(dem_image_path, cv2.IMREAD_UNCHANGED)
    im_mask = cv2.imread(final_mask_path, cv2.IMREAD_UNCHANGED)

    if im_dem is None or im_mask is None:
        print(f"[WARN] Missing DEM or mask → DEM:{dem_image_path} MASK:{final_mask_path}")
        return

    # DEM to float + nodata to NaN
    im_dem = im_dem.astype(np.float32, copy=False)
    im_dem[im_dem == -9999] = np.nan

    # ensure mask is single-channel uint8 (0/255)
    if im_mask.ndim == 3:
        im_mask = im_mask[:, :, 0]
    if im_mask.dtype != np.uint8:
        im_mask = im_mask.astype(np.uint8, copy=False)

    # align shapes conservatively
    if im_dem.shape != im_mask.shape:
        h = min(im_dem.shape[0], im_mask.shape[0])
        w = min(im_dem.shape[1], im_mask.shape[1])
        im_dem = im_dem[:h, :w]
        im_mask = im_mask[:h, :w]

    # apply mask
    masked = cv2.bitwise_and(im_dem, im_dem, mask=im_mask)
    masked = np.where(im_mask > 0, im_dem, np.nan)

    vals = masked.reshape(-1)
    vals = vals[~np.isnan(vals)]
    if vals.size == 0:
        row = {
            'Date': date_component,
            'Image ID': image_id,
            'Canopy Coverage pixel': np.nan,
            'Canopy Coverage (m^2)': np.nan,
            'Relative Average Height (Top 5%) (cm)': np.nan,
            'Relative Volume (m^3)': np.nan,
        }
        if keep_absolute:
            row.update({
                'Average Height (Top 5%)': np.nan,
                'Volume': np.nan,
            })
        output_dict.setdefault(date_component, []).append(row)
        return

    # stats
    n = vals.size
    k = max(1, int(0.05 * n))
    top5 = np.partition(vals, n - k)[n - k:]
    avg_top5 = float(np.nanmean(top5))
    volume = float(np.nansum(vals))
    coverage_px = int(n)

    # GSD (mm/pix) → cm^2/pix
    gsd_mm = _safe_get_gsd_mm(gsd_df, date_component)
    if np.isnan(gsd_mm):
        px_cm2 = np.nan
        print(f"[WARN] No GSD for date {date_component} in gsd_4_all.xlsx")
    else:
        px_m2 = (gsd_mm / 1000.0) ** 2  # (m/pix)^2

    coverage_m2 = coverage_px * px_m2

    # reference mulch baseline
    ref_h = _safe_get_ref_height(reference_df, image_id)
    if np.isnan(ref_h):
        print(f"[WARN] No reference mulch height for Image ID '{image_id}'")
    rel_avg_cm = (avg_top5 - ref_h) * 100.0 if not np.isnan(ref_h) else np.nan
    rel_vol_m3 = ((volume - coverage_px * ref_h) * px_m2) \
              if not (np.isnan(ref_h) or np.isnan(px_m2)) else np.nan

    row = {
        'Date': date_component,
        'Image ID': image_id,
        'Canopy Coverage pixel': coverage_px,
        'Canopy Coverage (m^2)': coverage_m2,
        'Relative Average Height (Top 5%) (cm)': rel_avg_cm,
        'Relative Volume (m^3)': rel_vol_m3,
    }
    row.update({
        'Relative Average Height (Top 5%) (cm)': avg_top5,  # units = DEM units (often meters)
        'Relative Volume (m^3)': volume,                      # sum of DEM heights over veg pixels (DEM units × pixels)
    })
    output_dict.setdefault(date_component, []).append(row)

def trait_extract_dem(input_folder, mask_subdir="masks_overlapping",
                      reference_subdir="mulch_height",
                      gsd_file=None, keep_absolute=False):
    # paths
    folder_name = os.path.basename(input_folder)
    output_folder = os.path.join(input_folder, "dem_trait")
    os.makedirs(output_folder, exist_ok=True)

    # reference (mulch baseline per image id)
    folder_name = os.path.basename(input_folder)
    date_component = folder_name.split("_")[0]   # e.g. "20231111" from "20231111_Swb_Cl"
    ref_path = os.path.join(os.path.dirname(input_folder), reference_subdir, f"{date_component}.xlsx")

    reference_df = None
    if os.path.exists(ref_path):
        try:
            reference_df = pd.read_excel(ref_path)
        except Exception as e:
            print(f"[WARN] Could not read reference file: {ref_path} ({e})")
    else:
        print(f"[WARN] Reference not found: {ref_path}")

    # GSD table (gsd_4_all.xlsx)
    if gsd_file is None:
        gsd_file = os.path.join(os.path.dirname(input_folder), "metashape_report", "gsd_4_all.xlsx")
    gsd_df = None
    if os.path.exists(gsd_file):
        try:
            gsd_df = pd.read_excel(gsd_file)
        except Exception as e:
            print(f"[WARN] Could not read GSD file: {gsd_file} ({e})")
    else:
        print(f"[WARN] GSD file not found: {gsd_file}")

    # iterate DEMs
    output_data = {}
    found = False
    for root, _, files in os.walk(input_folder):
        if os.path.basename(root).endswith('dem_by_plot'):
            for file in files:
                if file.lower().endswith('.tif'):
                    found = True
                    dem_path = os.path.join(root, file)
                    mask_path = os.path.join(input_folder, mask_subdir, file)
                    date_component = os.path.basename(os.path.dirname(os.path.dirname(dem_path))).split('_')[0]
                    process_image(dem_path, mask_path, date_component,
                                  reference_df, gsd_df, keep_absolute, output_data)
    if not found:
        print(f"[WARN] No .tif under {input_folder}\\**\\dem_by_plot")
        return

    # write per-date xlsx
    for date, rows in output_data.items():
        df = pd.DataFrame(rows)
        out_xlsx = os.path.join(output_folder, f"{date}.xlsx")
        df.to_excel(out_xlsx, index=False)
        print(f"[OK] Saved traits → {out_xlsx}")

def trait_extract_dem_batch(batch_folder, folder_pattern="*AS_S2*",
                            mask_subdir="masks_overlapping",
                            reference_subdir="mulch_height",
                            gsd_file=None, keep_absolute=False):
    patterns = _normalize_patterns(folder_pattern)
    count = 0
    for folder in os.listdir(batch_folder):
        input_folder = os.path.join(batch_folder, folder)
        if os.path.isdir(input_folder) and _matches_any(folder, patterns):
            print(f"[INFO] Processing {input_folder}")
            trait_extract_dem(input_folder, mask_subdir=mask_subdir,
                              reference_subdir=reference_subdir,
                              gsd_file=gsd_file, keep_absolute=keep_absolute)
            count += 1
    if count == 0:
        print(f"[WARN] No subfolders matched {patterns} under {batch_folder}")

# ---------- cli ----------
if __name__ == "__main__":
    p = argparse.ArgumentParser(description="DEM trait extraction (relative to mulch) with flexible batch pattern.")
    p.add_argument("--ipath", type=str, help="Path to one date folder (e.g., ...\\20231111_Swb_Cl_AS_S2)")
    p.add_argument("--batchpath", type=str, help="Path containing multiple date folders.")
    p.add_argument("--folder-pattern", type=str, default="*AS_S2*",
                   help="Glob(s) for batch subfolders; e.g. '*_Swb_Cl*' or 'AS_S2,*_Swb_Cl*'.")
    p.add_argument("--mask-subdir", type=str, default="masks_overlapping",
                   help="Mask subfolder inside each date folder.")
    p.add_argument("--reference-subdir", type=str, default="mulch_height",
                   help="Subfolder (next to date folder) containing mulch baseline Excel per date.")
    p.add_argument("--gsd-file", type=str, default=None,
                   help="Path to gsd_4_all.xlsx (default: ../metashape_report/gsd_4_all.xlsx).")
    p.add_argument("--keep-absolute", action="store_true",
                   help="Also keep absolute Average Height (Top 5%) and Volume columns.")
    args = p.parse_args()

    if args.batchpath:
        trait_extract_dem_batch(args.batchpath,
                                folder_pattern=args.folder_pattern,
                                mask_subdir=args.mask_subdir,
                                reference_subdir=args.reference_subdir,
                                gsd_file=args.gsd_file,
                                keep_absolute=args.keep_absolute)
    elif args.ipath:
        trait_extract_dem(args.ipath,
                          mask_subdir=args.mask_subdir,
                          reference_subdir=args.reference_subdir,
                          gsd_file=args.gsd_file,
                          keep_absolute=args.keep_absolute)
    else:
        raise SystemExit("Provide either --ipath or --batchpath")
