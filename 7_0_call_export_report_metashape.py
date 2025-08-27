import os
import subprocess
import argparse

def main(base_dir):
    for folder_name in os.listdir(base_dir):
        folder_path = os.path.join(base_dir, folder_name)
        
        project = folder_path+"\\ortho_dem_process.psx"
        if os.path.exists(project):
            command = f"metashape.exe -r 7_0_export_report_metashape.py -wp {folder_path}"
            
            subprocess.run(command, shell=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run export Ground resolution mm/pix for all')
    parser.add_argument('base_dir', type=str, help='Path to the base directory')

    args = parser.parse_args()

    main(args.base_dir)
