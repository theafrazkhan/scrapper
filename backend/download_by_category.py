#!/usr/bin/env python3
"""
Download product pages organized by category
Reads CSV files from data/categories/ and saves HTML files to data/{category}/
"""

import csv
import json
import os
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime


class CategoryDownloader:
    def __init__(self, cookies_file, categories_folder, data_folder, max_concurrent=20, max_contexts=3):
        self.cookies_file = cookies_file
        self.categories_folder = categories_folder
        self.data_folder = data_folder
        self.max_concurrent = max_concurrent  # Reduced to 20 for server stability
        self.max_contexts = max_contexts  # Reduced to 3 contexts for better reliability
        self.cookies = []
        
    def load_cookies(self):
        """Load cookies from JSON file"""
        with open(self.cookies_file, 'r') as f:
            cookies_data = json.load(f)
        
        # Convert to Playwright format
        for cookie in cookies_data:
            playwright_cookie = {
                'name': cookie['name'],
                'value': cookie['value'],
                'domain': cookie.get('domain', '.lululemon.com'),
                'path': cookie.get('path', '/'),
                'httpOnly': cookie.get('httpOnly', False),
                'secure': cookie.get('secure', False)
            }
            # Only add sameSite if it's a valid value
            if 'sameSite' in cookie and cookie['sameSite'] in ['Strict', 'Lax', 'None']:
                playwright_cookie['sameSite'] = cookie['sameSite']
            
            self.cookies.append(playwright_cookie)
        
        print(f"✓ Loaded {len(self.cookies)} cookies")
    
    def load_category_urls(self, category_name):
        """Load product URLs from a category CSV file"""
        csv_file = os.path.join(self.categories_folder, f"{category_name}.csv")
        urls = []
        
        if not os.path.exists(csv_file):
            print(f"⚠️  CSV file not found: {csv_file}")
            return urls
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)  # Skip header if present
            for row in reader:
                if row:  # Skip empty rows
                    urls.append(row[0])
        
        return urls
    
    async def download_page(self, context, url, category_folder, semaphore, stats):
        """Download a single page using a browser context"""
        async with semaphore:
            product_id = url.rstrip('/').split('/')[-1]
            output_file = os.path.join(category_folder, f"{product_id}.html")
            
            page = None
            try:
                # Create a new page in the context
                page = await context.new_page()
                
                # Longer timeout and better wait strategy for server reliability
                await page.goto(url, wait_until='networkidle', timeout=45000)
                
                # Wait for the product data script to load
                try:
                    await page.wait_for_selector('script#__NEXT_DATA__', timeout=8000)
                    # Wait for content to fully render
                    await asyncio.sleep(1.5)
                except:
                    # If __NEXT_DATA__ not found, try alternative selectors and wait longer
                    try:
                        await page.wait_for_selector('[data-testid="product-details"]', timeout=5000)
                    except:
                        pass
                    # Extra wait for dynamic content
                    await asyncio.sleep(2)
                
                # Ensure all JavaScript has executed
                await page.wait_for_load_state('domcontentloaded')
                await asyncio.sleep(1)
                
                # Get the HTML
                html = await page.content()
                
                # Verify we got actual content (not error page)
                if len(html) < 1000:
                    raise Exception(f"Page content too short ({len(html)} bytes) - might be an error page")
                
                # Save to file
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(html)
                
                await page.close()
                
                stats['downloaded'] += 1
                
                # More frequent progress updates
                if stats['downloaded'] % 5 == 0:
                    print(f"  [Progress] {stats['downloaded']}/{stats['total']} pages downloaded")
                
                # Delay between downloads to avoid rate limiting
                await asyncio.sleep(1.0)
                
                return True
                
            except Exception as e:
                print(f"  ❌ Error downloading {product_id}: {e}")
                stats['failed'] += 1
                if page:
                    await page.close()
                
                # Longer delay after error
                await asyncio.sleep(3)
                return False
    
    async def download_category(self, browser, category_name, urls):
        """Download all pages for a specific category"""
        print(f"\n📦 Category: {category_name.upper()}")
        print(f"   URLs to download: {len(urls)}")
        
        if not urls:
            print(f"   ⚠️  No URLs found for {category_name}")
            return {'downloaded': 0, 'failed': 0, 'total': 0}
        
        # Create category folder
        category_folder = os.path.join(self.data_folder, category_name)
        
        # Delete existing files in the folder if it exists
        if os.path.exists(category_folder):
            print(f"   🗑️  Clearing existing files in {category_name}/")
            for filename in os.listdir(category_folder):
                file_path = os.path.join(category_folder, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
        
        os.makedirs(category_folder, exist_ok=True)
        
        # Create multiple contexts for better parallelism (connection pooling)
        contexts = []
        for _ in range(self.max_contexts):
            context = await browser.new_context()
            await context.add_cookies(self.cookies)
            contexts.append(context)
        
        # Stats for this category
        stats = {'downloaded': 0, 'failed': 0, 'total': len(urls)}
        
        # Create semaphore to limit concurrent downloads
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # Download all pages in parallel using round-robin context assignment
        tasks = []
        for idx, url in enumerate(urls):
            context = contexts[idx % len(contexts)]  # Distribute across contexts
            tasks.append(self.download_page(context, url, category_folder, semaphore, stats))
        
        await asyncio.gather(*tasks)
        
        # Close all contexts
        for context in contexts:
            await context.close()
        
        print(f"   ✅ Downloaded: {stats['downloaded']}/{stats['total']} pages")
        if stats['failed'] > 0:
            print(f"   ❌ Failed: {stats['failed']} pages")
        
        return stats
    
    async def download_all_categories(self):
        """Download pages for all categories"""
        print("\n" + "=" * 70)
        print("Category-Based Product Page Downloader")
        print("=" * 70)
        
        # Load cookies
        print("\n🔐 Loading session cookies...")
        self.load_cookies()
        
        # Find all category CSV files
        categories = ['women', 'men', 'accessories', 'supplies']
        
        print(f"\n📂 Categories to process: {', '.join(categories)}")
        
        start_time = datetime.now()
        total_stats = {'downloaded': 0, 'failed': 0, 'total': 0}
        
        async with async_playwright() as p:
            # Launch browser with optimized settings for high-speed VPS
            print("\n🚀 Starting browser...")
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',  # Overcome limited resource problems
                    '--no-sandbox',  # Required for some VPS environments
                    '--disable-setuid-sandbox',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--ignore-certificate-errors',
                ]
            )
            
            # Process each category
            for category_name in categories:
                urls = self.load_category_urls(category_name)
                stats = await self.download_category(browser, category_name, urls)
                
                total_stats['downloaded'] += stats['downloaded']
                total_stats['failed'] += stats['failed']
                total_stats['total'] += stats['total']
            
            await browser.close()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Summary
        print("\n" + "=" * 70)
        print("DOWNLOAD COMPLETE!")
        print("=" * 70)
        print(f"✅ Successfully downloaded: {total_stats['downloaded']} pages")
        if total_stats['failed'] > 0:
            print(f"❌ Failed: {total_stats['failed']} pages")
        print(f"⏱️  Total time: {int(duration)} seconds ({duration/60:.1f} minutes)")
        if total_stats['downloaded'] > 0:
            pages_per_second = total_stats['downloaded'] / duration
            print(f"⚡ Average speed: {pages_per_second:.2f} pages/second")
        print(f"📂 Files saved to: {self.data_folder}/{{category}}/")
        print("=" * 70)


async def main():
    """Main function"""
    import sys
    
    # Use relative paths - works on both local and server
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Allow command-line override for concurrent downloads (default: 50 for VPS)
    max_concurrent = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    max_contexts = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    print(f"\n⚙️  Performance Settings:")
    print(f"   • Max concurrent downloads: {max_concurrent}")
    print(f"   • Browser contexts: {max_contexts}")
    
    downloader = CategoryDownloader(
        cookies_file=os.path.join(script_dir, "data/cookie/cookie.json"),
        categories_folder=os.path.join(script_dir, "data/categories"),
        data_folder=os.path.join(script_dir, "data"),
        max_concurrent=max_concurrent,
        max_contexts=max_contexts
    )
    
    await downloader.download_all_categories()


if __name__ == "__main__":
    asyncio.run(main())
