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
│  │  ├─ ortho_dem_process.psx
│  │  ├─ ortho.tif
│  │  └─ dem.tif
├─ DATE2
│  │  ├─ ortho_dem_process.psx
│  │  ├─ ortho.tif
│  │  └─ dem.tif
├─ DATE3
...
```

### Extract GSD from Metashape report
Generates **Agisoft Metashape** project reports and parses the **GSD (cm/px)** for each orthomosaic.  
The extracted GSD is then used as the **pixel size** when computing **canopy coverage area** and **volume**.

```bash
python 0_call_export_report_metashape.py <base_dir>
python 0_extract_from_report.py <base_dir>
```
**Outputs**
- A table mapping `DATE / scene → GSD` (e.g., `gsd_summary.csv`).
- Per-row cached GSD values for downstream scripts.

---

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

---

## Raster calculation
> Using **pyqgis.cmd** for raster math and cropping.

---

**About the shapefile (`--shp`)**  
Use a polygon (or circle) layer that outlines **one plot/plant per feature**—a *plot/plant ROI shapefile*. Include an ID field (e.g., `plotID` or `plantID`). These ROIs can include vegetation and background; vegetation-only refinement happens later in **mask generation**.

---
### Scripts

#### 1) `1_call_rasterRenderRGB.py`
- **What it does:** Creates an RGB render from the built orthomosaic (maps bands to R/G/B; writes a view-ready RGB GeoTIFF).
- **Input:** Orthomosaic files inside folders matching `--folder-pattern`.
- **Output:** One RGB GeoTIFF per input orthomosaic (same extent/resolution).
- **Why:** QC and downstream visualization.

#### 2) `2_call_multiOmRasterCalculation4.py`
- **What it does:** Computes **52 vegetation indices (VIs)** and writes **one raster per VI** (same size/geo as the ortho).  
  - You can **mute/disable** VIs you don’t need in `2_multiOmRasterCalculation4.py`.
  - **Band order assumption:** **Blue / Green / Red / Red-Edge / NIR** (B, G, R, RE, NIR).  
    **Verify this order for your data before running.**
- **Input:** Multiband orthomosaics (B/G/R/RE/NIR).
- **Output:** Per-VI GeoTIFFs (e.g., NDVI, OSAVI, etc.).
- **Why:** Standardized VI layers for masking and trait extraction.

#### 3) `3_call_cropFromOrthomosaic2.py`
- **What it does:** Crops orthos (and/or derived rasters) **per ROI feature** using the plot/plant shapefile.  
  - Each crop corresponds to a single plot/plant and carries its `plotID/plantID`.  
  - **Saves each cropped individual into a separate folder** for clean organization.  
  - Crops may still include non-veg pixels; you’ll refine to veg-only in **mask generation**.
- **Input:** Orthomosaics (and VIs, if configured), ROI shapefile (one feature per plot/plant + ID field).
- **Output:** Per-plot/plant cropped rasters, named/attributed by the ID.
- **Why:** Moves from field-scale to ID-linked plot/plant tiles.

---
### Commands
```bash
# pyqgis
python 1_call_rasterRenderRGB.py <base_dir> --folder-pattern "*_Swb_Cl*"
python 2_call_multiOmRasterCalculation4.py <base_dir> --folder-pattern "*_Swb_Cl*"
python 3_call_cropFromOrthomosaic2.py <base_dir> --folder-pattern "*_Swb_Cl*" --shp <path_to_roi_shapefile>
```

---
### updated structure (after raster calculation & per-ROI cropping)
```
<base_dir>/
├─ DATE1/
│  ├─ orthos/
│  │  ├─ ortho.tif
│  │  ├─ dem.tif
│  │  └─ rgb_render.tif
│  ├─ ortho_by_plot/    # each ROI saved to its own folder
│  │  ├─ plot_001.tif
│  │  ├─ plot_002.tif
│  │  └─ ...
│  ├─ dem_by_plot
│  ├─ rgb_by_plot
│  └─ vi_by_plot
├─ DATE2/
│  └─ (same structure as DATE1)
├─ DATE3/
│  └─ ...
└─ ...
```

---
### RGB brightness adjustment (optional, for preview only)
Sometimes the generated RGB images from orthomosaics look **too dark** for quick viewing.
This step simply brightens them **for visualization purposes only**. It does not affect analysis or trait extraction.

**How it works**

- Applies a linear transform to each pixel:
**output = alpha × input + beta**
  - alpha = contrast/scale factor (higher = stronger contrast, image looks sharper but can clip).
  - beta = brightness shift (positive = brighter, negative = darker).
- Adjust values to make previews visually clearer.

### Commands
```bash
# Batch mode: apply default brightness adjustment to all matching folders
python adjust_bright.py --batchpath <base_dir> --endswith "*_Swb_Cl*"

# Single folder: apply a lighter adjustment
python adjust_bright.py --ipath <base_dir> --alpha 2.2 --beta 10
```
**Note:** These adjusted images are just for **preview**. For actual processing (masks, traits), always use the original RGB/orthos.

---

## Mask Generation

> **Skip this section** if you already have a vegetation shapefile/mask and don’t need refinement.  
> Use it if you want to (re)generate or improve masks.
---
### 1) Vegetation masks (flexible VI choice)
You can choose any vegetation index (VI) you prefer (e.g., **OSAVI**, **NDVI**, **HSV-derived** from RGB).  
The script thresholds a VI (and/or DEM) to produce a **binary vegetation mask** per plot/plant.

- **Tip:** Adjust `--vi-subdir` to point to the VI folder you’re using.  
- Tune `--vi-lt` / `--vi-gt` thresholds depending on the index and your dataset.

```bash
# Single OSAVI folder → veg mask (example threshold)
python 4_generate_mask_on_1orbatch.py "/data/OSAVI_by_plot" "/data/masks/OSAVI_mask" --lt 0.6

# Single DEM folder → veg mask (height-based, if desired)
python 4_generate_mask_on_1orbatch.py "/data/dem_by_plot" "/data/masks/dem_mask"

# Batch: use OSAVI across date folders (swap OSAVI_by_plot for NDVI_by_plot, HSV_by_plot, etc.)
python 4_generate_mask_on_1orbatch.py --batchpath <base_dir> --vi-subdir OSAVI_by_plot --vi-lt 0.6
```

---

### 2) Vegetation mask smoothing (refinement)
This step merges and cleans overlapping veg masks across dates to reduce noise and fill small holes.

> **Note:** The DEM-assisted refinement in this stage is to be updated.

```bash
python 5_masks_overlapping_batch_veg.py --batchpath <base_dir>
```

---

### 3) Mulch/background masks
Generates masks for the **mulch/bedding** (non-vegetation background).  
These are useful for explicitly separating canopy from bed during trait extraction and visualization.

```bash
python 6_masks_overlapping_batch_mulch.py --batchpath <base_dir>
```

---

### Outputs
- Per-plot/plant binary masks (veg and mulch), aligned to the cropped rasters.  
- Use **masks_overlapping** for canopy coverage/volume.  
- Use **masks_overlapping_mulch** for bed height and background separation.

---
### updated structure (after raster calculation & per-ROI cropping)
```
<base_dir>/
├─ DATE1/
│  ├─ orthos/
│  ├─ ortho_by_plot
│  ├─ dem_by_plot
│  ├─ rgb_by_plot
│  ├─ vi_by_plot
│  ├─ masks/
│  │  ├─ OSAVI_mask
│  │  │  ├─ plot_001.tif
│  │  │  ├─ plot_002.tif
│  │  │  ├─ ...
│  │  ├─ dem_mask
│  │  │  ├─ plot_001.tif
│  │  │  ├─ plot_002.tif
│  │  │  ├─ ...
│  │  └─ ...
│  ├─ masks_overlapping
│  │  ├─ plot_001.tif
│  │  ├─ plot_002.tif
│  │  └─ ...
│  └─ masks_overlapping_mulch
│     ├─ plot_001.tif
│     ├─ plot_002.tif
│     └─ ...
├─ DATE2/
│  └─ (same structure as DATE1)
├─ DATE3/
│  └─ ...
└─ ...
```

---
## Structural Trait Extraction
> Height, canopy coverage area, and canopy volume derived from DEM and masks.

### 1) Mulch (bed) height extraction (baseline DTM)
Derives a **DTM of the mulch surface** to serve as the height baseline.  
> This is **DTM**, not DSM. Plant height is later computed as:  
**plant_height = plant_top_5%_mean_DSM − mulch_DTM**.

```bash
python 7_mulch_height_extract.py --batchpath <base_dir> --folder-pattern "*_Swb_Cl*"
```
**What it does**
- Uses mulch/background masks to model the **mulch surface** per plot.
- Fits/smooths a surface to estimate the **baseline elevation** (DTM) for each plot.
- Exports per‑plot DTM stats for later height/volume calculations.

**Outputs**
- Per‑plot mulch DTM rasters (optional) and a CSV of baseline stats.

---

### 2) Canopy coverage and volume extraction
Computes **canopy coverage (area)** and **canopy volume** per plot using the veg masks, the DEM, and the GSD.

```bash
python 8_trait_extract_dem.py --batchpath <base_dir> --folder-pattern "*_Swb_Cl*"
```
**What it does**
- **Coverage (area):** counts vegetation‑mask pixels × `pixel_area (from GSD)`.
- **Height:** estimates **plant height = DSM − mulch_DTM** within veg mask.
- **Volume:** approximates canopy volume by integrating height over area.

**Outputs**
- Per‑plot/plant coverage (m²), height (m), and volume (m³).

---

## Spectral Trait Extraction (spectral info)
Extracts **spectral summaries** per plot (from bands and/or VIs) within the veg mask.  
Reported values include **mean** and **standard deviation** (and can be extended if needed).

```bash
python 9_trait_extract_spectral.py --batchpath <base_dir> --folder-pattern "*_Swb_Cl*"
```
**Outputs**
- Per‑plot/plant mean & stddev for selected spectral layers (e.g., bands, NDVI/OSAVI, etc.).

---

## Merge Morphological and Spectral Traits
Joins the structural (coverage/height/volume) and spectral summaries into one table for analysis.

```bash
python 10_merge_dem_nodem.py --batchpath <base_dir>
```
**Outputs**
- A merged CSV keyed by `date / plotid` (and other IDs you provide), ready for modeling and visualization.

### updated structure (after raster calculation & per-ROI cropping)
```
<base_dir>/
├─ dem_trait
├─ nodem_trait
├─ merged_trait
├─ DATE1
├─ DATE2/
│  └─ (same structure as DATE1)
├─ DATE3/
│  └─ ...
└─ ...
```
