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
    """Export PDF report for the first .psx project found in the folder."""
    psx_files = [f for f in os.listdir(folder) if f.lower().endswith(".psx")]
    if not psx_files:
        print(f"[SKIP] No .psx project in {folder}")
        return

    psx_path = os.path.join(folder, psx_files[0])
    doc = Metashape.Document()
    try:
        doc.open(psx_path)
    except Exception as e:
        print(f"[ERR] Failed to open {psx_path}: {e}")
        return

    report_folder = os.path.join(os.path.dirname(folder), "metashape_report")
    os.makedirs(report_folder, exist_ok=True)
    report_path = os.path.join(report_folder, os.path.basename(folder) + ".pdf")

    try:
        # Export report for all chunks in the project
        for i, chunk in enumerate(doc.chunks):
            chunk_report_path = report_path
            if len(doc.chunks) > 1:
                # Append chunk index if multiple chunks exist
                chunk_report_path = os.path.join(report_folder, f"{os.path.basename(folder)}_chunk{i+1}.pdf")
            chunk.exportReport(path=chunk_report_path)
            print(f"[OK] Report saved: {chunk_report_path}")
    except Exception as e:
        print(f"[ERR] Could not export report for {folder}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Export PDF reports for all Metashape projects in a batch folder.")
    parser.add_argument("--batchpath", required=True, help="Folder containing multiple project subfolders")
    args = parser.parse_args()

    batch_root = os.path.abspath(args.batchpath)
    if not os.path.exists(batch_root):
        print(f"[ERR] Batch path does not exist: {batch_root}")
        return

    for name in sorted(os.listdir(batch_root)):
        folder = os.path.join(batch_root, name)
        if os.path.isdir(folder):
            export_report_for_folder(folder)

if __name__ == "__main__":
    main()
