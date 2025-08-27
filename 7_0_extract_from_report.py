import os
import re
import PyPDF2
import openpyxl
import argparse

def extract_pdf_data(pdf_path):
    """Extracts ground resolution and flight altitude from a PDF."""
    try:
        text = ""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                if page.extract_text():
                    text += page.extract_text()

        # Regular expressions to find GSD and Flight Altitude
        ground_resolution_match = re.search(r"Ground resolution\s*:\s*([\d.]+)\s*mm/pix", text, re.IGNORECASE)
        flight_altitude_match = re.search(r"Flying altitude\s*:\s*([\d.]+)\s*m", text, re.IGNORECASE)

        # Extract and convert values
        ground_resolution = float(ground_resolution_match.group(1)) if ground_resolution_match else None
        flight_altitude = float(flight_altitude_match.group(1)) if flight_altitude_match else None

        return ground_resolution, flight_altitude

    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
        return None, None

def main(base_dir):
    """Reads multiple PDF reports and writes extracted data to an Excel file."""
    
    report_folder = os.path.join(base_dir, "metashape_report")
    excel_filename = os.path.join(report_folder, "gsd_4_all.xlsx")

    # Ensure the report folder exists
    if not os.path.exists(report_folder):
        print(f"Error: Report folder '{report_folder}' not found!")
        return

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(["filename", "GSD(mm/pix)", "flight_altitude(m)"])  # Header row

    for filename in os.listdir(report_folder):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(report_folder, filename)
            ground_resolution, flight_altitude = extract_pdf_data(pdf_path)

            # Append results or mark as "n/a" if extraction failed
            if ground_resolution is not None and flight_altitude is not None:
                sheet.append([filename.split('_')[0], ground_resolution, flight_altitude])
            else:
                print(f"Warning: Could not extract data from {filename}")
                sheet.append([filename, "n/a", "n/a"])

    # Save to Excel
    workbook.save(excel_filename)
    print(f"Data saved to {excel_filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract GSD & Flight Altitude from Metashape reports')
    parser.add_argument('base_dir', type=str, help='Path to the base directory containing "metashape_report"')

    args = parser.parse_args()
    main(args.base_dir)

