# 10_flatten_traits.py
# Collect all <date>\dem_trait\*.xlsx into <base>\dem_trait\
# and all <date>\nodem_trait\*.xlsx into <base>\nodem_trait\
# Usage:
#   python 10_flatten_traits.py --batchpath C:\path\to\23_24_GC_SB_CL_RP
#   python 10_flatten_traits.py --batchpath C:\path\to\23_24_GC_SB_CL_RP --move

import os
import argparse
from pathlib import Path
import shutil

def _xlsx_list(dirpath: Path):
    return [p for p in dirpath.glob("*.xlsx") if not p.name.startswith("~$")]

def _copy_or_move(src: Path, dst: Path, do_move: bool):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if do_move:
        shutil.move(str(src), str(dst))
        print(f"[MOVE] {src} -> {dst}")
    else:
        shutil.copy2(str(src), str(dst))
        print(f"[COPY] {src} -> {dst}")

def _flatten_one_kind(base: Path, subdir_name: str, do_move: bool) -> int:
    """Flatten all <date>\<subdir_name>\*.xlsx into <base>\<subdir_name>\."""
    outdir = base / subdir_name
    outdir.mkdir(parents=True, exist_ok=True)
    count = 0

    for child in sorted(base.iterdir()):
        if not child.is_dir():
            continue
        # skip the central output folder itself
        if child.resolve() == outdir.resolve():
            continue

        src_dir = child / subdir_name
        if not src_dir.is_dir():
            continue

        for fp in _xlsx_list(src_dir):
            dst = outdir / fp.name
            # if name clashes, add date-folder suffix
            if dst.exists():
                dst = outdir / f"{fp.stem}__{child.name}{fp.suffix}"
            _copy_or_move(fp, dst, do_move)
            count += 1

    print(f"[OK] {subdir_name}: placed {count} file(s) into {outdir}")
    return count

def main(batchpath: str, move_files: bool, dem_dir: str, nodem_dir: str):
    base = Path(batchpath).resolve()
    if not base.is_dir():
        raise SystemExit(f"[ERR] Not a directory: {base}")

    total = 0
    total += _flatten_one_kind(base, dem_dir, move_files)
    total += _flatten_one_kind(base, nodem_dir, move_files)

    if total == 0:
        print(f"[WARN] No Excel files found under per-date '{dem_dir}' or '{nodem_dir}' folders.")

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Flatten per-date dem_trait and nodem_trait Excel files into base folders (no merge).")
    p.add_argument("--batchpath", required=True, help="Base directory containing date subfolders.")
    p.add_argument("--move", action="store_true", help="Move files instead of copying.")
    p.add_argument("--dem-dir", default="dem_trait", help="Per-date DEM trait subfolder name (and base target).")
    p.add_argument("--nodem-dir", default="nodem_trait", help="Per-date NoDEM/VI trait subfolder name (and base target).")
    args = p.parse_args()
    main(args.batchpath, move_files=args.move, dem_dir=args.dem_dir, nodem_dir=args.nodem_dir)
