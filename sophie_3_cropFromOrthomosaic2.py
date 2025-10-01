def crop_from_orthomosaic(src_geoTiff, shape_file, target_path):
    import glob
    import os
    import fiona
    import rasterio
    from rasterio.mask import mask

    # Open shapefile
    with fiona.open(shape_file) as shapes:
        geoms = [feature["geometry"] for feature in shapes]
        plot_props = [feature["properties"] for feature in shapes]

    os.makedirs(target_path, exist_ok=True)

    # Detect PlotID field
    sample_props = plot_props[0] if plot_props else {}
    field_name = next((k for k in sample_props.keys() if 'PlotID' in k), None)
    if field_name is None:
        raise KeyError(f"No 'PlotID' field found. Available fields: {', '.join(sample_props.keys())}")

    # Handle folder or single file
    if os.path.isdir(src_geoTiff):
        src_files = glob.glob(os.path.join(src_geoTiff, "*.tif"))
    else:
        src_files = [src_geoTiff]

    for src_file in src_files:
        for i, props in enumerate(plot_props):
            plotIDUpdated = str(props.get(field_name, f"plot_{i+1}")).replace('"', '')

            with rasterio.open(src_file) as src:
                out_image, out_transform = mask(src, [geoms[i]], crop=True)
                out_meta = src.meta.copy()
                out_meta.update({
                    "driver": "GTiff",
                    "height": out_image.shape[1],
                    "width": out_image.shape[2],
                    "transform": out_transform
                })

            tif_basename = os.path.splitext(os.path.basename(src_file))[0].split('_')[-1]
            target_folder = os.path.join(target_path, tif_basename + "_by_plot")
            os.makedirs(target_folder, exist_ok=True)

            out_file = os.path.join(target_folder, plotIDUpdated + ".tif")
            with rasterio.open(out_file, "w", **out_meta) as dest:
                dest.write(out_image)

            print(f"[ok] Wrote {out_file}")
