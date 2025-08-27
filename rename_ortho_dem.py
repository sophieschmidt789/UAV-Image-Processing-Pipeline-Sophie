import os
import argparse

def rename_files_in_subfolders(root_dir):
    # Iterate through each subfolder in the root directory
    for subdir, dirs, files in os.walk(root_dir):
        for file in files:
            # Check if the file is ortho.tif or dem.tif
            if file == 'ortho.tif' or file == 'dem.tif':
                folder_name = os.path.basename(subdir)
                new_filename = f"{folder_name}_{file}"
                old_path = os.path.join(subdir, file)
                new_path = os.path.join(subdir, new_filename)

                # Rename the file
                os.rename(old_path, new_path)
                print(f"Renamed: {old_path} -> {new_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rename ortho.tif and dem.tif files by prefixing with their folder name.")
    parser.add_argument("root_dir", help="Path to the root directory containing subfolders")
    args = parser.parse_args()

    rename_files_in_subfolders(args.root_dir)
