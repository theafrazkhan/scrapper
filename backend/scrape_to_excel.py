#!/usr/bin/env python3
"""
Direct Scraper to Excel - Optimized for fast internet + limited server resources.
Low memory footprint, fast page loads, direct to Excel.
"""

import csv
import json
import os
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_CONCURRENT = 5  # Low concurrency for limited resources
PAGE_TIMEOUT = 20000  # 20s - fast internet should load quickly
ROW_HEIGHT = 80
USE_IMAGE_FORMULA = True


def extract_product_image(soup):
    img_tag = soup.find('img', class_='image_image__ECDWj')
    if img_tag:
        srcset = img_tag.get('srcset', '')
        if srcset:
            for source in srcset.split(','):
                parts = source.strip().split(' ')
                if len(parts) >= 2 and parts[0].startswith('http'):
                    if '1280w' in parts[1] or '1080w' in parts[1]:
                        return parts[0]
            for source in srcset.split(','):
                parts = source.strip().split(' ')
                if parts and parts[0].startswith('http'):
                    return parts[0]
        src = img_tag.get('src', '')
        if src and src.startswith('http'):
            return src
    return ''


def extract_color_swatches(soup):
    swatches = []
    container = soup.find('div', class_='color-swatches-selector_colorSwatchContainer__fjw54')
    if container:
        for img in container.find_all('img', class_='color-swatch_colorSwatchImg__apmdW'):
            name = img.get('alt', 'Unknown')
            url = img.get('src', '')
            if not url.startswith('http'):
                srcset = img.get('srcset', '')
                for src in srcset.split(','):
                    parts = src.strip().split(' ')
                    if parts and parts[0].startswith('http'):
                        url = parts[0]
                        break
            if url.startswith('http'):
                swatches.append({'name': name, 'url': url})
    return swatches


def extract_inventory(soup):
    inventory = {}
    for accordion in soup.find_all('details', class_='inventory-grid_accordionItem__XXIck'):
        heading = accordion.find('span', class_='inventory-grid_accordionHeadingContent__oebUk')
        if not heading:
            continue
        color = heading.get_text(strip=True)
        table = accordion.find('table')
        if not table:
            continue
        items = []
        tbody = table.find('tbody')
        if tbody:
            for row in tbody.find_all('tr'):
                size_span = row.find('span', class_='inventory-grid-table_size__5wMgv')
                if not size_span:
                    continue
                size = size_span.get_text(strip=True)
                qty = 0
                for q in row.find_all('span', class_='inventory-grid-table_quantity__Q0EiU'):
                    try:
                        qty += int(q.get_text(strip=True))
                    except:
                        pass
                inputs = row.find_all('input', {'name': True})
                sku = inputs[0].get('name') if inputs else None
                items.append({'size': size, 'sku': sku, 'available_quantity': qty, 'in_stock': qty > 0})
        inventory[color] = items
    return inventory


def extract_product_data(html):
    soup = BeautifulSoup(html, 'html.parser')
    script = soup.find('script', {'id': '__NEXT_DATA__'})
    if not script:
        return None, None, None, None
    try:
        data = json.loads(script.string)
        product = data['props']['pageProps']['data']['pageFolder']['dataSourceConfigurations'][0]['preloadedValue']['product']
    except:
        return None, None, None, None
    return product, extract_inventory(soup), extract_color_swatches(soup), extract_product_image(soup)


def setup_worksheet(ws, name):
    ws.title = name
    widths = {'A': 20, 'B': 30, 'C': 20, 'D': 25, 'E': 35, 'F': 15, 'G': 15, 'H': 20, 'I': 12, 'J': 12, 'K': 20, 'L': 12, 'M': 40, 'N': 25, 'O': 20}
    for col, w in widths.items():
        ws.column_dimensions[col].width = w
    
    headers = ["Product Image", "Product Name", "SKU", "colorSku", "sku name c", "Retail Price", "Wholesale Price", "color names", "Current Color Swatch", "Size", "quantity", "instock", "Description", "Slug", "product type"]
    fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    font = Font(bold=True, color="FFFFFF", size=12)
    border = Border(left=Side(style='medium'), right=Side(style='medium'), top=Side(style='medium'), bottom=Side(style='medium'))
    
    for i, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=i, value=h)
        cell.fill, cell.font, cell.alignment, cell.border = fill, font, Alignment(horizontal='center', vertical='center'), border
    ws.row_dimensions[1].height = 30


def add_row(ws, row, data):
    thin = Border(left=Side(style='thin', color='CCCCCC'), right=Side(style='thin', color='CCCCCC'), top=Side(style='thin', color='CCCCCC'), bottom=Side(style='thin', color='CCCCCC'))
    fill = PatternFill(start_color="E8F4F8" if row % 2 == 0 else "FFFFFF", end_color="E8F4F8" if row % 2 == 0 else "FFFFFF", fill_type="solid")
    
    if data.get('image') and USE_IMAGE_FORMULA:
        ws[f'A{row}'] = f'=IMAGE("{data["image"]}",1)'
        ws.row_dimensions[row].height = ROW_HEIGHT
    
    ws[f'B{row}'] = data.get('name', '')
    ws[f'C{row}'] = data.get('sku', '')
    ws[f'D{row}'] = data.get('color_sku', '')
    ws[f'E{row}'] = data.get('sku_name', '')
    ws[f'F{row}'] = data.get('retail', '')
    ws[f'G{row}'] = data.get('wholesale', '')
    ws[f'H{row}'] = data.get('color', '')
    
    if data.get('swatch_url') and USE_IMAGE_FORMULA:
        ws[f'I{row}'] = f'=IMAGE("{data["swatch_url"]}",1)'
    
    ws[f'J{row}'] = data.get('size', '')
    ws[f'K{row}'] = str(data.get('qty', 0))
    ws[f'L{row}'] = 'Yes' if data.get('in_stock') else 'No'
    ws[f'M{row}'] = data.get('description', '')
    ws[f'N{row}'] = data.get('slug', '')
    ws[f'O{row}'] = data.get('product_type', '')
    
    for cell in ws[row]:
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = thin
        cell.fill = fill


def add_product(ws, row, product, inventory, swatches, image):
    v = product.get('variants', [{}])[0]
    attr = v.get('attributes', {})
    
    base = {
        'name': product.get('name', ''),
        'sku': v.get('sku', ''),
        'sku_name': attr.get('skuName', ''),
        'retail': f"${product.get('retailPriceRange', ['0'])[0]}",
        'wholesale': f"${product.get('wholesalePriceRange', ['0'])[0]}",
        'description': v.get('designIntent', ''),
        'slug': product.get('slug', ''),
        'product_type': ', '.join(attr.get('productType', [])) if isinstance(attr.get('productType'), list) else attr.get('productType', ''),
        'image': image
    }
    
    if inventory:
        for color, items in inventory.items():
            swatch_url = ''
            for s in swatches:
                if s['name'].lower() == color.lower():
                    swatch_url = s['url']
                    break
            
            for item in items:
                data = {**base, 'color': color, 'swatch_url': swatch_url, 'size': item['size'], 'qty': item['available_quantity'], 'in_stock': item['in_stock']}
                if item.get('sku'):
                    data['sku'] = item['sku']
                    data['color_sku'] = f"{item['sku']}-{color.lower().replace(' ', '')}"
                add_row(ws, row, data)
                row += 1
    else:
        add_row(ws, row, {**base, 'color': attr.get('colourName', ''), 'size': '', 'qty': 0, 'in_stock': False})
        row += 1
    
    return row


class Scraper:
    def __init__(self, cookies_file, categories_folder, output_folder):
        self.cookies_file = cookies_file
        self.categories_folder = categories_folder
        self.output_folder = output_folder
        self.cookies = []
        self.data = {}
        self.stats = {'done': 0, 'fail': 0, 'total': 0}
    
    def load_cookies(self):
        with open(self.cookies_file) as f:
            for c in json.load(f):
                cookie = {'name': c['name'], 'value': c['value'], 'domain': c.get('domain', '.lululemon.com'), 'path': c.get('path', '/')}
                if c.get('sameSite') in ['Strict', 'Lax', 'None']:
                    cookie['sameSite'] = c['sameSite']
                self.cookies.append(cookie)
    
    def load_urls(self, cat):
        path = os.path.join(self.categories_folder, f"{cat}.csv")
        if not os.path.exists(path):
            return []
        with open(path) as f:
            reader = csv.reader(f)
            next(reader, None)
            return [r[0] for r in reader if r]
    
    async def scrape_page(self, context, url, cat, sem):
        pid = url.rstrip('/').split('/')[-1]
        async with sem:
            page = None
            try:
                page = await context.new_page()
                
                # Block heavy resources
                await page.route('**/*', lambda r: r.abort() if r.request.resource_type in ['image', 'media', 'font', 'stylesheet'] or any(p in r.request.url.lower() for p in ['analytics', 'facebook', 'google', '.png', '.jpg', '.woff']) else r.continue_())
                
                # Fast load
                await page.goto(url, wait_until='domcontentloaded', timeout=PAGE_TIMEOUT)
                
                # Quick wait for data
                try:
                    await page.wait_for_selector('script#__NEXT_DATA__', timeout=8000)
                except:
                    pass
                
                html = await page.content()
                await page.close()
                
                product, inv, swatches, img = extract_product_data(html)
                if product:
                    self.data[cat].append((product, inv, swatches, img))
                    self.stats['done'] += 1
                    if self.stats['done'] % 25 == 0:
                        print(f"  Progress: {self.stats['done']}/{self.stats['total']}", flush=True)
                    return True
                
                self.stats['fail'] += 1
                return False
                
            except Exception as e:
                self.stats['fail'] += 1
                if self.stats['fail'] <= 5:
                    print(f"  Skip {pid}: {str(e)[:30]}", flush=True)
                if page:
                    try: await page.close()
                    except: pass
                return False
    
    async def run(self):
        print("\n" + "=" * 50, flush=True)
        print("  SCRAPE TO EXCEL", flush=True)
        print("  Optimized for fast internet + low resources", flush=True)
        print("=" * 50, flush=True)
        
        self.load_cookies()
        print(f"\nCookies: {len(self.cookies)}", flush=True)
        
        cats = ['women', 'men', 'accessories', 'supplies']
        urls = {}
        for c in cats:
            urls[c] = self.load_urls(c)
            self.stats['total'] += len(urls[c])
            print(f"  {c}: {len(urls[c])}", flush=True)
        
        print(f"\nTotal: {self.stats['total']} products", flush=True)
        start = datetime.now()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--headless=new', '--disable-gpu', '--no-sandbox', '--disable-dev-shm-usage'])
            print(f"\nBrowser ready ({MAX_CONCURRENT} concurrent)", flush=True)
            
            for cat in cats:
                if not urls[cat]:
                    continue
                print(f"\n{cat.upper()} ({len(urls[cat])})", flush=True)
                self.data[cat] = []
                
                ctx = await browser.new_context(java_script_enabled=True)
                await ctx.add_cookies(self.cookies)
                
                sem = asyncio.Semaphore(MAX_CONCURRENT)
                await asyncio.gather(*[self.scrape_page(ctx, u, cat, sem) for u in urls[cat]])
                await ctx.close()
            
            await browser.close()
        
        # Write Excel
        print("\nWriting Excel...", flush=True)
        wb = Workbook()
        first = True
        for cat in cats:
            if not self.data.get(cat):
                continue
            ws = wb.active if first else wb.create_sheet()
            first = False
            setup_worksheet(ws, cat.capitalize())
            row = 2
            for product, inv, swatches, img in self.data[cat]:
                row = add_product(ws, row, product, inv, swatches, img)
            print(f"  {cat}: {len(self.data[cat])} products", flush=True)
        
        os.makedirs(self.output_folder, exist_ok=True)
        out = os.path.join(self.output_folder, f"lululemon_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        wb.save(out)
        
        dur = (datetime.now() - start).total_seconds()
        print(f"\n" + "=" * 50, flush=True)
        print(f"DONE! {self.stats['done']}/{self.stats['total']} in {dur:.0f}s", flush=True)
        if self.stats['fail']:
            print(f"Failed: {self.stats['fail']}", flush=True)
        print(f"Speed: {self.stats['done']/dur:.1f}/sec", flush=True)
        print(f"File: {out}", flush=True)
        print("=" * 50, flush=True)


async def main():
    import sys
    s = Scraper(
        os.path.join(SCRIPT_DIR, "data/cookie/cookie.json"),
        os.path.join(SCRIPT_DIR, "data/categories"),
        os.path.join(SCRIPT_DIR, "data/results")
    )
    await s.run()

if __name__ == "__main__":
    asyncio.run(main())
