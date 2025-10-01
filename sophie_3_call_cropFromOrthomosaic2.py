import os
import sys
import subprocess
import argparse

def main(base_dir: str, folder_pattern: str, subdir: str, shp_path: str):
    qgis_python = r'"C:\Program Files\QGIS 3.44.3\bin\python-qgis.bat"'

    if not os.path.isdir(base_dir):
        raise FileNotFoundError(f"Base directory not found: {base_dir}")
    if not os.path.isfile(shp_path):
        raise FileNotFoundError(f"Shapefile not found: {shp_path}")

    for folder_name in os.listdir(base_dir):
        folder_path = os.path.join(base_dir, folder_name)
        if not (os.path.isdir(folder_path) and folder_name.endswith(folder_pattern)):
            continue

        raster_folder = os.path.join(folder_path, subdir)
        if not os.path.isdir(raster_folder):
            print(f"[skip] Missing subdir: {raster_folder}")
            continue

        cmd = [
            qgis_python, "3_cropFromOrthomosaic2.py",
            "-sgt", raster_folder,
            "-shp", shp_path,
            "-tpath", folder_path,
        ]
        try:
            subprocess.run(" ".join(cmd), check=True, shell=True)
        except subprocess.CalledProcessError as e:
            print(f"[error] {e} for folder: {folder_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Call 3_cropFromOrthomosaic2.py for subfolders matching a suffix."
    )
    parser.add_argument("base_dir", type=str,
                        help="Path to the base directory containing target folders.")
    parser.add_argument("--folder-pattern", type=str, default="_Swb_Cl",
                        help="Folder name ending to match (default: '_Swb_Cl').")
    parser.add_argument("--subdir", type=str, default="orthos",
                        help="Subfolder containing orthomosaics (default: 'orthos').")
    parser.add_argument("--shp", type=str, required=True,
                        help="Path to the shapefile to use with -shp.")

    args = parser.parse_args()
    main(args.base_dir, args.folder_pattern, args.subdir, args.shp)
