import os
import sys
import subprocess
import argparse

def main(base_dir: str, folder_pattern: str, subdir: str):
    for folder_name in os.listdir(base_dir):
        folder_path = os.path.join(base_dir, folder_name)
        if not os.path.isdir(folder_path):
            continue
        if not folder_name.endswith(folder_pattern):
            continue

        orthos_path = os.path.join(folder_path, subdir)
        if not os.path.isdir(orthos_path):
            print(f"[skip] missing subdir: {orthos_path}")
            continue

        # Call the worker script with the same Python interpreter
        cmd = [sys.executable, "2_multiOmRasterCalculation4.py", "-s", orthos_path]
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"[error] {e} in {orthos_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run multi raster calculation for subfolders matching a suffix."
    )
    parser.add_argument("base_dir", type=str,
                        help="Path to the base directory containing target folders.")
    parser.add_argument("--folder-pattern", type=str, default="_Swb_Cl",
                        help="Folder name ending to match (default: '_Swb_Cl').")
    parser.add_argument("--subdir", type=str, default="orthos",
                        help="Subfolder to pass as -s (default: 'orthos').")

    args = parser.parse_args()
    main(args.base_dir, args.folder_pattern, args.subdir)
