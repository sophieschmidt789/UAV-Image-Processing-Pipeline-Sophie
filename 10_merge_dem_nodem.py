# 10_merge_dem_nodem.py
# 1) Copy (flatten) per-date DEM/NoDEM Excel files to top-level dem_trait/ & nodem_trait/
# 2) Merge paired files by auto-detected ID column (tif-like values) into merged_trait/
# Usage:
#   python 10_merge_dem_nodem.py --batchpath E:\AS

import argparse
import re
import shutil
from pathlib import Path
import pandas as pd

TIFF_LIKE_RE = re.compile(r".*\.tif(f)?$", re.IGNORECASE)

# replace detect_id_column with this
def detect_id_column(df: pd.DataFrame) -> str | None:
    """Auto-detect an ID column (prefer tif-like values, else fallback to known names)."""

    def _tif_hits(series: pd.Series) -> int:
        s = series.astype(str).str.strip().str.lower()
        return s.str.endswith((".tif", ".tiff")).sum()

    # 1) prefer columns that look like *.tif / *.tiff
    best_col, best_hits = None, 0
    for col in df.columns:
        hits = _tif_hits(df[col])
        if hits > best_hits:
            best_col, best_hits = col, hits
    if best_hits > 0:
        return best_col

    # 2) fallback names (case-insensitive)
    for cand in ["Image ID", "id", "plotid", "plot_id", "plantid", "plant_id"]:
        for c in df.columns:
            if c.lower() == cand.lower():
                return c

    return None

def flatten_to_top_level(base: Path) -> tuple[list[Path], list[Path]]:
    """
    Copy *.xlsx from each <date>/dem_trait and <date>/nodem_trait into
    <base>/dem_trait and <base>/nodem_trait, keeping the same filename.
    Overwrites if a file with the same name already exists.
    Returns lists of paths that now exist in the top-level dem/nodem folders.
    """
    top_dem = base / "dem_trait"
    top_nodem = base / "nodem_trait"
    top_dem.mkdir(parents=True, exist_ok=True)
    top_nodem.mkdir(parents=True, exist_ok=True)

    copied_dem, copied_nodem = [], []

    # iterate immediate subfolders of base (date folders)
    for child in sorted(base.iterdir()):
        if not child.is_dir():
            continue
        if child.name in ("dem_trait", "nodem_trait", "merged_trait"):
            continue

        dem_src = child / "dem_trait"
        nodem_src = child / "nodem_trait"

        if dem_src.is_dir():
            for f in dem_src.glob("*.xlsx"):
                dst = top_dem / f.name
                shutil.copy2(f, dst)  # overwrite if exists
                copied_dem.append(dst)
                print(f"[COPY] {f} -> {dst}")

        if nodem_src.is_dir():
            for f in nodem_src.glob("*.xlsx"):
                dst = top_nodem / f.name
                shutil.copy2(f, dst)  # overwrite if exists
                copied_nodem.append(dst)
                print(f"[COPY] {f} -> {dst}")

    print(f"[OK] Top-level dem_trait has {len(list(top_dem.glob('*.xlsx')))} files.")
    print(f"[OK] Top-level nodem_trait has {len(list(top_nodem.glob('*.xlsx')))} files.")
    return list(top_dem.glob("*.xlsx")), list(top_nodem.glob("*.xlsx"))

def merge_pairs(base: Path):
    """
    Pair files by identical filename between <base>/dem_trait and <base>/nodem_trait,
    auto-detect ID columns (tif-like), and write merged files into <base>/merged_trait.
    """
    dem_dir = base / "dem_trait"
    nodem_dir = base / "nodem_trait"
    out_dir = base / "merged_trait"
    out_dir.mkdir(parents=True, exist_ok=True)

    demfiles = sorted(dem_dir.glob("*.xlsx"))
    nodem_map = {p.name: p for p in nodem_dir.glob("*.xlsx")}

    merged_count = 0
    for demfile in demfiles:
        nodemfile = nodem_map.get(demfile.name)
        if nodemfile is None:
            print(f"[WARN] Missing NoDEM for {demfile.name}, skipping.")
            continue

        df_dem = pd.read_excel(demfile)
        df_nodem = pd.read_excel(nodemfile)

        dem_id = detect_id_column(df_dem)
        nodem_id = detect_id_column(df_nodem)
        if not dem_id or not nodem_id:
            print(f"[WARN] Could not detect ID in {demfile.name}, skipping.")
            continue

        print(f"[INFO] Pair {demfile.name}: DEM id='{dem_id}', NoDEM id='{nodem_id}'")
        merged = pd.merge(df_dem, df_nodem, left_on=dem_id, right_on=nodem_id, how="outer")

        out_file = out_dir / demfile.name
        merged.to_excel(out_file, index=False)
        print(f"[OK] Wrote {out_file}")
        merged_count += 1

    if merged_count == 0:
        print("[WARN] No merged files created.")
    else:
        print(f"[DONE] Created {merged_count} merged file(s) in {out_dir}")

def main(batchpath: str):
    base = Path(batchpath)
    # 1) flatten/copy to top-level dem_trait & nodem_trait
    flatten_to_top_level(base)
    # 2) merge paired files into merged_trait
    merge_pairs(base)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Flatten DEM/NoDEM xlsx to top-level and merge by tif-like ID.")
    parser.add_argument("--batchpath", type=str, required=True, help="Path to the base folder")
    args = parser.parse_args()
    main(args.batchpath)
