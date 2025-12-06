"""
Script to automate login to Lululemon wholesale portal and save cookies.
This script uses Selenium to handle the login process and save authentication cookies.
It also extracts product counts from category pages and updates links.csv.

Note: Credentials are now fetched from database instead of .env file
"""

import json
import os
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

# Category URLs (with limit=12 initially to check product count)
CATEGORY_URLS = {
    "women": "https://wholesale.lululemon.com/lululemon/women?limit=12&pic=14ffd75b-6d75-49dd-8ea5-811f163e6c06&prc=a1eb736a-58d3-43fb-b99a-e435e30b5b4c",
    "men": "https://wholesale.lululemon.com/lululemon/men?limit=12&pic=14ffd75b-6d75-49dd-8ea5-811f163e6c06&prc=a1eb736a-58d3-43fb-b99a-e435e30b5b4c",
    "accessories": "https://wholesale.lululemon.com/lululemon/accessories?limit=12&pic=14ffd75b-6d75-49dd-8ea5-811f163e6c06&prc=a1eb736a-58d3-43fb-b99a-e435e30b5b4c",
    "supplies": "https://wholesale.lululemon.com/lululemon/supplies?limit=12&pic=14ffd75b-6d75-49dd-8ea5-811f163e6c06&prc=a1eb736a-58d3-43fb-b99a-e435e30b5b4c"
}

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
    
    # Wait for page to load
    time.sleep(3)
    
    try:
        # Wait for and find the email input field
        print("Looking for email input field...")
        email_input = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "email"))
        )
        
        # Enter email
        print(f"Entering email: {EMAIL}")
        email_input.clear()
        email_input.send_keys(EMAIL)
        time.sleep(1)
        
        # Find and enter password
        print("Entering password...")
        password_input = driver.find_element(By.ID, "password")
        password_input.clear()
        password_input.send_keys(PASSWORD)
        time.sleep(1)
        
        # Find and click the login button
        print("Clicking login button...")
        login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_button.click()
        
        # Wait for login to complete - wait for URL to change or specific element to appear
        print("Waiting for login to complete...")
        WebDriverWait(driver, 20).until(
            lambda d: "wholesale.lululemon.com" in d.current_url and d.current_url != LOGIN_URL
        )
        
        # Additional wait to ensure all cookies are set
        time.sleep(5)
        
        print("✓ Login successful!")
        print(f"Current URL: {driver.current_url}")
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

def extract_product_count(driver, category_name, url):
    """Navigate to a category page and extract the total product count."""
    print(f"\n  Navigating to {category_name}...")
    driver.get(url)
    
    # Wait for the page to load
    time.sleep(5)
    
    try:
        # Look for the div with product count: "Showing 12 of 246 items"
        # Try multiple selectors
        product_count_element = None
        
        # Method 1: Look for the specific div with class
        try:
            product_count_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.bg-white.px-16.pt-16 p.lll-type-label-medium"))
            )
        except:
            pass
        
        # Method 2: Look for any paragraph with similar text pattern
        if not product_count_element:
            try:
                product_count_element = driver.find_element(By.XPATH, "//p[contains(text(), 'Showing') and contains(text(), 'of') and contains(text(), 'items')]")
            except:
                pass
        
        if product_count_element:
            text = product_count_element.text
            print(f"  Found text: {text}")
            
            # Extract the total count using regex: "Showing X of Y items"
            match = re.search(r'Showing\s+\d+\s+of\s+(\d+)\s+items', text)
            if match:
                total_count = int(match.group(1))
                print(f"  ✓ Total products in {category_name}: {total_count}")
                return total_count+10
        
        print(f"  ⚠ Could not extract product count for {category_name}, using default limit=12")
        return 12
        
    except Exception as e:
        print(f"  ⚠ Error extracting count for {category_name}: {e}")
        return 12

def update_links_file(category_counts):
    """Update the links.csv file with the correct product limits."""
    print("\n[4/4] Updating links.csv file...")
    
    # Create directory if it doesn't exist
    LINKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Build updated URLs
    updated_urls = []
    for category, count in category_counts.items():
        base_url = CATEGORY_URLS[category]
        # Replace limit=12 with the actual count
        updated_url = re.sub(r'limit=\d+', f'limit={count}', base_url)
        updated_urls.append(updated_url)
        print(f"  - {category}: limit={count}")
    
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
        print("\n[2/4] Logging in to wholesale portal...")
        if not login_to_wholesale(driver):
            print("\n✗ Login failed. Please check credentials and try again.")
            return
        
        # Save cookies
        print("\n[3/4] Saving cookies...")
        save_cookies(driver, COOKIE_FILE)
        
        # Extract product counts from category pages
        print("\n[4/4] Extracting product counts from category pages...")
        category_counts = {}
        for category_name, url in CATEGORY_URLS.items():
            count = extract_product_count(driver, category_name, url)
            category_counts[category_name] = count
        
        # Update links.csv file
        update_links_file(category_counts)
        
        print("\n" + "=" * 60)
        print("✓ SUCCESS! All tasks completed.")
        print("=" * 60)
        print(f"\nCookie file: {os.path.abspath(COOKIE_FILE)}")
        print(f"Links file: {os.path.abspath(LINKS_FILE)}")
        print("\nYou can now use these cookies and links with your download scripts.")
        
    except Exception as e:
        print(f"\n✗ An error occurred: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Close the browser
        if driver:
            print("\nClosing browser...")
            time.sleep(2)  # Brief pause before closing
            driver.quit()

if __name__ == "__main__":
    main()
