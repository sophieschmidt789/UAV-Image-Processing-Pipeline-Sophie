# suffix 'AS_S2'
# python 9_trait_extract_nodem_rgb_test.py --batchpath E:\AS\low_altitude_RGB\low_altitude_RGB\veg_preview
import os
import cv2
import numpy as np
import pandas as pd
import skimage
from skimage import io, img_as_float
import imagecodecs
import matplotlib.pyplot as plt
from pathlib import Path
from skimage.feature import canny
from skimage.color import gray2rgb
import argparse

def process_image_nodem(nodem_image_path, output_data_nodem, root):
    date_component = os.path.basename(root)
    imarray_nodem = cv2.imread(nodem_image_path)
    imarray_nodem = cv2.cvtColor(imarray_nodem, cv2.COLOR_BGR2RGB)
    
    image = imarray_nodem.astype(np.float32)

    non_black_mask = np.any(image != 0, axis=-1)

    # Apply the mask to set black pixels to NaN
    image_masked = image.copy()
    image_masked[~non_black_mask] = np.nan

    R, G, B = image_masked[:, :, 0], image_masked[:, :, 1], image_masked[:, :, 2]

    epsilon = 1e-6

    # Compute vegetation indices @ https://www.sciencedirect.com/science/article/pii/S0168169924009566#s0080
    indices = {
        "Kawashima Index": (R - B) / (R + B + epsilon),
        "Green-Red Ratio Index": R / (G + epsilon),
        "VARI": (G - R) / (G + R - B + epsilon),  # Visible Atmospherically Resistant Index
        "CIVE": 0.441 * R - 0.811 * G + 0.385 * B + 18.78745,  # Color Index of Vegetation Extraction
        "NGRDI": (G - R) / (G + R + epsilon),  # Normalized Green-Red Difference Index
        "Excess Red Vegetation Index": 1.4 * R - G,
        "ExG-ExR": (3 * G - 2.4 * R - B),  # Excess Green minus Excess Red Index
        "GLI": (2 * G - R - B) / (2 * G + R + B + epsilon),  # Green Leaf Index
        "PCAI": 0.994 * np.abs(R - B) + 0.961 * np.abs(G - B) + 0.914 * np.abs(G - R),  # PCA Index
        "MGBVI": (G**2 - R**2) / (G**2 + R**2 + epsilon),  # Modified Green-Blue Vegetation Index
        "RGBVI": (G**2 - B * R) / (G**2 + B * R + epsilon),  # Red Green Blue Vegetation Index
        "NDYI": (G - B) / (G + B + epsilon),  # Normalized Difference Yellowness Index
        "CFI": G - R,  # Color Feature Index
        "Normalized Red": R / (R + G + B + epsilon),
        "Normalized Green": G / (R + G + B + epsilon),
        "TCVI": (1.4 * (2 * R - 2 * B)) / (2 * R - G - 2 * B + 255 * 0.4 + epsilon),  # True Color Vegetation Index
    }
    
    # # Create a nested dictionary for each image and date if it doesn't exist
    # if (image_id, date_component) not in output_data_nodem:
        # output_data_nodem[(image_id, date)] = {'Date': date_component, 'Image ID': image_id}

    # for name, index_values in indices.items():
        # flattened_values = index_values.flatten()
        # valid_values = np.where((flattened_values <= -1e10) | (flattened_values >= 1e10) | (flattened_values == 0), np.nan, flattened_values)
        # valid_values = valid_values[~np.isnan(valid_values)]

        # if len(valid_values) > 0:
            # lower_bound, upper_bound = np.percentile(valid_values, [5, 95])
            # valid_values = valid_values[(valid_values >= lower_bound) & (valid_values <= upper_bound)]
            # output_data_nodem[(image_id, date)][f"{name}_Avg"] = np.nanmean(valid_values)
            # output_data_nodem[(image_id, date)][f"{name}_StdDev"] = np.nanstd(valid_values)
        # else:
            # output_data_nodem[(image_id, date)][f"{name}_Avg"] = np.nan
            # output_data_nodem[(image_id, date)][f"{name}_StdDev"] = np.nan
    
    nodem_data = {'Date': date_component, 'Image ID': os.path.basename(nodem_image_path)}

    for name, index_values in indices.items():
        flattened_values = index_values.flatten()
        valid_values = np.where((flattened_values <= -1e10) | (flattened_values >= 1e10) | (flattened_values == 0), np.nan, flattened_values)
        valid_values = valid_values[~np.isnan(valid_values)]

        if len(valid_values) > 0:
            lower_bound, upper_bound = np.percentile(valid_values, [5, 95])
            valid_values = valid_values[(valid_values >= lower_bound) & (valid_values <= upper_bound)]
            nodem_data[f"{name}_Avg"] = np.nanmean(valid_values)
            nodem_data[f"{name}_StdDev"] = np.nanstd(valid_values)
        else:
            nodem_data[f"{name}_Avg"] = np.nan
            nodem_data[f"{name}_StdDev"] = np.nan

    output_data_nodem.append(nodem_data) # Append the dictionary to the list
    
    
    # for name, index_values in indices.items():
        # flattened_values = index_values.flatten()
        # valid_values = np.where((flattened_values <= -1e10) | (flattened_values >= 1e10) | (flattened_values == 0), np.nan, flattened_values)
        # valid_values = valid_values[~np.isnan(valid_values)]

        # if len(valid_values) > 0:
            # lower_bound, upper_bound = np.percentile(valid_values, [5, 95])
            # valid_values = valid_values[(valid_values >= lower_bound) & (valid_values <= upper_bound)]
            # nodem_data = {
                # 'Date': date_component,
                # 'Image ID': os.path.basename(nodem_image_path),
                # f"{name}_Avg": np.nanmean(valid_values),
                # f"{name}_StdDev": np.nanstd(valid_values)
            # }
        # else:
            # nodem_data = {
                # 'Date': date_component,
                # 'Image ID': os.path.basename(nodem_image_path),
                # f"{name}_Avg": np.nan,
                # f"{name}_StdDev": np.nan
            # }
 
    # output_dict_nodem.setdefault((os.path.basename(nodem_image_path), nodem_data['Date']), {}).update(nodem_data)

def trait_extract_nodem(input_folder):
    output_folder = os.path.join(os.path.dirname(os.path.dirname(input_folder)), "nodem_trait_RGB")
    os.makedirs(output_folder, exist_ok=True)

    # Create an empty dictionary to store data for each date
    output_data_nodem = []

    # Iterate through all subfolders and process images
    for root, dirs, files in os.walk(input_folder):
        # date_component = os.path.basename(input_folder).split('_')[0]
        if os.path.basename(root).isdigit() and len(os.path.basename(root)) == 8:
            for file in files:
                if file.endswith('.JPG'):
                    nodem_image_path = os.path.join(root, file)
                    # image_name = os.path.basename(nodem_image_path)
                    process_image_nodem(nodem_image_path, output_data_nodem, root)

    df = pd.DataFrame(output_data_nodem)

    # Save the data for each date to a separate Excel file with dir structure
    for date, data_list in df.groupby('Date'):
        # Create a DataFrame from the list of dictionaries
        date_df = data_list.drop(columns=['Date'])
        parent_dir = date.replace('/', '_')  # Replace '/' with '_'

        # Save the DataFrame to an Excel file within the date-specific folder with the date as the file name
        output_excel_path = os.path.join(output_folder, f'{date}.xlsx')
        date_df.to_excel(output_excel_path, index=False)
        
    print("non-dem All data saved in separate Excel files by date and parent directory.")
    # Flatten output_data_nodem into a list of dictionaries
    # data_list = []
    # for (image_id, date), data in output_data_nodem.items():
        # data_list.append(data)

    # df = pd.DataFrame(data_list)

    # for date, data_list in df.groupby('Date'):
        # date_df = data_list.drop(columns=['Date'])
        # parent_dir = date.replace('/', '_')

        # output_excel_path = os.path.join(output_folder, f'{date}.xlsx')
        # date_df.to_excel(output_excel_path, index=False)

    # print("non-dem All data saved in separate Excel files by date.")
def trait_extract_nodem_4_batch(batch_folder):
    for folder in os.listdir(batch_folder):
        input_folder = os.path.join(batch_folder, folder)
        trait_extract_nodem(input_folder)
            
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="nodem extraction from images with masks.")
    parser.add_argument("--ipath", type=str, default=None, help="Path to folder on 1 date.")
    parser.add_argument("--batchpath", type=str, default=None, help="Path to the folder containing multidates data")

    args = parser.parse_args()

    if args.batchpath is not None:
        trait_extract_nodem_4_batch(args.batchpath)
    else:
        trait_extract_nodem(args.ipath)

