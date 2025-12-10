"""
Script to automate login to Lululemon wholesale portal and save cookies.
This script uses Selenium to handle the login process and save authentication cookies.
It also extracts product counts from category pages and updates links.csv.

Note: Credentials are now fetched from database instead of .env file
"""

import json
import os
import sys
import time
import re
import csv
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Import database credentials utility
try:
    from db_credentials import get_credentials, update_last_used
except ImportError:
    print("Error: Cannot import db_credentials module")
    print("Make sure db_credentials.py exists in the backend folder")
    raise

# Configuration
SCRIPT_DIR = Path(__file__).parent
LOGIN_URL = "https://wholesale.lululemon.com/"

# Get credentials from database
EMAIL, PASSWORD = get_credentials()

# Validate credentials
if not EMAIL or not PASSWORD:
    raise ValueError(
        "Missing credentials! Please add Lululemon credentials through the web dashboard:\n"
        "1. Login to the web interface\n"
        "2. Go to Settings\n"
        "3. Add your Lululemon wholesale credentials"
    )

COOKIE_FILE = SCRIPT_DIR / "data" / "cookie" / "cookie.json"
LINKS_FILE = SCRIPT_DIR / "data" / "links.csv"

# Base URL - categories will be discovered dynamically
BASE_URL = "https://wholesale.lululemon.com"

def setup_driver():
    """Set up Chrome WebDriver with appropriate options."""
    print("Setting up Chrome WebDriver...")
    chrome_options = Options()
    
    # Run in headless mode (no browser window) - perfect for servers
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    chrome_options.add_argument('--window-size=1920,1080')
    
    # Disable automation flags
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    try:
        # Check if we're in Docker (has system chromium)
        chrome_bin = os.environ.get('CHROME_BIN')
        chromedriver_path = os.environ.get('CHROMEDRIVER_PATH')
        
        if chrome_bin and os.path.exists(chrome_bin):
            # Use system-installed Chromium (Docker)
            print(f"Using system Chromium: {chrome_bin}")
            chrome_options.binary_location = chrome_bin
            
            if chromedriver_path and os.path.exists(chromedriver_path):
                print(f"Using system ChromeDriver: {chromedriver_path}")
                service = Service(chromedriver_path)
            else:
                # Try default path
                service = Service('/usr/bin/chromedriver')
        else:
            # Use webdriver_manager to automatically download and manage chromedriver
            print("Installing/updating ChromeDriver...")
            service = Service(ChromeDriverManager().install())
        
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        print("✓ Chrome WebDriver initialized successfully")
        return driver
    except Exception as e:
        print(f"❌ Error setting up Chrome WebDriver: {e}")
        print("Make sure Chrome/Chromium is installed on your system")
        raise

def login_to_wholesale(driver):
    """Navigate to the login page and perform login."""
    print(f"Navigating to {LOGIN_URL}...")
    driver.get(LOGIN_URL)
    
    try:
        # Wait for and find the email input field (page load implicit)
        print("Looking for email input field...")
        email_input = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "email"))
        )
        
        # Enter email
        print(f"Entering email: {EMAIL}")
        email_input.clear()
        email_input.send_keys(EMAIL)
        
        # Find and enter password (no delay needed)
        print("Entering password...")
        password_input = driver.find_element(By.ID, "password")
        password_input.clear()
        password_input.send_keys(PASSWORD)
        
        # Find and click the login button
        print("Clicking login button...")
        login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_button.click()
        
        # Wait for login to complete - wait for URL to change or specific element to appear
        print("Waiting for login to complete...")
        WebDriverWait(driver, 20).until(
            lambda d: "wholesale.lululemon.com" in d.current_url and d.current_url != LOGIN_URL
        )
        
        # Brief wait to ensure page loads completely
        time.sleep(3)
        
        # CRITICAL: Validate actual login success
        print("Validating login success...")
        
        # Check for error messages
        try:
            error_elements = driver.find_elements(By.CSS_SELECTOR, ".error, .alert-danger, [class*='error'], [class*='Error']")
            if error_elements:
                for elem in error_elements:
                    error_text = elem.text.strip()
                    if error_text and len(error_text) > 0:
                        print(f"✗ Login error detected: {error_text}")
                        return False
        except:
            pass
        
        # Check if we're still on login page or redirected to error page
        current_url = driver.current_url.lower()
        if 'login' in current_url or 'signin' in current_url or 'error' in current_url:
            print(f"✗ Login failed - still on auth page: {current_url}")
            return False
        
        # Check for wholesale-specific elements that prove we're logged in
        try:
            # Try to find navigation menu or wholesale-specific elements
            wholesale_indicators = [
                (By.CSS_SELECTOR, "nav"),
                (By.CSS_SELECTOR, "[class*='navigation']"),
                (By.CSS_SELECTOR, "[class*='menu']"),
                (By.XPATH, "//a[contains(@href, 'wholesale')]"),
            ]
            
            found_indicator = False
            for by, selector in wholesale_indicators:
                try:
                    elements = driver.find_elements(by, selector)
                    if elements:
                        found_indicator = True
                        break
                except:
                    continue
            
            if not found_indicator:
                print("✗ Warning: Could not find wholesale navigation elements")
                print("   This might indicate login failure")
                
        except Exception as e:
            print(f"⚠ Warning: Could not verify wholesale elements: {e}")
        
        # Final validation: Check page title or content
        page_title = driver.title.lower()
        if 'error' in page_title or 'login' in page_title or 'sign in' in page_title:
            print(f"✗ Login failed - page title indicates error: {driver.title}")
            return False
        
        print("✓ Login successful!")
        print(f"Current URL: {driver.current_url}")
        print(f"Page title: {driver.title}")
        return True
        
    except TimeoutException as e:
        print(f"✗ Timeout during login: {e}")
        print(f"Current URL: {driver.current_url}")
        return False
    except NoSuchElementException as e:
        print(f"✗ Could not find login element: {e}")
        print(f"Current URL: {driver.current_url}")
        return False
    except Exception as e:
        print(f"✗ Error during login: {e}")
        print(f"Current URL: {driver.current_url}")
        return False

def discover_categories(driver):
    """Dynamically discover categories from the navigation menu."""
    print("\n[2/4] Discovering categories from navigation...")
    
    try:
        # Navigate to home page if not already there
        if driver.current_url == LOGIN_URL or "/login" in driver.current_url:
            driver.get(BASE_URL)
            # Wait for navigation to load (reduced from 3s to 1.5s)
            time.sleep(1.5)
        
        # Find the primary navigation with all category links
        # Look for: class="primary-nav_primaryNavAnchor__A22xB"
        nav_links = driver.find_elements(By.CSS_SELECTOR, "a.primary-nav_primaryNavAnchor__A22xB")
        
        categories = {}
        
        for link in nav_links:
            try:
                href = link.get_attribute('href')
                text = link.text.strip()
                
                if href and text:
                    # Extract category name from URL or link text
                    # URLs like: /lululemon/women, /lululemon/men, /whats-new
                    if '/lululemon/' in href:
                        # Standard category: women, men, accessories, supplies
                        category_name = href.split('/lululemon/')[-1].split('?')[0]
                    elif '/whats-new' in href:
                        # Special category: what's new
                        category_name = 'whats-new'
                    else:
                        continue
                    
                    # Make full URL if relative
                    if href.startswith('/'):
                        href = BASE_URL + href
                    
                    # Ensure it has the limit parameter (start with 12 to check count)
                    if 'limit=' not in href:
                        href += '?limit=12' if '?' not in href else '&limit=12'
                    else:
                        # Replace existing limit with 12
                        href = re.sub(r'limit=\d+', 'limit=12', href)
                    
                    categories[category_name] = {
                        'url': href,
                        'display_name': text
                    }
                    
                    print(f"  ✓ Found: {text} → {category_name}")
            except Exception as e:
                print(f"  ⚠ Error processing link: {e}")
                continue
        
        if not categories:
            print("  ⚠ No categories found, using fallback defaults")
            # Fallback to basic categories
            categories = {
                'women': {
                    'url': f'{BASE_URL}/lululemon/women?limit=12&pic=14ffd75b-6d75-49dd-8ea5-811f163e6c06&prc=a1eb736a-58d3-43fb-b99a-e435e30b5b4c',
                    'display_name': 'Women'
                },
                'men': {
                    'url': f'{BASE_URL}/lululemon/men?limit=12&pic=14ffd75b-6d75-49dd-8ea5-811f163e6c06&prc=a1eb736a-58d3-43fb-b99a-e435e30b5b4c',
                    'display_name': 'Men'
                },
                'accessories': {
                    'url': f'{BASE_URL}/lululemon/accessories?limit=12&pic=14ffd75b-6d75-49dd-8ea5-811f163e6c06&prc=a1eb736a-58d3-43fb-b99a-e435e30b5b4c',
                    'display_name': 'Accessories'
                },
                'supplies': {
                    'url': f'{BASE_URL}/lululemon/supplies?limit=12&pic=14ffd75b-6d75-49dd-8ea5-811f163e6c06&prc=a1eb736a-58d3-43fb-b99a-e435e30b5b4c',
                    'display_name': 'Supplies'
                }
            }
        
        print(f"\n  ✓ Discovered {len(categories)} categories: {', '.join(categories.keys())}")
        return categories
        
    except Exception as e:
        print(f"  ❌ Error discovering categories: {e}")
        # Return empty dict, will use fallback
        return {}

def extract_product_count_and_links(driver, category_name, url):
    """Navigate to a category page, extract the total product count, and extract all product links."""
    print(f"\n  📂 Processing {category_name}...")
    
    # Step 1: Load initial page with limit=12 to detect count
    initial_url = re.sub(r'limit=\d+', 'limit=12', url) if 'limit=' in url else (url + '?limit=12' if '?' not in url else url + '&limit=12')
    print(f"    ⏳ Loading initial page...")
    driver.get(initial_url)
    
    try:
        # Wait for the product count element to appear
        product_count_element = None
        total_count = None
        
        # Method 1: Look for the specific paragraph with class
        try:
            product_count_element = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "p.lll-type-label-medium"))
            )
        except:
            pass
        
        # Method 2: Look for any paragraph with the pattern
        if not product_count_element:
            try:
                product_count_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//p[contains(text(), 'Showing') and contains(text(), 'of') and contains(text(), 'items')]"))
                )
            except:
                pass
        
        if product_count_element:
            text = product_count_element.text
            print(f"    📊 Found: '{text}'")
            
            # Extract the total count using regex: "Showing X of Y items"
            match = re.search(r'Showing\s+\d+\s+of\s+(\d+)\s+items?', text, re.IGNORECASE)
            if match:
                total_count = int(match.group(1))
                print(f"    ✓ Detected {total_count} total products")
        
        if not total_count:
            print(f"    ⚠ Could not detect count, using default=500")
            total_count = 500
        
        # Step 2: Reload page with full limit
        full_url = re.sub(r'limit=\d+', f'limit={total_count}', url) if 'limit=' in url else (url + f'?limit={total_count}' if '?' not in url else url + f'&limit={total_count}')
        print(f"    ⏳ Loading all {total_count} products...")
        driver.get(full_url)
        
        # CRITICAL: Wait longer for heavy pages to load all products
        # Dynamic wait: more products = more wait time
        if total_count > 200:
            wait_time = 30  # 30 seconds for 200+ products
        elif total_count > 100:
            wait_time = 20  # 20 seconds for 100+ products
        else:
            wait_time = 15  # 15 seconds for <100 products
        
        print(f"    ⏳ Waiting {wait_time}s for all products to render...")
        time.sleep(wait_time)
        
        # Step 3: Extract all product links from the page
        print(f"    🔍 Extracting product links...")
        product_links = set()
        
        # Find all <a> tags with href containing "/p/"
        link_elements = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/p/"]')
        print(f"    📦 Found {len(link_elements)} link elements in DOM")
        
        # Filter to only valid product links with pattern: /p/{name}/{id}
        product_pattern = re.compile(r'^/p/[^/]+/[^/?#]+$')
        
        for link_elem in link_elements:
            try:
                href = link_elem.get_attribute('href')
                if href:
                    # Extract path from full URL
                    if 'wholesale.lululemon.com' in href:
                        path = href.split('wholesale.lululemon.com')[-1].split('?')[0].split('#')[0]
                    else:
                        path = href.split('?')[0].split('#')[0]
                    
                    # Check if it matches product URL pattern
                    if product_pattern.match(path):
                        full_url = f"https://wholesale.lululemon.com{path}" if path.startswith('/') else href
                        product_links.add(full_url)
            except:
                continue
        
        print(f"    ✓ Extracted {len(product_links)} unique product links")
        
        return {
            'count': total_count,
            'links': product_links
        }
        
    except Exception as e:
        print(f"    ❌ Error processing {category_name}: {e}")
        return {
            'count': 500,
            'links': set()
        }

def save_category_links_to_csv(category_name, product_links):
    """Save product links for a category to a CSV file."""
    # Create categories folder if it doesn't exist
    categories_folder = SCRIPT_DIR / "data" / "categories"
    categories_folder.mkdir(parents=True, exist_ok=True)
    
    output_file = categories_folder / f"{category_name}.csv"
    sorted_links = sorted(list(product_links))
    
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Product URL'])
            for link in sorted_links:
                writer.writerow([link])
        
        print(f"    💾 Saved to: {output_file.name}")
        return True
    except Exception as e:
        print(f"    ❌ Error saving CSV: {e}")
        return False

def update_links_file(category_counts):
    """Update the links.csv file with the correct product limits."""
    print("\n[4/4] Updating links.csv file...")
    
    # Create directory if it doesn't exist
    LINKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Build updated URLs
    updated_urls = []
    for category_name, data in category_counts.items():
        url = data['url']
        count = data['count']
        
        # Replace limit=12 with the actual count
        updated_url = re.sub(r'limit=\d+', f'limit={count}', url)
        updated_urls.append(updated_url)
        print(f"  - {category_name}: limit={count}")
    
    # Save to CSV file (overwrite if exists)
    with open(LINKS_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        for url in updated_urls:
            writer.writerow([url])
    
    print(f"\n✓ Links saved to: {LINKS_FILE}")

def save_cookies(driver, cookie_file):
    """Extract cookies from the driver and save them to a JSON file."""
    # Get all cookies
    cookies = driver.get_cookies()
    
    print(f"\nFound {len(cookies)} cookies")
    
    # Format cookies in the same structure as the existing cookie file
    formatted_cookies = []
    for cookie in cookies:
        formatted_cookie = {
            "domain": cookie.get("domain", ""),
            "hostOnly": "." not in cookie.get("domain", ""),
            "httpOnly": cookie.get("httpOnly", False),
            "name": cookie.get("name", ""),
            "path": cookie.get("path", "/"),
            "sameSite": cookie.get("sameSite", "unspecified"),
            "secure": cookie.get("secure", False),
            "session": cookie.get("expiry") is None,
            "storeId": "0",
            "value": cookie.get("value", "")
        }
        
        # Add expiry if it exists
        if "expiry" in cookie:
            formatted_cookie["expirationDate"] = cookie["expiry"]
        
        formatted_cookies.append(formatted_cookie)
    
    # Create directory if it doesn't exist
    cookie_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Save cookies to file
    with open(cookie_file, 'w') as f:
        json.dump(formatted_cookies, f, indent=2)
    
    print(f"✓ Cookies saved to: {cookie_file}")
    
    # Update last_used timestamp in database
    try:
        update_last_used()
    except Exception as e:
        print(f"Warning: Could not update credentials timestamp: {e}")
    
    # Print important cookies
    important_cookies = ["wholesale_strategic_sales", "JSESSIONID", "Route_SSSAuth", "frontastic-session"]
    print("\nImportant cookies found:")
    for cookie in formatted_cookies:
        if cookie["name"] in important_cookies:
            value_preview = cookie["value"][:50] + "..." if len(cookie["value"]) > 50 else cookie["value"]
            print(f"  - {cookie['name']}: {value_preview}")

def main():
    """Main function to orchestrate the login and cookie saving process."""
    print("=" * 60)
    print("Lululemon Wholesale Portal - Login & Cookie Extractor")
    print("=" * 60)
    
    driver = None
    try:
        # Set up the driver
        print("\n[1/4] Setting up Chrome WebDriver...")
        driver = setup_driver()
        
        # Perform login
        print("\n[Step 1/4] Logging in to wholesale portal...")
        login_success = login_to_wholesale(driver)
        
        if not login_success:
            print("\n" + "=" * 60)
            print("❌ LOGIN FAILED - ABORTING")
            print("=" * 60)
            print("\nPossible reasons:")
            print("  1. Incorrect email or password")
            print("  2. Account is locked or suspended")
            print("  3. Lululemon changed their login page structure")
            print("  4. Network connectivity issues")
            print("\nPlease:")
            print("  - Verify your credentials in Settings > Lululemon Login")
            print("  - Try logging in manually at https://wholesale.lululemon.com/")
            print("  - Check if your wholesale account is active")
            print("=" * 60)
            sys.exit(1)  # Exit with error code
        
        # Discover categories dynamically
        print("\n[Step 2/4] Discovering categories...")
        categories = discover_categories(driver)
        
        if not categories:
            print("\n✗ No categories discovered. Exiting.")
            sys.exit(1)
        
        # Extract product counts AND links from category pages (in same session!)
        print("\n[Step 3/4] Extracting product links from all categories...")
        print("  🔥 Using same browser session - already authenticated!")
        category_data = {}
        total_products = 0
        
        for category_name, cat_info in categories.items():
            result = extract_product_count_and_links(driver, cat_info['display_name'], cat_info['url'])
            
            category_data[category_name] = {
                'url': cat_info['url'],
                'count': result['count'],
                'display_name': cat_info['display_name']
            }
            
            # Save links to CSV immediately
            if result['links']:
                save_category_links_to_csv(category_name, result['links'])
                total_products += len(result['links'])
            else:
                print(f"    ⚠ No links extracted for {category_name}")
        
        print(f"\n  🎉 Total products extracted: {total_products}")
        
        # Save cookies
        print("\n[Step 4/4] Saving session cookies...")
        save_cookies(driver, COOKIE_FILE)
        
        # Update links.csv file with updated URLs
        print("\n[Step 4.5/4] Updating links.csv...")
        update_links_file(category_data)
        
        print("\n" + "=" * 60)
        print("✓ SUCCESS! All tasks completed.")
        print("=" * 60)
        print(f"\n📂 Cookie file: {os.path.abspath(COOKIE_FILE)}")
        print(f"📂 Links file: {os.path.abspath(LINKS_FILE)}")
        print(f"📂 Product CSVs: {os.path.abspath(SCRIPT_DIR / 'data' / 'categories')}/")
        print(f"\n🔗 Total products extracted: {total_products}")
        print("\n✅ You can now use these cookies and product lists with your download scripts.")

        
    except Exception as e:
        print(f"\n✗ An error occurred: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Close the browser
        if driver:
            print("\nClosing browser...")
            driver.quit()

if __name__ == "__main__":
    main()
