import os
import subprocess
import argparse

def main(base_dir: str, folder_pattern: str, suffix: str):
    # Path to QGIS Python launcher
    qgis_python = r"C:\Program Files\QGIS 3.44.3\bin\python-qgis.bat"
    
    # Full path to raster render script
    script_path = os.path.join(os.path.dirname(__file__), "1_rasterRenderRGB.py")

    # Iterate over folders
    for folder_name in os.listdir(base_dir):
        folder_path = os.path.join(base_dir, folder_name)
        if os.path.isdir(folder_path) and folder_name.endswith(folder_pattern):
            orthos_folder = os.path.join(folder_path, 'orthos')
            if os.path.isdir(orthos_folder):
                ortho_files = [f for f in os.listdir(orthos_folder) if f.endswith(suffix)]
                if ortho_files:
                    ortho_file_path = os.path.join(orthos_folder, ortho_files[0])
                    
                    # Build command using QGIS Python
                    command = f"\"{qgis_python}\" \"{script_path}\" -s \"{ortho_file_path}\""
                    print("Running:", command)  # Debug print
                    subprocess.run(command, shell=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run raster render command for folders with a specific ending"
    )
    parser.add_argument("base_dir", type=str,
                        help="Path to the base directory containing target folders")
    parser.add_argument("--folder-pattern", type=str, default="_Swb_Cl",
                        help="Folder name ending to match (default: '_Swb_Cl')")
    parser.add_argument("--suffix", type=str, default="ortho.tif",
                        help="File suffix to match inside orthos/ (default: 'ortho.tif')")

    args = parser.parse_args()
    main(args.base_dir, args.folder_pattern, args.suffix)
