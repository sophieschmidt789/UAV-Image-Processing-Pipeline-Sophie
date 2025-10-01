'''
Created on Jan 8, 2019

updated on May 2, 2024 K.
updated on May 9, 2024 K.

@author: xuwang
'''

import argparse
import fiona
import rasterio
import os 
from rasterio.mask import mask

def crop_from_orthomosaic(src_geoTiff, shape_file, target_path):
    with fiona.open(shape_file) as shapes:
        geoms = [feature["geometry"] for feature in shapes]
        plot_props = [feature["properties"] for feature in shapes]

    if not os.path.exists(target_path):
        os.makedirs(target_path)

    for i in range(len(plot_props)):
        # Use PlotID field directly
        plotIDUpdated = str(plot_props[i].get("PlotID", f"plot_{i+1}"))

        with rasterio.open(src_geoTiff) as src:
            out_image, out_transform = mask(src, [geoms[i]], crop=True)
            out_meta = src.meta.copy()
            out_meta.update({
                "driver": "GTiff",
                "height": out_image.shape[1],
                "width": out_image.shape[2],
                "transform": out_transform
            })
        
        tif_basename = os.path.splitext(os.path.basename(src_geoTiff))[0].split('_')[-1]
        target_folder = os.path.join(target_path, tif_basename + "_by_plot")

        if not os.path.exists(target_folder):
            os.makedirs(target_folder)

        out_tif_path = os.path.join(target_folder, plotIDUpdated + ".tif")
        with rasterio.open(out_tif_path, "w", **out_meta) as dest:
            dest.write(out_image)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-sgt", "--geoTiff", required=True,
                    help="Source GeoTiff image or folder containing GeoTiff images")
    ap.add_argument("-shp", "--shapeFile", required=True,
                    help="Source shapefile")
    ap.add_argument("-tpath", "--targetPath", required=True,
                    help="Target path")

    args = ap.parse_args()
    src_geoTiff = args.geoTiff
    plot_shape = args.shapeFile
    target_path = args.targetPath

    if os.path.isdir(src_geoTiff):
        for file in os.listdir(src_geoTiff):
            if file.endswith(".tif"):
                crop_from_orthomosaic(os.path.join(src_geoTiff, file), plot_shape, target_path)
                if not file.endswith(('ortho.tif', 'render.tif', 'dem.tif')):
                    os.remove(os.path.join(src_geoTiff, file))
    else:
        crop_from_orthomosaic(src_geoTiff, plot_shape, target_path)
        if not src_geoTiff.endswith(('ortho.tif', 'render.tif', 'dem.tif')):
            os.remove(src_geoTiff)
