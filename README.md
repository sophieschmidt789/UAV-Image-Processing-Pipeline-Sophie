# Image Processing Pipeline

> A step‑by‑step pipeline for UAV image processing (preprocessing → analysis → visualization).

> Replace any `<PLACEHOLDER>` with your project specifics as you iterate.

---

## Quickstart
Follow these steps in order.

### 1) Clone this repository

```bash
# HTTPS
git clone <REPO_URL_HTTPS>

cd <REPO_NAME>
```

## Installation
**Pip**
```bash
pip install -r requirements.txt
```

---

## Usage

### original structure
```
<base_dir>/
├─ DATE1
│  │  ├─ ortho.tif
│  │  └─ dem.tif
├─ DATE2
│  │  ├─ ortho.tif
│  │  └─ dem.tif
├─ DATE3
...
```

```
├─ src/
│  ├─ pipeline.py           # entrypoint orchestrating stages
│  ├─ stages/
│  │  ├─ preprocess.py      # e.g., resize/denoise/normalize
│  │  ├─ segment.py         # e.g., threshold/ML/DL
│  │  ├─ features.py        # e.g., morphology/texture/VI
│  │  └─ visualize.py       # plots/overlays/exports
│  ├─ utils/
│  │  └─ io.py              # I/O helpers, logging, timing
│  └─ __init__.py
├─ configs/
│  ├─ minimal.yaml          # tiny sample config for smoke test
│  ├─ default.yaml          # baseline config
│  └─ <experiment>.yaml     # add your custom runs
├─ data/
│  ├─ raw/                  # immutable source data
│  ├─ interim/              # intermediate artifacts
│  └─ processed/            # final outputs for analysis
├─ outputs/                 # figs, tables, reports
├─ notebooks/               # exploration & EDA
├─ tests/                   # unit/integration tests
├─ requirements.txt         # or pyproject.toml
├─ environment.yml          # conda env (name: imgpipe)
├─ .gitignore
└─ README.md
```

### rename all ortho and dem with date suffix
```bash
python rename_ortho_dem.py <base_dir>
```

### put all render, dem, ortho into folder orthos
```yaml
folder-pattern: all subfolders end with "_Swb_Cl"
```

```bash
python mv_render_dem_orthos.py <base_dir> --folder-pattern "*_Swb_Cl*" --suffixes dem.tif ortho.tif --dest orthos
```

### raster calculation
> using pyqgis for raster calculation
```yaml
path to shapefile: shapefile path
```

```bash
# pyqgis
python 1_call_rasterRenderRGB.py <base_dir> --folder-pattern "*_Swb_Cl*"
python 2_call_multiOmRasterCalculation4.py <base_dir> --folder-pattern "*_Swb_Cl*"
python 3_call_cropFromOrthomosaic2.py <base_dir> --folder-pattern "*_Swb_Cl*" --shp <path to shapefile>
```

> optional
### RGB brightness adjusted for preview only
```bash
# using RGB images, brightness adjusted for preview

# Batch: same as your defaults
python adjust_bright.py --batchpath <base_dir> --endswith "*_Swb_Cl*"

# Single folder, slightly less intense brighten
python adjust_bright.py --ipath <base_dir> --alpha 2.2 --beta 10
```

### mask generation
> single folder or batch mode
#### 1) veg
```bash
# Single OSAVI folder → mask
python 4_generate_mask_on_1orbatch.py "/data/OSAVI_by_plot" "/data/masks/OSAVI_mask" --lt 0.6

# Single DEM folder → mask
python 4_generate_mask_on_1orbatch.py "/data/dem_by_plot" "/data/masks/dem_mask"

# Batch: DEM + NDVI across date folders
python 4_generate_mask_on_1orbatch.py --batchpath <base_dir> --vi-subdir OSAVI_by_plot --vi-lt 0.6
```

#### 2) veg smoothed
```bash
python 5_masks_overlapping_batch_veg.py --batchpath <base_dir>
```

#### 3) mulch
```bash
python 6_masks_overlapping_batch_mulch.py --batchpath <base_dir>
```

### structural trait extraction
> height, canopy coverage area, volume.

#### 1)  extract GSD from report
```bash
python 7_0_call_export_report_metashape.py <base_dir>
python 7_0_extract_from_report.py <base_dir>
```

#### 2) mulch height extraction
```bash
python 7_mulch_height_extract.py --batchpath <base_dir> --folder-pattern "*_Swb_Cl*"
```

#### 3) canopy coverage and volume extraction
```bash
python 8_trait_extract_dem.py --batchpath <base_dir> --folder-pattern "*_Swb_Cl*"
```

### spectral trait extraction
> height, canopy coverage area, volume.
```bash
python 9_trait_extract_spectral.py --batchpath <base_dir> --folder-pattern "*_Swb_Cl*"
```

### merge morphological and spectral trait
```bash
python 10_merge_dem_nodem.py --batchpath <base_dir>
```