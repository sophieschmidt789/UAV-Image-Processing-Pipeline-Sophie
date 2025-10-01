import os
import fiona
import rasterio
from rasterio.mask import mask

def crop_from_orthomosaic(src_geoTiff, shape_file, target_path):
    # Open shapefile
    with fiona.open(shape_file) as shapes:
        geoms = [feature["geometry"] for feature in shapes]
        plot_props = [feature["properties"] for feature in shapes]

    # Ensure target path exists
    if not os.path.exists(target_path):
        os.makedirs(target_path)

    # Loop over all features
    for i in range(len(plot_props)):
        # Use the exact field name as Fiona sees it
        field_name = '"PlotID"'  # Fiona sees the quotes in your shapefile
        plotIDUpdated = str(plot_props[i].get(field_name, f"plot_{i+1}"))
        plotIDUpdated = plotIDUpdated.replace('"', '')  # remove quotes

        # Read and mask the raster
        with rasterio.open(src_geoTiff) as src:
            out_image, out_transform = mask(src, [geoms[i]], crop=True)
            out_meta = src.meta.copy()
            out_meta.update({
                "driver": "GTiff",
                "height": out_image.shape[1],
                "width": out_image.shape[2],
                "transform": out_transform
            })

        # Create folder based on raster name
        tif_basename = os.path.splitext(os.path.basename(src_geoTiff))[0].split('_')[-1]
        target_folder = os.path.join(target_path, tif_basename + "_by_plot")
        if not os.path.exists(target_folder):
            os.makedirs(target_folder)

        # Write masked raster
        out_file = os.path.join(target_folder, plotIDUpdated +
