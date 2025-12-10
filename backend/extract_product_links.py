#!/usr/bin/env python3
"""
Download category pages and extract product links
Downloads HTML pages for 4 categories (women, men, accessories, supplies) 
and extracts product links into separate CSV files per category
"""

import os
import csv
import json
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime
from playwright.async_api import async_playwright


# Configuration - Use relative paths for portability
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LINKS_CSV = os.path.join(BASE_DIR, "data/links.csv")
DATA_FOLDER = os.path.join(BASE_DIR, "data")
CATEGORIES_FOLDER = os.path.join(DATA_FOLDER, "categories")
COOKIES_FILE = os.path.join(BASE_DIR, "data/cookie/cookie.json")


def load_cookies():
    """Load cookies from JSON file"""
    try:
        with open(COOKIES_FILE, 'r') as f:
            cookies_data = json.load(f)
            # Convert to Playwright format and filter out invalid sameSite values
            playwright_cookies = []
            for cookie in cookies_data:
                # Skip or fix invalid sameSite values
                if 'sameSite' in cookie:
                    if cookie['sameSite'] not in ['Strict', 'Lax', 'None']:
                        cookie['sameSite'] = 'Lax'  # Default to Lax
                playwright_cookies.append(cookie)
            return playwright_cookies
    except Exception as e:
        print(f"⚠ Warning: Could not load cookies: {e}")
        return []


def read_category_links():
    """Read category links from CSV file"""
    categories = {}
    try:
        with open(LINKS_CSV, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                url = line.strip()
                if url:
                    # Extract category name from URL
                    # Example: https://wholesale.lululemon.com/lululemon/women?... -> women
                    if '/whats-new' in url or '/what-new' in url:
                        categories['whats-new'] = url
                    elif '/women' in url:
                        categories['women'] = url
                    elif '/men' in url:
                        categories['men'] = url
                    elif '/accessories' in url:
                        categories['accessories'] = url
                    elif '/supplies' in url:
                        categories['supplies'] = url
        return categories
    except Exception as e:
        print(f"❌ Error reading {LINKS_CSV}: {e}")
        return {}


async def download_category_page(context, category_name, url):
    """Download a single category page"""
    print(f"\n📥 Downloading: {category_name}")
    
    try:
        page = await context.new_page()
        
        # Step 1: Load the initial page to get the total count
        print(f"   ⏳ Loading initial page to detect total products...")
        await page.goto(url, wait_until='domcontentloaded', timeout=120000)
        
        # Wait for page to load
        await asyncio.sleep(5)
        
        # Extract total count from "Showing X of Y items"
        total_products = None
        try:
            # Look for the grid container first, then find the paragraph with count
            print(f"   ⏳ Searching for product count...")
            
            # Method 1: Look for the specific grid structure
            try:
                # Find the grid container and get text content
                grid_locator = page.locator('div.grid.grid-cols-4.gap-24').first
                # Look for paragraph with "Showing X of Y items" pattern inside or near it
                count_locator = grid_locator.locator('p:has-text("Showing")').first
                count_text = await count_locator.text_content(timeout=10000)
                print(f"   ℹ️ Found count text in grid: {count_text}")
                
                if count_text:
                    import re
                    match = re.search(r'Showing\s+\d+\s+of\s+(\d+)\s+items?', count_text, re.IGNORECASE)
                    if match:
                        total_products = int(match.group(1))
                        print(f"   ✓ Detected {total_products} total products in category")
            except Exception as e:
                print(f"   ⚠ Grid method failed: {e}")
            
            # Method 2: Search entire page for the pattern if grid method failed
            if not total_products:
                try:
                    # Look for any paragraph with the pattern
                    count_locator = page.locator('p:has-text("Showing")').first
                    count_text = await count_locator.text_content(timeout=10000)
                    print(f"   ℹ️ Found count text (fallback): {count_text}")
                    
                    if count_text:
                        import re
                        match = re.search(r'Showing\s+\d+\s+of\s+(\d+)\s+items?', count_text, re.IGNORECASE)
                        if match:
                            total_products = int(match.group(1))
                            print(f"   ✓ Detected {total_products} total products in category")
                except Exception as e:
                    print(f"   ⚠ Paragraph search failed: {e}")
            
            # Method 3: Last resort - search HTML content directly
            if not total_products:
                print(f"   ⏳ Searching page HTML for count...")
                page_text = await page.content()
                import re
                match = re.search(r'Showing\s+\d+\s+of\s+(\d+)\s+items?', page_text, re.IGNORECASE)
                if match:
                    total_products = int(match.group(1))
                    print(f"   ✓ Detected {total_products} total products in category (from HTML)")
                else:
                    print(f"   ⚠ Could not find product count pattern in HTML")
                    
        except Exception as e:
            print(f"   ⚠ Could not detect total count: {e}")
        
        # Step 2: If we found a total, update the URL with the correct limit
        if total_products:
            # Parse URL and update limit parameter
            import re
            if '?' in url:
                base_url, params = url.split('?', 1)
                # Replace limit parameter
                new_params = re.sub(r'limit=\d+', f'limit={total_products}', params)
                # If limit wasn't in params, add it
                if 'limit=' not in params:
                    new_params = f'limit={total_products}&{new_params}'
                updated_url = f"{base_url}?{new_params}"
            else:
                updated_url = f"{url}?limit={total_products}"
            
            print(f"   ⏳ Reloading with limit={total_products}...")
            await page.goto(updated_url, wait_until='domcontentloaded', timeout=120000)
            await asyncio.sleep(8)  # Wait for all products to load
        else:
            print(f"   ⚠ Using default limit, could not detect total")
            await asyncio.sleep(8)
        
        # Wait for products to be in DOM
        try:
            await page.wait_for_selector('a[href*="/p/"]', timeout=20000)
            product_count = await page.locator('a[href*="/p/"]').count()
            print(f"   ✓ Found {product_count} product links in DOM")
        except:
            print(f"   ⚠ Timeout waiting for product elements")
        
        # Get HTML content
        html_content = await page.content()
        
        # Save to file
        output_file = f"{DATA_FOLDER}/{category_name}.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"   ✓ Saved to: {output_file}")
        
        await page.close()
        return output_file
        
    except Exception as e:
        print(f"   ❌ Error downloading {category_name}: {e}")
        return None


def extract_product_links_from_html(html_file, category_name):
    """Extract product links from downloaded HTML file using __NEXT_DATA__ JSON"""
    print(f"\n🔍 Extracting links from: {category_name}.html")
    
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        product_links = set()
        
        # Method 1: Extract from __NEXT_DATA__ JSON (more reliable)
        script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
        if script_tag and script_tag.string:
            try:
                json_data = json.loads(script_tag.string)
                
                # Navigate through the JSON to find products
                # The structure is: props.pageProps.data.dataSource.items
                page_props = json_data.get('props', {}).get('pageProps', {})
                data = page_props.get('data', {})
                data_source = data.get('dataSource', {})
                items = data_source.get('items', [])
                
                print(f"   📦 Found {len(items)} products in JSON data")
                
                for item in items:
                    # Extract the product slug/ID
                    slug = item.get('slug')
                    if slug:
                        # Build the product URL
                        product_url = f"https://wholesale.lululemon.com/p/{slug}"
                        product_links.add(product_url)
                
                if product_links:
                    print(f"   ✓ Extracted {len(product_links)} unique product links from JSON")
                    return product_links
            except json.JSONDecodeError as e:
                print(f"   ⚠ Could not parse JSON: {e}")
            except Exception as e:
                print(f"   ⚠ Error extracting from JSON: {e}")
        
        # Method 2: Fallback to HTML parsing (if JSON extraction fails)
        print(f"   ℹ️  Falling back to HTML parsing...")
        
        # Look for product card links more specifically
        # Product links have format: /p/{product-name}/{product-id}
        import re
        product_pattern = re.compile(r'^/p/[^/]+/[^/?#]+$')  # Strict: must start with /p/ and have exactly 2 segments
        
        # Only look in the product grid area to avoid navigation/footer links
        # Try to find the product grid container first
        product_grid = soup.find('div', class_=lambda x: x and 'grid' in x and 'grid-cols' in x)
        search_area = product_grid if product_grid else soup
        
        for a_tag in search_area.find_all('a', href=True):
            href = a_tag['href']
            
            # Clean the href first (remove query params)
            clean_href = href.split('?')[0].split('#')[0]
            
            # Check if this matches the strict product URL pattern
            if product_pattern.match(clean_href):
                # Convert to full URL
                if clean_href.startswith('/'):
                    full_url = f"https://wholesale.lululemon.com{clean_href}"
                else:
                    continue
                
                product_links.add(full_url)
        
        print(f"   ✓ Found {len(product_links)} unique product links")
        return product_links
        
    except Exception as e:
        print(f"   ❌ Error extracting links: {e}")
        return set()


def save_links_to_csv(product_links, category_name):
    """Save product links to category-specific CSV file"""
    # Create categories folder if it doesn't exist
    os.makedirs(CATEGORIES_FOLDER, exist_ok=True)
    
    output_file = f"{CATEGORIES_FOLDER}/{category_name}.csv"
    sorted_links = sorted(list(product_links))
    
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Product URL'])
            for link in sorted_links:
                writer.writerow([link])
        
        print(f"   ✓ Saved to: {output_file}")
        return True
    except Exception as e:
        print(f"   ❌ Error saving CSV: {e}")
        return False


async def main():
    """Main function"""
    print("=" * 70)
    print("Category Page Downloader & Product Link Extractor")
    print("=" * 70)
    
    # Create necessary folders
    os.makedirs(DATA_FOLDER, exist_ok=True)
    os.makedirs(CATEGORIES_FOLDER, exist_ok=True)
    
    # Read category links
    print("\n📖 Reading category links from CSV...")
    categories = read_category_links()
    
    if not categories:
        print("❌ No categories found in links.csv")
        return
    
    print(f"✓ Found {len(categories)} categories: {', '.join(categories.keys())}")
    
    # Load cookies
    print("\n🍪 Loading session cookies...")
    cookies = load_cookies()
    print(f"✓ Loaded {len(cookies)} cookies")
    
    # Download category pages
    print("\n" + "=" * 70)
    print("STEP 1: Downloading Category Pages")
    print("=" * 70)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        
        # Add cookies to context
        if cookies:
            await context.add_cookies(cookies)
        
        # Download all category pages
        downloaded_files = {}
        for category_name, url in categories.items():
            html_file = await download_category_page(context, category_name, url)
            if html_file:
                downloaded_files[category_name] = html_file
        
        await browser.close()
    
    # Extract product links from each category
    print("\n" + "=" * 70)
    print("STEP 2: Extracting Product Links")
    print("=" * 70)
    
    total_links = 0
    summary = {}
    
    for category_name, html_file in downloaded_files.items():
        product_links = extract_product_links_from_html(html_file, category_name)
        if product_links:
            save_links_to_csv(product_links, category_name)
            summary[category_name] = len(product_links)
            total_links += len(product_links)
    
    # Clean up: Delete HTML files after extraction
    print("\n" + "=" * 70)
    print("STEP 3: Cleaning Up HTML Files")
    print("=" * 70)
    
    for category_name, html_file in downloaded_files.items():
        if html_file and os.path.exists(html_file):
            try:
                os.remove(html_file)
                print(f"🗑️  Deleted: {os.path.basename(html_file)}")
            except Exception as e:
                print(f"⚠️  Could not delete {os.path.basename(html_file)}: {e}")
    
    # Print summary
    print("\n" + "=" * 70)
    print("EXTRACTION COMPLETE!")
    print("=" * 70)
    for category_name, count in summary.items():
        print(f"✓ {category_name.capitalize()}: {count} product links")
    print(f"\n🔗 Total unique product links: {total_links}")
    print(f"📁 CSV files saved in: {CATEGORIES_FOLDER}/")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
