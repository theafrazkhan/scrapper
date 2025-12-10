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
    """Setup logging to both file and console with unbuffered output"""
    # Force unbuffered output for Docker logs
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    
    # Create logs directory if it doesn't exist
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"scraper_{timestamp}.log"
    
    # Configure logging with immediate flush
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='a'),
            logging.StreamHandler(sys.stdout)
        ],
        force=True
    )
    
    # Set all handlers to flush immediately
    for handler in logging.root.handlers:
        handler.flush()
    
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
    """Run a Python script and log output with real-time streaming"""
    logging.info("\n" + "="*70)
    logging.info(f"{description}")
    logging.info("="*70)
    sys.stdout.flush()
    
    script_path = Path(__file__).parent / script_name
    
    if not script_path.exists():
        logging.error(f"❌ Script not found: {script_name}")
        sys.stdout.flush()
        return False
    
    try:
        logging.info(f"🚀 Running: {script_name}")
        logging.info(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        sys.stdout.flush()
        
        start_time = datetime.now()
        
        # Run the script and stream output in real-time
        process = subprocess.Popen(
            [sys.executable, str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        line_count = 0
        # Stream output line by line
        for line in process.stdout:
            line = line.rstrip()
            if line:
                logging.info(line)
                line_count += 1
                # Flush every 10 lines to ensure visibility
                if line_count % 10 == 0:
                    sys.stdout.flush()
        
        process.wait()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if process.returncode == 0:
            logging.info(f"✅ {script_name} completed successfully")
            logging.info(f"⏱️  Duration: {duration:.1f} seconds")
            sys.stdout.flush()
            return True
        else:
            logging.error(f"❌ {script_name} failed with exit code {process.returncode}")
            logging.error(f"⏱️  Duration: {duration:.1f} seconds")
            sys.stdout.flush()
            return False
            
    except Exception as e:
        logging.error(f"❌ Error running {script_name}: {e}")
        sys.stdout.flush()
        return False

def cleanup_temporary_files():
    """Clean up temporary files after successful scraping, keeping only logs and results"""
    logging.info("\n" + "="*70)
    logging.info("CLEANUP: Removing temporary files...")
    logging.info("="*70)
    
    data_dir = Path(__file__).parent / "data"
    
    try:
        import shutil
        
        # List of folders/files to delete
        cleanup_items = [
            data_dir / "cookie",
            data_dir / "categories", 
            data_dir / "html",
            data_dir / "links.csv"
        ]
        
        for item in cleanup_items:
            if item.exists():
                if item.is_dir():
                    shutil.rmtree(item)
                    logging.info(f"✓ Deleted folder: {item.name}/")
                else:
                    item.unlink()
                    logging.info(f"✓ Deleted file: {item.name}")
            else:
                logging.info(f"⚠️  Not found: {item.name}")
        
        # Keep only logs and results
        logging.info("\n✓ Cleanup complete! Kept folders:")
        logging.info("  - logs/")
        logging.info("  - results/")
        
        return True
        
    except Exception as e:
        logging.error(f"❌ Error during cleanup: {e}")
        return False


def main():
    """Main pipeline function"""
    # Setup logging
    log_file = setup_logging()
    
    print("\n" + "="*70)
    print("🍋 LULULEMON WHOLESALE SCRAPER PIPELINE")
    print("="*70)
    sys.stdout.flush()
    
    logging.info("Pipeline started")
    logging.info(f"Log file: {log_file}")
    logging.info(f"Python: {sys.executable}")
    logging.info(f"Working directory: {Path(__file__).parent}")
    sys.stdout.flush()
    
    # Check credentials from database
    logging.info("\n" + "="*70)
    logging.info("STEP 0: Checking Database Credentials")
    logging.info("="*70)
    sys.stdout.flush()
    
    if not check_credentials():
        sys.exit(1)
    
    # Run scraping pipeline
    pipeline_steps = [
        ("login_and_save_cookies.py", "STEP 1: Login & Extract Product Links (in same session)"),
        # REMOVED: extract_product_links.py - now handled in login script with same browser session
        ("download_by_category.py", "STEP 2: Download Product Pages"),
        ("extract_to_excel.py", "STEP 3: Generate Excel Report")
    ]
    
    total_start = datetime.now()
    logging.info(f"\n🎬 Starting pipeline at: {total_start.strftime('%Y-%m-%d %H:%M:%S')}")
    sys.stdout.flush()
    
    for idx, (script, description) in enumerate(pipeline_steps, 1):
        logging.info(f"\n📍 Progress: Step {idx}/{len(pipeline_steps)}")
        sys.stdout.flush()
        
        if not run_script(script, description):
            logging.error(f"\n❌ Pipeline failed at: {script}")
            logging.error("Check the log file for details")
            sys.stdout.flush()
            sys.exit(1)
    
    # Clean up temporary files
    cleanup_temporary_files()
    
    # Success!
    total_end = datetime.now()
    total_duration = (total_end - total_start).total_seconds()
    
    logging.info("\n" + "="*70)
    logging.info("✅ PIPELINE COMPLETED SUCCESSFULLY!")
    logging.info("="*70)
    logging.info(f"⏱️  Total execution time: {total_duration:.1f} seconds ({total_duration/60:.1f} minutes)")
    sys.stdout.flush()
    
    # Find the generated Excel file in data/results/
    results_dir = Path(__file__).parent / "data" / "results"
    excel_files = list(results_dir.glob("all_products_*.xlsx"))
    
    if excel_files:
        latest_excel = max(excel_files, key=lambda p: p.stat().st_mtime)
        logging.info(f"\n📊 Excel report generated: {latest_excel.name}")
        logging.info(f"📁 Full path: {latest_excel.absolute()}")
    
    logging.info(f"\n📝 Log file saved: {log_file}")
    logging.info("\n🎉 All done! Your product data is ready.")
    sys.stdout.flush()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.warning("\n⚠️  Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"\n❌ Unexpected error: {e}", exc_info=True)
        sys.exit(1)
