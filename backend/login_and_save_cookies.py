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
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementNotInteractableException,
    ElementClickInterceptedException,
    WebDriverException,
)
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

AUTH_COOKIE_NAMES = {
    "wholesale_strategic_sales",
    "JSESSIONID",
    "Route_SSSAuth",
    "frontastic-session",
}


def _find_first_element(driver, selectors, timeout=15):
    """Try multiple selectors and return the first matching element."""
    end_time = time.time() + timeout
    while time.time() < end_time:
        for by, selector in selectors:
            try:
                element = driver.find_element(by, selector)
                if element:
                    return element
            except Exception:
                continue
        time.sleep(0.25)
    return None


def _looks_like_auth_url(url):
    """Check if URL appears to be an auth/login page."""
    lowered = (url or "").lower()
    return any(token in lowered for token in ["login", "signin", "sign-in", "auth", "oauth", "sso"])


def _has_login_form(driver):
    """Detect presence of visible login form fields."""
    try:
        login_fields = driver.find_elements(
            By.CSS_SELECTOR,
            "input[type='password'], input#password, input[name='password']"
        )
        for field in login_fields:
            if field.is_displayed():
                return True
    except Exception:
        pass
    return False


def _has_auth_cookie(driver):
    """Check for expected auth/session cookies."""
    try:
        cookies = driver.get_cookies()
        for cookie in cookies:
            if cookie.get("name") in AUTH_COOKIE_NAMES and cookie.get("value"):
                return True
    except Exception:
        pass
    return False


def _type_into_field(driver, selectors, value, field_name, timeout=20):
    """Reliably type into an input field with retries and JS fallback."""
    deadline = time.time() + timeout
    last_error = None

    while time.time() < deadline:
        element = _find_first_element(driver, selectors, timeout=2)
        if not element:
            time.sleep(0.3)
            continue

        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        except Exception:
            pass

        try:
            WebDriverWait(driver, 3).until(lambda d: element.is_displayed() and element.is_enabled())
            element.click()
            element.clear()
            element.send_keys(value)

            typed_value = (element.get_attribute("value") or "").strip()
            if typed_value:
                return True
        except (StaleElementReferenceException, ElementNotInteractableException, ElementClickInterceptedException, WebDriverException) as exc:
            last_error = exc

        # JS fallback when normal input fails in headless mode
        try:
            fresh_element = _find_first_element(driver, selectors, timeout=1)
            if not fresh_element:
                time.sleep(0.2)
                continue
            driver.execute_script(
                "arguments[0].focus(); arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
                fresh_element,
                value,
            )
            typed_value = (fresh_element.get_attribute("value") or "").strip()
            if typed_value:
                return True
        except Exception as exc:
            last_error = exc

        time.sleep(0.4)

    if last_error:
        print(f"✗ Failed to type into {field_name}: {type(last_error).__name__}: {last_error}")
    else:
        print(f"✗ Failed to type into {field_name}: field not found or not interactable")
    return False


def _click_submit(driver, selectors, fallback_element=None, timeout=10):
    """Reliably click submit button with fallbacks."""
    deadline = time.time() + timeout
    last_error = None

    while time.time() < deadline:
        button = _find_first_element(driver, selectors, timeout=1)
        if button:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
            except Exception:
                pass

            try:
                if button.is_displayed() and button.is_enabled():
                    button.click()
                    return True
            except (StaleElementReferenceException, ElementNotInteractableException, ElementClickInterceptedException, WebDriverException) as exc:
                last_error = exc

            try:
                driver.execute_script("arguments[0].click();", button)
                return True
            except Exception as exc:
                last_error = exc

        time.sleep(0.3)

    if fallback_element is not None:
        try:
            fallback_element.submit()
            return True
        except Exception as exc:
            last_error = exc

    if last_error:
        print(f"✗ Failed to click submit: {type(last_error).__name__}: {last_error}")
    return False

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
        # Wait for and find the email input field (with selector fallbacks)
        print("Looking for email input field...")
        email_selectors = [
            (By.ID, "email"),
            (By.NAME, "email"),
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.CSS_SELECTOR, "input[autocomplete='username']"),
            (By.CSS_SELECTOR, "input[name*='email' i]"),
        ]

        email_input = _find_first_element(driver, email_selectors, timeout=20)

        if not email_input:
            print("✗ Could not locate email input field")
            return False
        
        # Enter email
        print(f"Entering email: {EMAIL}")
        if not _type_into_field(driver, email_selectors, EMAIL, "email", timeout=15):
            return False
        
        # Find and enter password (no delay needed)
        print("Entering password...")
        password_selectors = [
            (By.ID, "password"),
            (By.NAME, "password"),
            (By.CSS_SELECTOR, "input[type='password']"),
            (By.CSS_SELECTOR, "input[autocomplete='current-password']"),
        ]

        password_input = _find_first_element(driver, password_selectors, timeout=10)

        if not password_input:
            print("✗ Could not locate password input field")
            return False

        if not _type_into_field(driver, password_selectors, PASSWORD, "password", timeout=12):
            return False
        
        # Find and click the login button
        print("Clicking login button...")
        submit_selectors = [
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.CSS_SELECTOR, "input[type='submit']"),
            (By.XPATH, "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'sign in') or contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'log in') or contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'login')]")
        ]

        if not _click_submit(driver, submit_selectors, fallback_element=password_input, timeout=10):
            return False
        
        # Wait for login state to settle (URL/auth cookie/login form disappearance)
        print("Waiting for login to complete...")
        WebDriverWait(driver, 30).until(
            lambda d: (
                _has_auth_cookie(d)
                or (not _has_login_form(d) and not _looks_like_auth_url(d.current_url))
            )
        )
        
        # Brief wait to ensure page loads completely
        time.sleep(3)
        
        # CRITICAL: Validate actual login success
        print("Validating login success...")
        
        # Check for visible error messages
        try:
            error_elements = driver.find_elements(By.CSS_SELECTOR, ".error, .alert-danger, [class*='error'], [class*='Error']")
            if error_elements:
                for elem in error_elements:
                    if not elem.is_displayed():
                        continue
                    error_text = elem.text.strip()
                    if error_text and any(token in error_text.lower() for token in ["invalid", "incorrect", "locked", "suspended", "failed", "try again"]):
                        print(f"✗ Login error detected: {error_text}")
                        return False
        except:
            pass
        
        # Check if we're still on login page
        current_url = driver.current_url.lower()
        if _looks_like_auth_url(current_url) and _has_login_form(driver) and not _has_auth_cookie(driver):
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
        
        # Final validation: authenticated cookie OR off-auth URL with no login form
        if not (_has_auth_cookie(driver) or (not _has_login_form(driver) and not _looks_like_auth_url(driver.current_url))):
            print(f"✗ Login validation failed - unable to confirm authenticated state")
            print(f"Current URL: {driver.current_url}")
            print(f"Page title: {driver.title}")
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
        print(f"✗ Error during login: {type(e).__name__}: {e}")
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

        # Optimized waiting: poll the DOM and source for product links (handles lazy loading/site changes).
        print("    ⏳ Waiting for products to render (progressive polling)...")
        product_links = set()
        product_pattern = re.compile(r'^/p/[^/]+/[^/?#]+$')
        page_source_pattern = re.compile(r'["\'](/p/[^"\'?#\s]+(?:/[^"\'?#\s]+)?)(?:["\'?#])', re.IGNORECASE)
        view_more_selectors = [
            (By.CSS_SELECTOR, "button[data-testid='cdp-pagination__view-more-products_test-id']"),
            (By.XPATH, "//button[contains(translate(normalize-space(.), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'VIEW MORE PRODUCTS')]")
        ]

        # Polling strategy: check every 1s up to a reasonable timeout based on total_count
        # fast path: timeout = min(60, 5 + total_count // 5)
        timeout_secs = min(60, 5 + total_count // 5)
        start_ts = time.time()
        last_count = 0

        while True:
            # Trigger lazy loading by scrolling through the page
            try:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.5);")
                time.sleep(0.2)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            except Exception:
                pass

            # If page still paginates with "VIEW MORE PRODUCTS", click until exhausted.
            # Some category pages ignore large `limit` values and require progressive loading.
            try:
                view_more_clicked = False
                for by, selector in view_more_selectors:
                    buttons = driver.find_elements(by, selector)
                    for button in buttons:
                        try:
                            if not button.is_displayed() or not button.is_enabled():
                                continue
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                            time.sleep(0.15)
                            button.click()
                            view_more_clicked = True
                            time.sleep(0.8)
                            break
                        except Exception:
                            continue
                    if view_more_clicked:
                        break
            except Exception:
                pass

            # Use JavaScript to quickly collect hrefs from anchors (faster than many selenium calls)
            try:
                js = (
                    "Array.from(document.querySelectorAll('a.product-tile_productTileLink__SW_Jh[href*=\"/p/\"], a[href*=\"/p/\"]')).map(a => a.getAttribute('href')).filter(Boolean)"
                )
                hrefs = driver.execute_script(f"return {js};")
            except Exception:
                hrefs = []

            # Fallback: parse product links from raw HTML/JSON payloads when anchors are not yet attached
            try:
                source = driver.page_source or ""
                source_matches = page_source_pattern.findall(source)
            except Exception:
                source_matches = []

            if source_matches:
                hrefs.extend(source_matches)

            # Normalize and filter
            found_before = len(product_links)
            for href in hrefs:
                try:
                    if not href:
                        continue

                    if 'wholesale.lululemon.com' in href:
                        path = href.split('wholesale.lululemon.com')[-1].split('?')[0].split('#')[0]
                    else:
                        path = href.split('?')[0].split('#')[0]

                    # Normalize non-root matches like p/slug/id
                    if path.startswith('p/'):
                        path = f'/{path}'

                    if product_pattern.match(path):
                        full_url = f"https://wholesale.lululemon.com{path}" if path.startswith('/') else href
                        product_links.add(full_url)
                except Exception:
                    continue

            current_count = len(product_links)
            # If we've reached expected total_count, or count isn't growing and we've passed a short stable window, break
            elapsed = time.time() - start_ts
            if current_count >= total_count:
                print(f"    ✓ Reached expected product count: {current_count}")
                break
            if current_count == last_count and elapsed > max(8, timeout_secs // 3):
                # no progress in a stable window; assume loaded
                print(f"    ⚠ Product count stabilized at {current_count} after {int(elapsed)}s")
                break

            if elapsed > timeout_secs:
                print(f"    ⚠ Timeout waiting for products after {int(elapsed)}s (found {current_count})")
                break

            last_count = current_count
            # Adaptive sleep: shorter when early, slightly longer when close to expected
            sleep_for = 0.8 if current_count < total_count // 2 else 1.2
            time.sleep(sleep_for)

        print(f"    📦 Collected {len(product_links)} candidate links")

        # Final fallback once more from full source if still empty
        if not product_links:
            try:
                source = driver.page_source or ""
                source_matches = page_source_pattern.findall(source)
                for raw_path in source_matches:
                    path = raw_path.split('?')[0].split('#')[0]
                    if path.startswith('p/'):
                        path = f'/{path}'
                    if product_pattern.match(path):
                        product_links.add(f"https://wholesale.lululemon.com{path}")
            except Exception:
                pass

        if not product_links:
            print("    ⚠ No product links found. Page structure may have changed or content is blocked for this session.")

        # Final dedupe and sanity-check: ensure the number doesn't exceed total_count wildly
        if len(product_links) > total_count * 3:
            # Something's off (duplicates or nav links slipped through). Trim by unique paths.
            print(f"    ⚠ Unusually high link count ({len(product_links)}), applying stricter filter")
            filtered = set()
            for url in product_links:
                try:
                    path = url.split('wholesale.lululemon.com')[-1].split('?')[0].split('#')[0]
                    if product_pattern.match(path):
                        filtered.add(f"https://wholesale.lululemon.com{path}" if path.startswith('/') else url)
                except Exception:
                    continue
            product_links = filtered

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
    print("\n" + "="*60)
    print("Updating links.csv with detected product counts...")
    print("="*60)
    
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
        print(f"  ✓ {data['display_name']}: limit={count}")
    
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
