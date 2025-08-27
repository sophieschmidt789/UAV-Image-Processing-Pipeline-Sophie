# 9_trait_extract_nodem.py
# suffix 'AS_S2'
# examples:
#   python 9_trait_extract_nodem.py --batchpath E:\AS\batch1
#   python 9_trait_extract_nodem.py --batchpath E:\AS\batch1 --folder-pattern "*_Swb_Cl*"
#   python 9_trait_extract_nodem.py --ipath E:\AS\batch1\20231111_Swb_Cl_AS_S2 --mask-subdir masks_overlapping

import os
import cv2
import numpy as np
import pandas as pd
import argparse
import fnmatch
from skimage import io as skio

def _to_gray_float(arr):
    """Return single-channel float32 image (avg RGB if multi-band)."""
    if arr.ndim == 2:
        return arr.astype(np.float32, copy=False)
    if arr.shape[-1] == 4:
        arr = arr[..., :3]
    if arr.shape[-1] >= 3:
        return arr.astype(np.float32).mean(axis=-1)
    return arr[..., 0].astype(np.float32, copy=False)

def _process_one(nodem_path, mask_path, index_prefix, rows):
    # date from folder name two levels up: <date>_...
    date_component = os.path.basename(os.path.dirname(os.path.dirname(nodem_path))).split('_')[0]
    image_id = os.path.basename(nodem_path)

    nodem = None
    mask = None
    try:
        nodem = skio.imread(nodem_path, plugin='tifffile')
    except Exception as e:
        print(f"[WARN] read nodem failed: {nodem_path} ({e})")
        return
    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
    if mask is None:
        print(f"[WARN] missing mask: {mask_path}")
        return

    gray = _to_gray_float(nodem)

    # align shapes by cropping
    h = min(gray.shape[0], mask.shape[0])
    w = min(gray.shape[1], mask.shape[1])
    gray = gray[:h, :w]
    mask = mask[:h, :w]

    # simple mask apply
    vals = np.where(mask > 0, gray, np.nan).ravel()
    vals = vals[~np.isnan(vals)]
    if vals.size == 0:
        mean_v, std_v = np.nan, np.nan
    else:
        mean_v = float(np.mean(vals))
        std_v  = float(np.std(vals))

    key = (date_component, image_id)
    if key not in rows:
        rows[key] = {'Date': date_component, 'Image ID': image_id}
    rows[key][f'{index_prefix}_Average'] = mean_v
    rows[key][f'{index_prefix}_StdDev'] = std_v

def trait_extract_nodem(ipath, mask_subdir="masks_overlapping"):
    out_dir = os.path.join(ipath, "nodem_trait")
    os.makedirs(out_dir, exist_ok=True)

    rows = {}  # (date, image_id) -> dict
    found = False

    for root, _, files in os.walk(ipath):
        base = os.path.basename(root)
        if base.endswith('_by_plot') and base != 'dem_by_plot':
            index_prefix = base.split('_')[0]  # e.g., NDVI_by_plot -> NDVI
            for fn in files:
                if fn.lower().endswith(".tif"):
                    found = True
                    nodem_path = os.path.join(root, fn)
                    mask_path  = os.path.join(ipath, mask_subdir, fn)
                    _process_one(nodem_path, mask_path, index_prefix, rows)

    if not found:
        print(f"[WARN] no VI/NoDEM TIFFs under {ipath}\\**\\*_by_plot (excluding dem_by_plot)")
        return

    df = pd.DataFrame(list(rows.values()))
    if df.empty:
        print(f"[WARN] no valid rows for {ipath}")
        return

    for date, g in df.groupby('Date'):
        out_path = os.path.join(out_dir, f"{date}.xlsx")
        g.drop(columns=['Date']).to_excel(out_path, index=False)
        print(f"[OK] saved → {out_path}")

def trait_extract_nodem_batch(batchpath, folder_pattern="*AS_S2*", mask_subdir="masks_overlapping"):
    processed = 0
    for folder in os.listdir(batchpath):
        ipath = os.path.join(batchpath, folder)
        if os.path.isdir(ipath) and fnmatch.fnmatch(folder, folder_pattern):
            print(f"[INFO] {ipath}")
            trait_extract_nodem(ipath, mask_subdir=mask_subdir)
            processed += 1
    if processed == 0:
        print(f"[WARN] no subfolders matched '{folder_pattern}' under {batchpath}")

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Simple NoDEM/VI trait extraction using binary masks.")
    p.add_argument("--ipath", type=str, help="One date folder (e.g., ...\\20231111_Swb_Cl_AS_S2)")
    p.add_argument("--batchpath", type=str, help="Folder containing multiple date folders")
    p.add_argument("--folder-pattern", type=str, default="*AS_S2*",
                   help="Glob for batch subfolders (e.g., '*_Swb_Cl*')")
    p.add_argument("--mask-subdir", type=str, default="masks_overlapping",
                   help="Mask subfolder name (default: masks_overlapping)")
    args = p.parse_args()

    if args.batchpath:
        trait_extract_nodem_batch(args.batchpath, folder_pattern=args.folder_pattern, mask_subdir=args.mask_subdir)
    elif args.ipath:
        trait_extract_nodem(args.ipath, mask_subdir=args.mask_subdir)
    else:
        raise SystemExit("Provide either --ipath or --batchpath")
