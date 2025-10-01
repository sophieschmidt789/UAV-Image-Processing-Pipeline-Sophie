import os
import fiona
import rasterio
from rasterio.mask import mask
import argparse

def crop_from_orthomosaic(src_geoTiff, shape_file, target_path):
    # Open shapefile
    with fiona.open(shape_file) as shapes:
        geoms = [feature["geometry"] for feature in shapes]
        plot_props = [feature["properties"] for feature in shapes]

    # Ensure target path exists
    os.makedirs(target_path, exist_ok=True)

    # Auto-detect PlotID field
    sample_props = plot_props[0] if plot_props else {}
    field_name = next((k for k in sample_props.keys() if 'PlotID' in k), None)
    if field_name is None:
        raise KeyError("No 'PlotID' field found in shapefile properties. Available fields: "
                       + ", ".join(sample_props.keys()))

    # Loop over all features
    for i, props in enumerate(plot_props):
        plotIDUpdated = str(props.get(field_name, f"plot_{i+1}")).replace('"', '')

        # Read and mask raster
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
        os.makedirs(target_folder, exist_ok=True)

        # Write masked raster
        out_file = os.path.join(target_folder, plotIDUpdated + ".tif")
        with rasterio.open(out_file, "w", **out_meta) as dest:
            dest.write(out_image)

        print(f"[ok] Wrote {out_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crop orthomosaic using shapefile")
    parser.add_argument("-sgt", "--source", required=True, help="Path to source GeoTIFF or folder")
    parser.add_argument("-shp", "--shapefile", required=True, help="Shapefile path")
    parser.add_argument("-tpath", "--target", required=True, help="Target folder path")
    args = parser.parse_args()

    crop_from_orthomosaic(args.source, args.shapefile, args.target)
