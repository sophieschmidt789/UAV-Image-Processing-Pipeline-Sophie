import os
import cv2
import argparse
from pathlib import Path

def adjust_brightness(input_folder: str,
                      subdir: str = 'render_by_plot',
                      alpha: float = 3.0,
                      beta: float = 0.0,
                      ext: str = '.tif',
                      outroot: str | None = None,
                      keep_rgba: bool = False):
    input_folder = Path(input_folder)
    date_component = input_folder.name.split('_')[0]
    out_base = Path(outroot) if outroot else (input_folder.parent / "rgb_adjust_bright" / date_component)
    out_base.mkdir(parents=True, exist_ok=True)

    for root, _, files in os.walk(input_folder):
        if Path(root).name.endswith(subdir):
            for file in files:
                if file.lower().endswith(ext.lower()):
                    in_p = Path(root) / file
                    out_p = out_base / file

                    img = cv2.imread(in_p.as_posix(), cv2.IMREAD_UNCHANGED)
                    if img is None:
                        print(f"[skip] unreadable: {in_p}")
                        continue

                    # keep your original behavior: strip alpha unless keep_rgba=True
                    if img.ndim == 3 and img.shape[2] >= 3:
                        if keep_rgba and img.shape[2] == 4:
                            rgb = img  # RGBA
                        else:
                            rgb = img[:, :, :3]  # RGB
                    else:
                        rgb = img  # grayscale or unexpected shape -> pass through

                    # your original brighten method (convertScaleAbs)
                    # alpha=contrast/gain, beta=brightness offset
                    bright = cv2.convertScaleAbs(rgb, alpha=alpha, beta=beta)
                    cv2.imwrite(out_p.as_posix(), bright)

    print(f"[done] rgb render-by-plot brightness adjustment → {out_base}")

def adjust_brightness_4_batch(batch_folder: str,
                              endswith: str = '_Swb_Cl',
                              **kwargs):
    moved = 0
    for folder in os.listdir(batch_folder):
        input_folder = os.path.join(batch_folder, folder)
        if os.path.isdir(input_folder) and input_folder.endswith(endswith):
            adjust_brightness(input_folder, **kwargs)
            moved += 1
    if moved == 0:
        print(f"[warn] no folder ended with '{endswith}' under {batch_folder}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="adjust brightness for rgb images (flexible flags, same logic).")
    ap.add_argument("--ipath", type=str, default=None, help="Path to one date folder.")
    ap.add_argument("--batchpath", type=str, default=None, help="Path containing multiple date folders.")
    ap.add_argument("--endswith", type=str, default="_Swb_Cl", help="Batch: folder name must end with this suffix.")
    ap.add_argument("--subdir", type=str, default="render_by_plot", help="Subfolder name to search in.")
    ap.add_argument("--alpha", type=float, default=3.0, help="Gain (cv2.convertScaleAbs alpha).")
    ap.add_argument("--beta", type=float, default=0.0, help="Bias/offset (cv2.convertScaleAbs beta).")
    ap.add_argument("--ext", type=str, default=".tif", help="Image extension to match (case-insensitive).")
    ap.add_argument("--outroot", type=str, default=None, help="Optional output root dir; default=../rgb_adjust_bright/<date>.")
    ap.add_argument("--keep-rgba", action="store_true", help="Keep 4th channel if present (don’t drop alpha).")
    args = ap.parse_args()

    if args.batchpath:
        adjust_brightness_4_batch(
            args.batchpath,
            endswith=args.endswith,
            subdir=args.subdir,
            alpha=args.alpha,
            beta=args.beta,
            ext=args.ext,
            outroot=args.outroot,
            keep_rgba=args.keep_rgba
        )
    else:
        if not args.ipath:
            raise SystemExit("Provide --ipath or --batchpath")
        adjust_brightness(
            args.ipath,
            subdir=args.subdir,
            alpha=args.alpha,
            beta=args.beta,
            ext=args.ext,
            outroot=args.outroot,
            keep_rgba=args.keep_rgba
        )
