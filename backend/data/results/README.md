# Results Directory

This directory contains the generated Excel files from the Lululemon scraper.

## File Naming Convention

Excel files are generated with timestamps:
```
all_products_YYYYMMDD_HHMMSS.xlsx
```

Example:
```
all_products_20251206_183045.xlsx
```

## Location

All Excel reports are automatically saved here by the `extract_to_excel.py` script.

## Access

The frontend application serves these files for download via the `/api/download_excel` endpoint.

## Cleanup

You may periodically delete old Excel files to save disk space. The application will always use the most recent file by timestamp.
