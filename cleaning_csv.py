import csv


def read_csv_first_9_columns_filtered(file_path):
    # handles BOM (\ufeff) if present.
    
    remove_columns = "<based on your csv>"
    filtered_rows = []

    with open(file_path, newline="", encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile)
        # Strip BOM from first column name if exists
        reader.fieldnames = [name.replace("\ufeff", "") for name in reader.fieldnames]
        # Keep only first 9 columns
        fieldnames = reader.fieldnames[:9]
        # Remove unwanted columns
        fieldnames = [f for f in fieldnames if f not in remove_columns]

        for row in reader:
            filtered_row = {k: row[k] for k in fieldnames}
            filtered_rows.append(filtered_row)

    return filtered_rows
