#!/usr/bin/env python3
"""
Download fully rendered HTML pages from Lululemon using Playwright.
Downloads pages with 5 concurrent connections for optimal speed.
"""

import csv
import json
import os
import sys
import asyncio
import logging
from datetime import datetime
from playwright.async_api import async_playwright

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger(__name__)

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_CONCURRENT = 10 # 10 concurrent downloads
PAGE_TIMEOUT = 30000  # 30 seconds
WAIT_FOR = 'networkidle'  # Wait for network to be idle for fully rendered content

log.info(f"Script directory: {SCRIPT_DIR}")
log.info(f"Config: MAX_CONCURRENT={MAX_CONCURRENT}, PAGE_TIMEOUT={PAGE_TIMEOUT}ms, WAIT_FOR={WAIT_FOR}")


class PageDownloader:
    def __init__(self, cookies_file, categories_folder, output_folder):
        self.cookies_file = cookies_file
        self.categories_folder = categories_folder
        self.output_folder = output_folder
        self.cookies = []
        self.stats = {'done': 0, 'fail': 0, 'total': 0}
        
        log.info(f"PageDownloader initialized")
        log.info(f"  Cookies: {cookies_file}")
        log.info(f"  Categories: {categories_folder}")
        log.info(f"  Output: {output_folder}")
    
    def check_prerequisites(self):
        """Check required files exist"""
        log.info("Checking prerequisites...")
        errors = []
        
        if not os.path.exists(self.cookies_file):
            errors.append(f"Cookie file NOT FOUND: {self.cookies_file}")
            log.error(f"❌ Cookie file missing: {self.cookies_file}")
            log.error(f"   Run: python login_and_save_cookies.py")
        else:
            log.info(f"✓ Cookie file exists")
        
        if not os.path.exists(self.categories_folder):
            errors.append(f"Categories folder NOT FOUND: {self.categories_folder}")
            log.error(f"❌ Categories folder missing: {self.categories_folder}")
        else:
            csv_files = [f for f in os.listdir(self.categories_folder) if f.endswith('.csv')]
            if csv_files:
                log.info(f"✓ Categories folder: {csv_files}")
            else:
                errors.append("No CSV files in categories folder")
                log.error(f"❌ No CSV files found")
        
        if errors:
            log.error("="*50)
            log.error("PREREQUISITES FAILED - Run these first:")
            log.error("  1. python login_and_save_cookies.py")
            log.error("  2. python extract_product_links.py")
            log.error("="*50)
            return False
        
        return True
    
    def load_cookies(self):
        """Load cookies from file"""
        log.info(f"Loading cookies...")
        with open(self.cookies_file) as f:
            for c in json.load(f):
                cookie = {
                    'name': c['name'],
                    'value': c['value'],
                    'domain': c.get('domain', '.lululemon.com'),
                    'path': c.get('path', '/')
                }
                if c.get('sameSite') in ['Strict', 'Lax', 'None']:
                    cookie['sameSite'] = c['sameSite']
                self.cookies.append(cookie)
        log.info(f"✓ Loaded {len(self.cookies)} cookies")
    
    def load_urls(self, cat):
        """Load product URLs for a category"""
        path = os.path.join(self.categories_folder, f"{cat}.csv")
        if not os.path.exists(path):
            return []
        with open(path) as f:
            reader = csv.reader(f)
            next(reader, None)  # Skip header
            return [r[0] for r in reader if r]
    
    def discover_categories(self):
        """Discover all available categories from CSV files"""
        if not os.path.exists(self.categories_folder):
            return []
        
        categories = []
        for file in os.listdir(self.categories_folder):
            if file.endswith('.csv'):
                # Get category name from filename (e.g., 'women.csv' -> 'women')
                category = file[:-4]
                categories.append(category)
        
        return sorted(categories)
    
    def ensure_output_dir(self, cat):
        """Create output directory for category"""
        cat_dir = os.path.join(self.output_folder, cat)
        os.makedirs(cat_dir, exist_ok=True)
        return cat_dir
    
    async def download_page(self, context, url, cat, output_dir, sem):
        """Download a single fully rendered page"""
        pid = url.rstrip('/').split('/')[-1]
        output_file = os.path.join(output_dir, f"{pid}.html")
        
        # Skip if already exists
        if os.path.exists(output_file):
            self.stats['done'] += 1
            log.debug(f"[{cat}] ⏭️  Already exists: {pid}")
            return True
        
        async with sem:
            page = None
            try:
                page = await context.new_page()
                
                # Navigate to page and wait for full render
                log.debug(f"[{cat}] 📥 Downloading: {pid}")
                await page.goto(url, wait_until=WAIT_FOR, timeout=PAGE_TIMEOUT)
                
                # Small delay to ensure everything is loaded
                await asyncio.sleep(1)
                
                # Get fully rendered HTML
                html = await page.content()
                await page.close()
                
                # Save to file
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(html)
                
                self.stats['done'] += 1
                log.debug(f"[{cat}] ✓ Saved: {pid} ({len(html)} bytes)")
                
                # Progress update every 20 files
                if self.stats['done'] % 20 == 0:
                    log.info(f"Progress: {self.stats['done']}/{self.stats['total']} done, {self.stats['fail']} failed")
                
                return True
                
            except Exception as e:
                self.stats['fail'] += 1
                log.error(f"[{cat}] ✗ {pid}: {type(e).__name__}: {str(e)[:100]}")
                if page:
                    try:
                        await page.close()
                    except:
                        pass
                return False
    
    async def run(self):
        """Main download loop"""
        log.info("="*50)
        log.info("DOWNLOAD BY CATEGORY - PLAYWRIGHT")
        log.info("Downloading fully rendered HTML pages")
        log.info("="*50)
        
        if not self.check_prerequisites():
            return
        
        self.load_cookies()
        
        # Discover all available categories dynamically
        cats = self.discover_categories()
        
        if not cats:
            log.error("No category CSV files found!")
            return
        
        urls = {}
        
        log.info("\nLoading categories...")
        for c in cats:
            urls[c] = self.load_urls(c)
            self.stats['total'] += len(urls[c])
            if urls[c]:
                log.info(f"  {c}: {len(urls[c])} products")
        
        log.info(f"\nTotal: {self.stats['total']} products to download")
        
        if self.stats['total'] == 0:
            log.error("No products found! Check category CSV files.")
            return
        
        start = datetime.now()
        
        try:
            async with async_playwright() as p:
                log.info("\nLaunching browser...")
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--headless=new',
                        '--disable-gpu',
                        '--no-sandbox',
                        '--disable-dev-shm-usage'
                    ]
                )
                log.info(f"✓ Browser ready")
                log.info(f"  Concurrency: {MAX_CONCURRENT}")
                log.info(f"  Timeout: {PAGE_TIMEOUT}ms")
                
                for cat in cats:
                    if not urls[cat]:
                        continue
                    
                    log.info(f"\n{'='*40}")
                    log.info(f"CATEGORY: {cat.upper()} ({len(urls[cat])} products)")
                    log.info(f"{'='*40}")
                    
                    # Create output directory
                    output_dir = self.ensure_output_dir(cat)
                    log.info(f"Output: {output_dir}")
                    
                    # Create browser context with cookies
                    ctx = await browser.new_context(java_script_enabled=True)
                    await ctx.add_cookies(self.cookies)
                    
                    # Semaphore for concurrency control
                    sem = asyncio.Semaphore(MAX_CONCURRENT)
                    cat_start = datetime.now()
                    
                    # Download all pages concurrently
                    results = await asyncio.gather(*[
                        self.download_page(ctx, u, cat, output_dir, sem) 
                        for u in urls[cat]
                    ], return_exceptions=True)
                    
                    success = sum(1 for r in results if r is True)
                    cat_dur = (datetime.now() - cat_start).total_seconds()
                    log.info(f"✓ {cat}: {success}/{len(urls[cat])} downloaded in {cat_dur:.1f}s")
                    
                    await ctx.close()
                
                await browser.close()
                log.info("\n✓ Browser closed")
        
        except Exception as e:
            log.error(f"Browser error: {type(e).__name__}: {str(e)}")
            raise
        
        # Final summary
        duration = (datetime.now() - start).total_seconds()
        log.info("\n" + "="*50)
        log.info("DOWNLOAD COMPLETE")
        log.info("="*50)
        log.info(f"Total: {self.stats['done']}/{self.stats['total']} downloaded")
        log.info(f"Failed: {self.stats['fail']}")
        log.info(f"Duration: {duration:.1f}s")
        log.info(f"Average: {duration/self.stats['total']:.2f}s per page")
        log.info("="*50)


async def main():
    """Entry point"""
    cookies_file = os.path.join(SCRIPT_DIR, 'data', 'cookie', 'cookie.json')
    categories_folder = os.path.join(SCRIPT_DIR, 'data', 'categories')
    output_folder = os.path.join(SCRIPT_DIR, 'data', 'html')
    
    downloader = PageDownloader(cookies_file, categories_folder, output_folder)
    await downloader.run()


if __name__ == '__main__':
    log.info("Starting download_by_category.py")
    log.info(f"Working directory: {os.getcwd()}")
    try:
        asyncio.run(main())
        log.info("✓ Script completed successfully")
    except KeyboardInterrupt:
        log.warning("\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        log.error(f"✗ Script failed: {type(e).__name__}: {str(e)}")
        sys.exit(1)
