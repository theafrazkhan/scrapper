#!/usr/bin/env python3
"""Product page downloader using Playwright - gets rendered DOM."""

import csv
import json
import os
import asyncio
import random
from playwright.async_api import async_playwright
from datetime import datetime


class ProductDownloader:
    
    def __init__(self, cookies_file, categories_folder, data_folder, max_concurrent=12):
        self.cookies_file = cookies_file
        self.categories_folder = categories_folder
        self.data_folder = data_folder
        self.max_concurrent = max_concurrent
        self.cookies = []
        self.stats = {'downloaded': 0, 'failed': 0, 'total': 0}
        
    def load_cookies(self):
        with open(self.cookies_file, 'r') as f:
            raw_cookies = json.load(f)
        
        for c in raw_cookies:
            cookie = {
                'name': c['name'],
                'value': c['value'],
                'domain': c.get('domain', '.lululemon.com'),
                'path': c.get('path', '/'),
            }
            if 'sameSite' in c and c['sameSite'] in ['Strict', 'Lax', 'None']:
                cookie['sameSite'] = c['sameSite']
            self.cookies.append(cookie)
        
        print(f"Loaded {len(self.cookies)} cookies", flush=True)
    
    def load_urls(self, category):
        csv_path = os.path.join(self.categories_folder, f"{category}.csv")
        urls = []
        
        if not os.path.exists(csv_path):
            return urls
        
        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            next(reader, None)
            urls = [row[0] for row in reader if row]
        
        return urls
    
    async def block_resources(self, route):
        if route.request.resource_type in ['image', 'media', 'font', 'stylesheet']:
            await route.abort()
            return
        
        url = route.request.url.lower()
        blocked = [
            'google-analytics', 'googletagmanager', 'facebook.net', 
            'doubleclick', 'segment.', 'hotjar', 'mixpanel',
            '.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg',
            '.woff', '.woff2', '.ttf', '.mp4', '.webm'
        ]
        
        for pattern in blocked:
            if pattern in url:
                await route.abort()
                return
        
        await route.continue_()
    
    async def download_page(self, context, url, output_folder, semaphore):
        product_id = url.rstrip('/').split('/')[-1]
        output_file = os.path.join(output_folder, f"{product_id}.html")
        
        async with semaphore:
            page = None
            for attempt in range(2):
                try:
                    page = await context.new_page()
                    
                    response = await page.goto(url, wait_until='domcontentloaded', timeout=25000)
                    
                    if not response or response.status >= 400:
                        raise Exception(f"HTTP {response.status if response else 'none'}")
                    
                    # Wait for React hydration
                    try:
                        await page.wait_for_selector('script#__NEXT_DATA__', timeout=8000)
                    except:
                        pass
                    
                    try:
                        await page.wait_for_selector('[class*="product"]', timeout=5000)
                    except:
                        pass
                    
                    await asyncio.sleep(0.5)
                    
                    # Get rendered DOM
                    html = await page.content()
                    
                    if len(html) < 5000:
                        raise Exception(f"Too small ({len(html)} bytes)")
                    
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(html)
                    
                    self.stats['downloaded'] += 1
                    
                    if self.stats['downloaded'] % 20 == 0:
                        print(f"  Progress: {self.stats['downloaded']}/{self.stats['total']}", flush=True)
                    
                    await page.close()
                    return True
                    
                except Exception as e:
                    if page:
                        try:
                            await page.close()
                        except:
                            pass
                    
                    if attempt == 0:
                        await asyncio.sleep(1 + random.random())
                        continue
                    else:
                        self.stats['failed'] += 1
                        if self.stats['failed'] <= 10:
                            print(f"  Error {product_id}: {str(e)[:40]}", flush=True)
                        return False
            
            return False
    
    async def download_category(self, browser, category, urls):
        if not urls:
            return
        
        output_folder = os.path.join(self.data_folder, category)
        if os.path.exists(output_folder):
            for f in os.listdir(output_folder):
                fp = os.path.join(output_folder, f)
                if os.path.isfile(fp):
                    os.remove(fp)
        os.makedirs(output_folder, exist_ok=True)
        
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            java_script_enabled=True,
        )
        await context.add_cookies(self.cookies)
        await context.route('**/*', self.block_resources)
        
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        tasks = [
            self.download_page(context, url, output_folder, semaphore)
            for url in urls
        ]
        
        await asyncio.gather(*tasks)
        await context.close()
    
    async def run(self):
        print("\n" + "=" * 50, flush=True)
        print("Product Page Downloader", flush=True)
        print("=" * 50, flush=True)
        
        self.load_cookies()
        
        categories = ['women', 'men', 'accessories', 'supplies']
        category_urls = {}
        
        for cat in categories:
            urls = self.load_urls(cat)
            category_urls[cat] = urls
            self.stats['total'] += len(urls)
            print(f"  {cat}: {len(urls)} products", flush=True)
        
        print(f"\nTotal: {self.stats['total']} products", flush=True)
        
        start_time = datetime.now()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--headless=new',
                    '--disable-gpu',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                ]
            )
            
            print(f"\nBrowser ready ({self.max_concurrent} concurrent)", flush=True)
            
            for cat in categories:
                urls = category_urls[cat]
                if urls:
                    print(f"\n{cat.upper()} ({len(urls)} pages)", flush=True)
                    await self.download_category(browser, cat, urls)
            
            await browser.close()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        print("\n" + "=" * 50, flush=True)
        print("COMPLETE", flush=True)
        print(f"Downloaded: {self.stats['downloaded']}/{self.stats['total']}", flush=True)
        if self.stats['failed'] > 0:
            print(f"Failed: {self.stats['failed']}", flush=True)
        print(f"Time: {duration:.0f}s ({duration/60:.1f} min)", flush=True)
        if self.stats['downloaded'] > 0:
            print(f"Speed: {self.stats['downloaded']/duration:.1f} pages/sec", flush=True)
        print("=" * 50, flush=True)


async def main():
    import sys
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    max_concurrent = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    
    downloader = ProductDownloader(
        cookies_file=os.path.join(script_dir, "data/cookie/cookie.json"),
        categories_folder=os.path.join(script_dir, "data/categories"),
        data_folder=os.path.join(script_dir, "data"),
        max_concurrent=max_concurrent
    )
    
    await downloader.run()


if __name__ == "__main__":
    asyncio.run(main())
