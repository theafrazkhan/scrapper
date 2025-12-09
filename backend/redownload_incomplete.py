#!/usr/bin/env python3
"""
Re-download incomplete HTML files that are missing inventory data.
This script scans existing HTML files and re-downloads those with issues.
"""

import os
import sys
import glob
import asyncio
import logging
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(SCRIPT_DIR, "data", "html")
COOKIES_FILE = os.path.join(SCRIPT_DIR, "data", "cookie", "cookie.json")
BASE_URL = "https://shop.lululemon.com/lululemon/product"


def check_html_completeness(html_file):
    """Check if HTML file has complete data"""
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html = f.read()
        
        # Must have reasonable size
        if len(html) < 50000:
            return False, "Small file size"
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Check for __NEXT_DATA__
        next_data = soup.find('script', {'id': '__NEXT_DATA__'})
        if not next_data:
            return False, "Missing __NEXT_DATA__"
        
        # Check for inventory table
        inventory_table = soup.find('table')
        if not inventory_table:
            return False, "Missing inventory table"
        
        # Check for product images
        product_image = soup.find('img', class_='image_image__ECDWj')
        if not product_image:
            return False, "Missing product image"
        
        return True, "Complete"
        
    except Exception as e:
        return False, f"Error: {str(e)}"


def scan_for_incomplete_files():
    """Scan all HTML files and find incomplete ones"""
    log.info("Scanning HTML files for incomplete data...")
    
    incomplete = []
    complete_count = 0
    
    # Scan all category folders
    if not os.path.exists(DATA_FOLDER):
        log.error(f"Data folder not found: {DATA_FOLDER}")
        return []
    
    for category in os.listdir(DATA_FOLDER):
        category_path = os.path.join(DATA_FOLDER, category)
        if not os.path.isdir(category_path):
            continue
        
        html_files = glob.glob(os.path.join(category_path, "*.html"))
        log.info(f"  Checking {category}: {len(html_files)} files")
        
        for html_file in html_files:
            is_complete, reason = check_html_completeness(html_file)
            
            if not is_complete:
                filename = os.path.basename(html_file)
                pid = filename[:-5]  # Remove .html
                url = f"{BASE_URL}/{pid}"
                
                incomplete.append({
                    'file': html_file,
                    'url': url,
                    'category': category,
                    'pid': pid,
                    'reason': reason
                })
            else:
                complete_count += 1
    
    log.info(f"\nScan complete:")
    log.info(f"  Complete: {complete_count}")
    log.info(f"  Incomplete: {len(incomplete)}")
    
    return incomplete


async def redownload_file(context, item):
    """Re-download a single incomplete file"""
    try:
        page = await context.new_page()
        
        log.info(f"Re-downloading: {item['pid']} (Reason: {item['reason']})")
        
        # Navigate and wait for content
        await page.goto(item['url'], wait_until='networkidle', timeout=45000)
        
        # Wait for critical elements
        try:
            await page.wait_for_selector('table tbody', timeout=10000, state='attached')
        except:
            log.warning(f"  ⚠ No inventory table: {item['pid']}")
        
        try:
            await page.wait_for_selector('img.image_image__ECDWj', timeout=10000, state='attached')
        except:
            log.warning(f"  ⚠ No product image: {item['pid']}")
        
        # Extra wait
        await asyncio.sleep(2)
        
        # Get HTML and save
        html = await page.content()
        await page.close()
        
        with open(item['file'], 'w', encoding='utf-8') as f:
            f.write(html)
        
        log.info(f"  ✓ Saved: {item['pid']} ({len(html)} bytes)")
        return True
        
    except Exception as e:
        log.error(f"  ✗ Failed {item['pid']}: {str(e)[:100]}")
        if page:
            try:
                await page.close()
            except:
                pass
        return False


async def redownload_incomplete_files(incomplete):
    """Re-download all incomplete files"""
    if not incomplete:
        log.info("No incomplete files to re-download!")
        return
    
    log.info(f"\nRe-downloading {len(incomplete)} incomplete files...")
    
    # Load cookies
    with open(COOKIES_FILE) as f:
        raw_cookies = json.load(f)
        cookies = []
        for c in raw_cookies:
            cookie = {
                'name': c['name'],
                'value': c['value'],
                'domain': c.get('domain', '.lululemon.com'),
                'path': c.get('path', '/')
            }
            if c.get('sameSite') in ['Strict', 'Lax', 'None']:
                cookie['sameSite'] = c['sameSite']
            cookies.append(cookie)
    
    log.info(f"✓ Loaded {len(cookies)} cookies")
    
    # Launch browser
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--headless=new', '--disable-gpu', '--no-sandbox', '--disable-dev-shm-usage']
        )
        
        context = await browser.new_context(java_script_enabled=True)
        await context.add_cookies(cookies)
        
        success = 0
        failed = 0
        
        # Download sequentially for reliability
        for item in incomplete:
            if await redownload_file(context, item):
                success += 1
            else:
                failed += 1
            
            # Progress
            if (success + failed) % 10 == 0:
                log.info(f"Progress: {success + failed}/{len(incomplete)}")
        
        await context.close()
        await browser.close()
    
    log.info(f"\n{'='*50}")
    log.info("RE-DOWNLOAD COMPLETE")
    log.info(f"{'='*50}")
    log.info(f"Success: {success}/{len(incomplete)}")
    log.info(f"Failed: {failed}")
    log.info(f"{'='*50}")


async def main():
    """Main function"""
    log.info("="*50)
    log.info("RE-DOWNLOAD INCOMPLETE HTML FILES")
    log.info("="*50)
    
    # Scan for incomplete files
    incomplete = scan_for_incomplete_files()
    
    if incomplete:
        log.info(f"\nFound {len(incomplete)} incomplete files:")
        for item in incomplete[:10]:  # Show first 10
            log.info(f"  - {item['pid']} ({item['category']}): {item['reason']}")
        
        if len(incomplete) > 10:
            log.info(f"  ... and {len(incomplete) - 10} more")
        
        # Ask for confirmation
        print(f"\nRe-download {len(incomplete)} files? [y/N]: ", end='')
        response = input().strip().lower()
        
        if response == 'y':
            await redownload_incomplete_files(incomplete)
        else:
            log.info("Cancelled by user")
    else:
        log.info("\n✓ All files are complete!")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.warning("\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        log.error(f"✗ Error: {str(e)}")
        sys.exit(1)
