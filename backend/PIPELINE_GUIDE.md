# Lululemon Wholesale Scraper - Pipeline Guide

## 📋 Overview

Complete pipeline to scrape Lululemon wholesale product data and generate Excel reports with images.

## 🔄 Pipeline Flow

```
run_pipeline.py
    ↓
1. login_and_save_cookies.py
    ├─ Logs into wholesale.lululemon.com
    ├─ Saves cookies to: data/cookie/cookie.json
    └─ Updates product counts in: data/links.csv
    ↓
2. extract_product_links.py
    ├─ Reads category URLs from: data/links.csv
    ├─ Downloads category pages (women, men, accessories, supplies)
    ├─ Extracts all product links
    └─ Saves to: data/categories/{category}.csv
    ↓
3. download_by_category.py
    ├─ Reads product URLs from: data/categories/*.csv
    ├─ Downloads fully rendered HTML pages (5 concurrent)
    ├─ Uses Playwright with cookies for authentication
    └─ Saves to: data/html/{category}/{product_id}.html
    ↓
4. extract_to_excel.py
    ├─ Reads HTML files from: data/html/{category}/*.html
    ├─ Extracts product data using __NEXT_DATA__ + DOM
    ├─ Processes inventory, swatches, images
    └─ Saves to: data/results/all_products_{timestamp}.xlsx
```

## 📁 Folder Structure

```
backend/
├── run_pipeline.py              # Main orchestrator
├── login_and_save_cookies.py    # Step 1: Authentication
├── extract_product_links.py     # Step 2: Get product URLs
├── download_by_category.py      # Step 3: Download HTML pages
├── extract_to_excel.py          # Step 4: Generate Excel
├── db_credentials.py            # Database credential helper
├── data/
│   ├── cookie/
│   │   └── cookie.json          # Saved authentication cookies
│   ├── links.csv                # Category URLs with product counts
│   ├── categories/              # Product URLs by category
│   │   ├── women.csv            # ~265 products
│   │   ├── men.csv              # ~169 products
│   │   ├── accessories.csv      # ~85 products
│   │   └── supplies.csv         # ~9 products
│   ├── html/                    # Downloaded HTML pages
│   │   ├── women/               # 265 HTML files
│   │   ├── men/                 # 169 HTML files
│   │   ├── accessories/         # 85 HTML files
│   │   └── supplies/            # 9 HTML files
│   └── results/                 # Generated Excel files
│       └── all_products_{timestamp}.xlsx
└── logs/                        # Pipeline execution logs
    └── scraper_{timestamp}.log
```

## 🚀 Usage

### Option 1: Run Complete Pipeline (Recommended)

```bash
cd /home/theafrazkhan/Desktop/scrappin/backend
python3 run_pipeline.py
```

This runs all 4 steps automatically and generates a complete Excel report.

### Option 2: Run Individual Steps

```bash
# Step 1: Login & save cookies
python3 login_and_save_cookies.py

# Step 2: Extract product links
python3 extract_product_links.py

# Step 3: Download HTML pages
python3 download_by_category.py

# Step 4: Generate Excel report
python3 extract_to_excel.py
```

## ⚙️ Configuration

### download_by_category.py Settings

```python
MAX_CONCURRENT = 5      # Number of concurrent downloads
PAGE_TIMEOUT = 30000    # 30 seconds per page
WAIT_FOR = 'networkidle' # Wait for network to be idle
```

**Why 5 concurrent downloads?**
- Balances speed with server resources
- Prevents overwhelming the target server
- Reduces risk of blocks/timeouts
- Each page waits for full render (~2-3 seconds)

### extract_to_excel.py Settings

```python
USE_IMAGE_FORMULA = True           # Use =IMAGE() formulas
PRODUCT_IMAGE_WIDTH = 150          # Main image width (pixels)
PRODUCT_IMAGE_HEIGHT = 150         # Main image height (pixels)
COLOR_SWATCH_WIDTH = 40            # Swatch width (pixels)
COLOR_SWATCH_HEIGHT = 40           # Swatch height (pixels)
MAX_COLOR_SWATCHES = 6             # Maximum swatch columns
```

## 📊 Excel Output Structure

### Column Layout (21 columns: A-U)

| Column | Name | Description |
|--------|------|-------------|
| A | Product Image | Main product image (=IMAGE formula) |
| B | Product Name | Full product name |
| C | SKU | Master product SKU |
| D | colorSku | SKU-color combination |
| E | sku name c | SKU name/identifier |
| F-K | Color Swatches 1-6 | Individual swatch images |
| L | Color Names | All colors comma-separated |
| M | Size | Size code (2, 4, 6, etc.) |
| N | Quantity | Available quantity (summed across lots) |
| O | In Stock | Yes/No |
| P | Retail Price | MSRP |
| Q | Wholesale Price | Wholesale cost |
| R | Description | Full product description |
| S | All Color Names | Complete color list |
| T | Gender | Category (women/men/accessories/supplies) |
| U | Product Type | Product type/category |

### Features
- ✅ IMAGE formulas work in Google Sheets & Excel 365+
- ✅ One row per size/color combination
- ✅ Quantities summed across all lots
- ✅ Alternating row colors for readability
- ✅ Auto-sized row height (80pt) for images
- ✅ Bordered cells with professional styling

## 🔍 Data Extraction Method

### Hybrid Approach (Most Reliable)

**__NEXT_DATA__ JSON (Core Product Data)**
- Product name
- Master SKU
- Retail price
- Wholesale price
- Description
- Product type

**DOM Parsing (Dynamic Data)**
- Product image (`class='image_image__ECDWj'`)
- Color swatches (`class='color-swatches-selector_colorSwatchContainer__fjw54'`)
- Inventory tables (`class='inventory-grid_accordionItem__XXIck'`)
- Size/quantity data (`class='inventory-grid-table_size__5wMgv'`)

**Why Hybrid?**
- Core data from JSON is accurate and consistent
- Inventory/swatches from DOM for real-time data
- More reliable than pure DOM extraction
- Faster than pure DOM parsing

## 🛠️ Prerequisites

### System Requirements
```bash
# Install Python 3.10+
sudo apt update
sudo apt install python3 python3-pip python3-venv

# Install Chrome/Chromium
sudo apt install chromium-browser

# Install Playwright browsers
python3 -m playwright install chromium
```

### Python Dependencies
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### Required Python Packages
- `playwright` - Browser automation for download_by_category.py
- `selenium` - Browser automation for login_and_save_cookies.py
- `beautifulsoup4` - HTML parsing
- `openpyxl` - Excel file generation
- `webdriver-manager` - ChromeDriver management

## 🔐 Credentials Setup

Credentials are stored in SQLite database (not .env files).

1. Login to web dashboard
2. Go to Settings
3. Add Lululemon wholesale credentials:
   - Email: your-email@company.com
   - Password: your-password

Credentials are read by `db_credentials.py` module.

## 📈 Performance

### Expected Timing (528 total products)

| Step | Duration | Details |
|------|----------|---------|
| 1. Login | ~30s | One-time authentication |
| 2. Extract Links | ~2-3 min | Downloads 4 category pages |
| 3. Download HTML | ~15-20 min | 5 concurrent, ~2s per page |
| 4. Generate Excel | ~2-3 min | Processes all HTML files |
| **Total** | **~20-25 min** | Complete pipeline |

### Optimization Tips

**For Faster Downloads:**
- Increase `MAX_CONCURRENT` to 10-15 (if server allows)
- Change `WAIT_FOR` to `'load'` instead of `'networkidle'`
- Reduce sleep time after page load

**For Lower Resource Usage:**
- Decrease `MAX_CONCURRENT` to 3
- Add longer delays between requests
- Process categories sequentially

## 🐛 Troubleshooting

### Issue: "No cookies found"
```bash
# Solution: Run login script first
python3 login_and_save_cookies.py
```

### Issue: "No HTML files found"
```bash
# Solution: Run download script
python3 download_by_category.py
```

### Issue: "Cookie expired" errors
```bash
# Solution: Re-login to get fresh cookies
python3 login_and_save_cookies.py
```

### Issue: Downloads timing out
```bash
# Solution: Increase timeout in download_by_category.py
PAGE_TIMEOUT = 60000  # 60 seconds
```

### Issue: Excel images not showing
```
Solution: Upload .xlsx to Google Sheets
IMAGE formulas work best in Google Sheets
```

## 📝 Logs

### Pipeline Logs
- Location: `backend/logs/scraper_{timestamp}.log`
- Contains: Complete pipeline execution details
- Created: Every run_pipeline.py execution

### Console Output
- Real-time progress updates
- Success/failure indicators
- File counts and statistics

## 🔄 Re-running the Pipeline

### Full Re-scrape
```bash
# Delete all data and start fresh
rm -rf data/html/*
rm -rf data/categories/*
rm data/cookie/cookie.json

# Run complete pipeline
python3 run_pipeline.py
```

### Update Only (Skip Existing Files)
```bash
# download_by_category.py automatically skips existing HTML files
python3 download_by_category.py

# Re-generate Excel with latest data
python3 extract_to_excel.py
```

### Incremental Update
```bash
# Only re-download specific category
rm -rf data/html/women/*
python3 download_by_category.py  # Will only download missing files

# Re-generate Excel
python3 extract_to_excel.py
```

## 🎯 Success Indicators

✅ **Step 1 Success:**
- `cookie.json` file created
- Contains 5+ cookies
- Console shows "✓ Cookies saved"

✅ **Step 2 Success:**
- 4 CSV files in `data/categories/`
- Each CSV has product URLs
- Total ~528 products

✅ **Step 3 Success:**
- HTML files in `data/html/{category}/`
- Each file ~500KB-1MB
- Total ~528 files

✅ **Step 4 Success:**
- Excel file in `data/results/`
- File size ~2-5MB
- Contains all products with images

## 🌐 Server Deployment

### Ubuntu VPS Setup
```bash
# 1. Clone repository
cd /home/user/Desktop
git clone <repo-url> scrappin

# 2. Install dependencies
cd scrappin/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Install system dependencies
sudo apt install chromium-browser
python3 -m playwright install chromium

# 4. Setup credentials via web interface
# (or manually in database)

# 5. Run pipeline
python3 run_pipeline.py
```

### Cron Job (Automated)
```bash
# Run daily at 2 AM
0 2 * * * cd /home/user/Desktop/scrappin/backend && /home/user/Desktop/scrappin/backend/venv/bin/python3 run_pipeline.py
```

## 📞 Support

For issues or questions:
1. Check logs in `backend/logs/`
2. Review console output for errors
3. Verify prerequisites are installed
4. Check credentials in database

---

**Last Updated:** December 8, 2025
**Pipeline Version:** 2.0
**Python Version:** 3.10+
