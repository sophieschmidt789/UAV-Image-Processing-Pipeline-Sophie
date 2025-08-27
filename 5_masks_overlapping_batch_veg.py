# python 5_masks_overlapping_batch_veg.py --ipath F:\...\masks --opath F:\...\masks_overlapping --op AND
# python 5_masks_overlapping_batch_veg.py --batchpath F:\AS\batch1 --op OR
import os
import argparse
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
import cv2

def _postprocess_morph(mask_bool, k_close=0, k_open=0):
    """
    mask_bool: HxW bool
    k_close, k_open: odd kernel sizes in pixels; 0 disables the op.
    Returns uint8 (0/255)
    """
    out_u8 = (mask_bool.astype(np.uint8) * 255)

    if k_close and k_close > 1:
        kernelclose = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_close, k_close))
        out_u8 = cv2.morphologyEx(out_u8, cv2.MORPH_CLOSE, kernelclose)
    if k_open and k_open > 1:
        kernelopen = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_open, k_open))
        out_u8 = cv2.morphologyEx(out_u8, cv2.MORPH_OPEN, kernelopen)

    return out_u8

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

def _read_and_binarize(fp):
    with rasterio.open(fp) as src:
        arr = src.read(1, masked=True)
        nodata = src.nodata
        arr = np.ma.masked_where(arr.mask | (arr == -9999) | ((nodata is not None) & (arr == nodata)), arr)
        bin_mask = np.zeros(arr.shape, dtype=bool)
        valid = ~arr.mask
        bin_mask[valid & (arr > 0)] = True
        return bin_mask, src.profile

def _reproject_to_ref(bin_mask, src_profile, ref_profile):
    if (src_profile["crs"] == ref_profile["crs"] and
        src_profile["transform"] == ref_profile["transform"] and
        src_profile["width"] == ref_profile["width"] and
        src_profile["height"] == ref_profile["height"]):
        return bin_mask
    out = np.zeros((ref_profile["height"], ref_profile["width"]), dtype=np.uint8)
    reproject(
        source=bin_mask.astype(np.uint8),
        destination=out,
        src_transform=src_profile["transform"],
        src_crs=src_profile["crs"],
        dst_transform=ref_profile["transform"],
        dst_crs=ref_profile["crs"],
        resampling=Resampling.nearest,
        src_nodata=0,
        dst_nodata=0,
    )
    return out.astype(bool)

def find_overlapping_masks(image_folder, output_folder,
                           op="AND", post_close=0, post_open=0):
    os.makedirs(output_folder, exist_ok=True)
    subdirs = _list_mask_dirs(image_folder)
    if len(subdirs) < 2 and op == "AND":
        print(f"[WARN] Need >=2 subfolders for {op}. Found: {subdirs}")
    if not subdirs:
        print(f"[WARN] No mask subfolders in {image_folder}")
        return

    ref_dir = os.path.join(image_folder, subdirs[0])
    common_files = _list_common_filenames(image_folder, subdirs)
    if not common_files:
        print(f"[WARN] No common file names across {subdirs}")
        return

    for fn in common_files:
        bin_masks = []
        ref_fp = os.path.join(ref_dir, fn)
        try:
            bm_ref, prof_ref = _read_and_binarize(ref_fp)
        except Exception as e:
            print(f"[skip] {ref_fp}: {e}")
            continue
        bin_masks.append(bm_ref)

        for sd in subdirs[1:]:
            fp = os.path.join(image_folder, sd, fn)
            if not os.path.exists(fp):
                continue
            try:
                bm, prof = _read_and_binarize(fp)
                bm = _reproject_to_ref(bm, prof, prof_ref)
                bin_masks.append(bm)
            except Exception as e:
                print(f"[skip] {fp}: {e}")

        if not bin_masks:
            continue

        stack = np.stack(bin_masks, axis=0)

        if op.upper() == "AND":
            combined = np.all(stack, axis=0)
        elif op.upper() == "OR":
            combined = np.any(stack, axis=0)
        else:
            raise ValueError("op must be one of: AND, OR")

        smoothed_u8 = _postprocess_morph(combined, k_close=post_close, k_open=post_open)

        out_fp = os.path.join(output_folder, fn)
        try:
            prof = prof_ref.copy()
            prof.update(count=1, dtype="uint8", nodata=0, compress="LZW")
            with rasterio.open(out_fp, "w", **prof) as dst:
                dst.write(smoothed_u8, 1)
        except Exception as e:
            print(f"[write] {out_fp}: {e}")

    print(f"[OK] Combined masks → {output_folder}")

def find_overlapping_masks_for_batch(batch_folder, **kwargs):
    for folder in os.listdir(batch_folder):
        root = os.path.join(batch_folder, folder)
        if not os.path.isdir(root):
            continue
        image_folder = os.path.join(root, "masks")
        if os.path.isdir(image_folder):
            output_folder = os.path.join(root, "masks_overlapping")
            find_overlapping_masks(image_folder, output_folder, **kwargs)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Combine GeoTIFF masks (AND/OR) with CRS preserved.")
    parser.add_argument("--ipath", type=str)
    parser.add_argument("--opath", type=str)
    parser.add_argument("--batchpath", type=str)
    parser.add_argument("--op", type=str, default="AND", choices=["AND", "OR"])
    parser.add_argument("--post-close", type=int, default=15)
    parser.add_argument("--post-open", type=int, default=2)

    args = parser.parse_args()

    if args.batchpath:
        find_overlapping_masks_for_batch(args.batchpath,
                                         op=args.op,
                                         post_close=args.post_close,
                                         post_open=args.post_open)
    else:
        if not args.ipath or not args.opath:
            raise SystemExit("Provide --ipath and --opath for single run (or use --batchpath).")
        find_overlapping_masks(args.ipath, args.opath,
                               op=args.op,
                               post_close=args.post_close,
                               post_open=args.post_open)
