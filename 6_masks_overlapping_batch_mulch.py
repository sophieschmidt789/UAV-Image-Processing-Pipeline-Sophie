# 6_masks_overlapping_batch_mulch.py
# ---------------------------------
# Combine per-source mulch masks into a single GeoTIFF mask per image.
# - Preserves CRS/transform (rasterio)
# - Operator: AND / OR
# - Automatically inverts vegetation-like masks (e.g., NDVI/OSAVI) for mulch
#
# Examples:
# Single folder:
#   python 6_masks_overlapping_batch_mulch.py ^
#     --ipath F:\...\masks ^
#     --opath F:\...\masks_overlapping_mulch ^
#     --op AND
#
# Batch:
#   python 6_masks_overlapping_batch_mulch.py ^
#     --batchpath F:\AS\batch1 ^
#     --op AND

import os
import argparse
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling

def _list_mask_dirs(root):
    return [d for d in os.listdir(root)
            if os.path.isdir(os.path.join(root, d)) and not d.startswith(".")]

def _list_common_filenames(root, subdirs, exts=(".tif", ".tiff")):
    sets = []
    for sd in subdirs:
        p = os.path.join(root, sd)
        names = set(fn for fn in os.listdir(p) if fn.lower().endswith(exts))
        sets.append(names)
    return sorted(list(set.intersection(*sets))) if sets else []

def _read_band1_bool(fp):
    with rasterio.open(fp) as src:
        arr = src.read(1, masked=True)
        nodata = src.nodata
        arr = np.ma.masked_where(arr.mask | (arr == -9999) | ((nodata is not None) & (arr == nodata)), arr)
        out = np.zeros(arr.shape, dtype=bool)
        valid = ~arr.mask
        out[valid & (arr > 0)] = True
        return out, src.profile

def _reproject_bool_to_ref(mask_bool, src_profile, ref_profile):
    if (src_profile["crs"] == ref_profile["crs"] and
        src_profile["transform"] == ref_profile["transform"] and
        src_profile["width"] == ref_profile["width"] and
        src_profile["height"] == ref_profile["height"]):
        return mask_bool
    dst = np.zeros((ref_profile["height"], ref_profile["width"]), dtype=np.uint8)
    reproject(
        source=mask_bool.astype(np.uint8),
        destination=dst,
        src_transform=src_profile["transform"],
        src_crs=src_profile["crs"],
        dst_transform=ref_profile["transform"],
        dst_crs=ref_profile["crs"],
        resampling=Resampling.nearest,
        src_nodata=0,
        dst_nodata=0,
    )
    return dst.astype(bool)

def _should_invert(subdir_name, invert_prefixes):
    s = subdir_name.lower()
    return any(s.startswith(p.lower()) for p in invert_prefixes)

def combine_mulch_masks(image_folder, output_folder, op="AND",
                        invert_prefixes=("ndvi", "osavi")):
    os.makedirs(output_folder, exist_ok=True)
    subdirs = _list_mask_dirs(image_folder)
    if not subdirs:
        print(f"[WARN] No mask subfolders in {image_folder}")
        return

    ref_dir = os.path.join(image_folder, subdirs[0])
    common_files = _list_common_filenames(image_folder, subdirs)
    if not common_files:
        print(f"[WARN] No common filenames across: {subdirs}")
        return

    for fn in common_files:
        bool_masks = []
        ref_fp = os.path.join(ref_dir, fn)
        try:
            bm_ref, prof_ref = _read_band1_bool(ref_fp)
        except Exception as e:
            print(f"[skip] {ref_fp}: {e}")
            continue

        if _should_invert(subdirs[0], invert_prefixes):
            bm_ref = ~bm_ref
        bool_masks.append(bm_ref)

        for sd in subdirs[1:]:
            fp = os.path.join(image_folder, sd, fn)
            if not os.path.exists(fp):
                continue
            try:
                bm, prof = _read_band1_bool(fp)
                if _should_invert(sd, invert_prefixes):
                    bm = ~bm
                bm = _reproject_bool_to_ref(bm, prof, prof_ref)
                bool_masks.append(bm)
            except Exception as e:
                print(f"[skip] {fp}: {e}")

        if not bool_masks:
            continue

        stack = np.stack(bool_masks, axis=0)
        if op.upper() == "AND":
            combined = np.all(stack, axis=0)
        elif op.upper() == "OR":
            combined = np.any(stack, axis=0)
        else:
            raise ValueError("op must be AND or OR")

        out_u8 = (combined.astype(np.uint8) * 255)

        out_fp = os.path.join(output_folder, fn)
        try:
            prof = prof_ref.copy()
            prof.update(count=1, dtype="uint8", nodata=0, compress="LZW")
            with rasterio.open(out_fp, "w", **prof) as dst:
                dst.write(out_u8, 1)
        except Exception as e:
            print(f"[write] {out_fp}: {e}")

    print(f"[OK] Mulch masks → {output_folder}")

def combine_mulch_masks_batch(batch_folder, subdir_in="masks",
                              subdir_out="masks_overlapping_mulch",
                              **kwargs):
    for folder in os.listdir(batch_folder):
        root = os.path.join(batch_folder, folder)
        if not os.path.isdir(root):
            continue
        image_folder = os.path.join(root, subdir_in)
        if os.path.isdir(image_folder):
            output_folder = os.path.join(root, subdir_out)
            combine_mulch_masks(image_folder, output_folder, **kwargs)

def main():
    ap = argparse.ArgumentParser(description="Combine per-source mulch masks into georeferenced GeoTIFF (AND/OR).")
    ap.add_argument("--ipath", type=str)
    ap.add_argument("--opath", type=str)
    ap.add_argument("--batchpath", type=str)
    ap.add_argument("--op", type=str, default="AND", choices=["AND", "OR"])
    ap.add_argument("--invert-prefix", type=str, default="ndvi,osavi",
                    help="Comma-separated subfolder prefixes to invert for mulch.")
    ap.add_argument("--subdir-in", type=str, default="masks")
    ap.add_argument("--subdir-out", type=str, default="masks_overlapping_mulch")
    args = ap.parse_args()

    invert_prefixes = [s.strip() for s in args.invert_prefix.split(",") if s.strip()]

    if args.batchpath:
        combine_mulch_masks_batch(
            args.batchpath,
            subdir_in=args.subdir_in,
            subdir_out=args.subdir_out,
            op=args.op,
            invert_prefixes=invert_prefixes,
        )
    else:
        if not args.ipath or not args.opath:
            raise SystemExit("Provide --ipath and --opath (or use --batchpath).")
        combine_mulch_masks(
            args.ipath,
            args.opath,
            op=args.op,
            invert_prefixes=invert_prefixes,
        )

if __name__ == "__main__":
    main()
