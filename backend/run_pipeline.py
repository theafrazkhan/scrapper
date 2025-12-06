#!/usr/bin/env python3
"""
Lululemon Wholesale Scraper - Complete Pipeline
Runs all scraping steps in sequence:
1. Login and save cookies
2. Extract product links by category
3. Download product pages
4. Generate Excel report

Note: Credentials are fetched from the database, not .env files
"""

import os
import sys
import subprocess
import logging
from datetime import datetime
from pathlib import Path

# Import credential utility
try:
    from db_credentials import get_credentials
except ImportError:
    logging.error("Failed to import db_credentials module")
    sys.exit(1)

# Setup logging
def setup_logging():
    """Setup logging to both file and console"""
    # Create logs directory if it doesn't exist
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"scraper_{timestamp}.log"
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return log_file

def check_credentials():
    """Check if credentials exist in database"""
    try:
        username, password = get_credentials()
        
        if not username or not password:
            logging.error("❌ No Lululemon credentials found in database!")
            logging.error("Please add credentials through the web dashboard:")
            logging.error("  1. Login to the web interface")
            logging.error("  2. Go to Settings")
            logging.error("  3. Add Lululemon wholesale credentials")
            return False
        
        logging.info(f"✓ Found credentials for: {username}")
        return True
        
    except Exception as e:
        logging.error(f"❌ Error checking credentials: {e}")
        return False

def run_script(script_name, description):
    """Run a Python script and log output"""
    logging.info("\n" + "="*70)
    logging.info(f"{description}")
    logging.info("="*70)
    
    script_path = Path(__file__).parent / script_name
    
    if not script_path.exists():
        logging.error(f"❌ Script not found: {script_name}")
        return False
    
    try:
        logging.info(f"🚀 Running: {script_name}")
        
        # Run the script and stream output in real-time
        process = subprocess.Popen(
            [sys.executable, str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Stream output line by line
        for line in process.stdout:
            line = line.rstrip()
            if line:
                logging.info(line)
        
        process.wait()
        
        if process.returncode == 0:
            logging.info(f"✓ {script_name} completed successfully")
            return True
        else:
            logging.error(f"❌ {script_name} failed with exit code {process.returncode}")
            return False
            
    except Exception as e:
        logging.error(f"❌ Error running {script_name}: {e}")
        return False

def main():
    """Main pipeline function"""
    # Setup logging
    log_file = setup_logging()
    
    print("\n" + "="*70)
    print("🍋 LULULEMON WHOLESALE SCRAPER PIPELINE")
    print("="*70)
    logging.info("Pipeline started")
    logging.info(f"Log file: {log_file}")
    
    # Check credentials from database
    if not check_credentials():
        sys.exit(1)
    
    # Run scraping pipeline
    pipeline_steps = [
        ("login_and_save_cookies.py", "STEP 1: Login & Save Cookies"),
        ("extract_product_links.py", "STEP 2: Extract Product Links"),
        ("download_by_category.py", "STEP 3: Download Product Pages"),
        ("extract_to_excel.py", "STEP 4: Generate Excel Report")
    ]
    
    for script, description in pipeline_steps:
        if not run_script(script, description):
            logging.error(f"\n❌ Pipeline failed at: {script}")
            logging.error("Check the log file for details")
            sys.exit(1)
    
    # Success!
    logging.info("\n" + "="*70)
    logging.info("✅ PIPELINE COMPLETED SUCCESSFULLY!")
    logging.info("="*70)
    
    # Find the generated Excel file in data/results/
    results_dir = Path(__file__).parent / "data" / "results"
    excel_files = list(results_dir.glob("all_products_*.xlsx"))
    
    if excel_files:
        latest_excel = max(excel_files, key=lambda p: p.stat().st_mtime)
        logging.info(f"\n📊 Excel report generated: {latest_excel.name}")
        logging.info(f"📁 Full path: {latest_excel.absolute()}")
    
    logging.info(f"\n📝 Log file saved: {log_file}")
    logging.info("\n🎉 All done! Your product data is ready.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.warning("\n⚠️  Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"\n❌ Unexpected error: {e}", exc_info=True)
        sys.exit(1)
