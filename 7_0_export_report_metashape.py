"""
Batch Metashape report exporter
-------------------------------
Usage:
    metashape.exe -r export_report_metashape.py --batchpath D:\...\S2
"""

import os
import argparse
import Metashape

def export_report_for_folder(folder):
    # find .psx file in folder
    psx_files = [f for f in os.listdir(folder) if f.lower().endswith(".psx")]
    if not psx_files:
        print(f"[SKIP] No .psx project in {folder}")
        return

    psx_path = os.path.join(folder, psx_files[0])
    doc = Metashape.app.document
    if not doc.open(psx_path):
        print(f"[ERR] Failed to open {psx_path}")
        return

    # export report
    report_folder = os.path.join(os.path.dirname(folder), "metashape_report")
    os.makedirs(report_folder, exist_ok=True)
    report_path = os.path.join(report_folder, os.path.basename(folder) + ".pdf")

    try:
        doc.chunk.exportReport(path=report_path)
        print(f"[OK] Report saved: {report_path}")
    except Exception as e:
        print(f"[ERR] Could not export report for {folder}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Export PDF reports for all Metashape projects in a batch folder.")
    parser.add_argument("--batchpath", required=True, help="Folder containing multiple project subfolders")
    args = parser.parse_args()

    batch_root = os.path.abspath(args.batchpath)
    for name in sorted(os.listdir(batch_root)):
        folder = os.path.join(batch_root, name)
        if os.path.isdir(folder):
            export_report_for_folder(folder)

if __name__ == "__main__":
    main()
