import os
import shutil
import glob
import argparse
from typing import Iterable, List

def move_image_files(base_path: str,
                     folder_pattern: str,
                     file_suffixes: Iterable[str],
                     dest_subfolder: str = "orthos",
                     dry_run: bool = False) -> List[str]:
    """
    Move files whose names end with any suffix in `file_suffixes` from folders
    matching `folder_pattern` (recursively) into a subfolder named `dest_subfolder`
    inside each matched folder.

    Returns a list of "SRC -> DST" strings for moved files.
    """
    moved: List[str] = []

    # Make suffix matching case-insensitive
    suffixes = tuple(s.lower() for s in file_suffixes)

    # Ensure the pattern is recursive (**), and add wildcards if user passed a bare token
    if not any(ch in folder_pattern for ch in "*?["):
        folder_pattern = f"*{folder_pattern}*"
    pattern = os.path.join(os.path.abspath(base_path), "**", folder_pattern)

    # Find all matching folders (recursive)
    folders = [p for p in glob.glob(pattern, recursive=True) if os.path.isdir(p)]

    for folder in folders:
        dest_dir = os.path.join(folder, dest_subfolder)
        for root, _, files in os.walk(folder):
            # Skip scanning the destination folder itself
            if os.path.abspath(root).startswith(os.path.abspath(dest_dir) + os.sep):
                continue

            for file in files:
                if not file.lower().endswith(suffixes):
                    continue

                src = os.path.join(root, file)
                dst = os.path.join(dest_dir, file)

                if dry_run:
                    moved.append(f"{src} -> {dst}")
                    continue

                os.makedirs(dest_dir, exist_ok=True)
                if os.path.exists(dst):
                    os.remove(dst)  # overwrite
                shutil.move(src, dst)
                moved.append(f"{src} -> {dst}")

    return moved

def main():
    parser = argparse.ArgumentParser(
        description="Move DEM/ortho (or other) files into a per-folder subdirectory."
    )
    parser.add_argument("base_dir", type=str,
                        help="Path to the base directory (search root).")
    parser.add_argument("--folder-pattern", type=str, default="*_Swb_Cl*",
                        help="Glob pattern for folders under base_dir to search (default: '*_Swb_Cl*').")
    parser.add_argument("--suffixes", type=str, nargs="+", default=["dem.tif", "ortho.tif"],
                        help="File suffixes to match (space-separated). Default: dem.tif ortho.tif")
    parser.add_argument("--dest", type=str, default="orthos",
                        help="Destination subfolder name within each matched folder (default: 'orthos').")
    parser.add_argument("--dry-run", action="store_true",
                        help="List what would be moved without making changes.")
    args = parser.parse_args()

    moved = move_image_files(
        base_path=args.base_dir,
        folder_pattern=args.folder_pattern,
        file_suffixes=args.suffixes,
        dest_subfolder=args.dest,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print("[DRY RUN] The following moves would occur:")
    else:
        print("Finished. Files moved:")
    for line in moved:
        print(line)
    if not moved:
        print("No files matched the given pattern/suffixes.")

if __name__ == "__main__":
    main()
