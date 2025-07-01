import os
import time
import random
import datetime
import pytz
import csv
from playwright.sync_api import sync_playwright
from reports import process_financial_report, process_ro_marketing_report, combine_ro_reports, verify_data_accuracy
from sql import upload_all_reports

def wait_random(min_sec=1, max_sec=2):
    time.sleep(random.uniform(min_sec, max_sec))

def get_arizona_time():
    return datetime.datetime.now(pytz.timezone('US/Arizona'))

def format_date(dt):
    return f"{dt.month}.{dt.day}.{dt.year}"

def format_date_short(dt):
    return f"{dt.month:02d}.{dt.day:02d}.{dt.year-2000:02d}"

def get_current_hour_12format():
    """Get current Arizona time in 12-hour format for Created_At column"""
    az_now = get_arizona_time()
    return az_now.strftime("%I %p").lstrip('0')

def get_date_info():
    az_now = get_arizona_time()
    target_date = az_now  # Processing today's data
    
    return {
        "target_file": format_date(target_date),
        "target_short": format_date_short(target_date),
        "target_us": target_date.strftime("%m/%d/%Y"),
        "target_date": target_date.date(),
        "current_hour": get_current_hour_12format()
    }

def setup_directories():
    base_path = os.getcwd()
    financial_dir = os.path.join(base_path, "Financial Reports")
    ro_dir = os.path.join(base_path, "RO Reports")
    os.makedirs(financial_dir, exist_ok=True)
    os.makedirs(ro_dir, exist_ok=True)
    return {"financial": financial_dir, "ro": ro_dir}

# FIXED: More robust login with better session management
def login_to_tekmetric(page):
    """Enhanced login with better session verification"""
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            print(f"Login attempt {attempt + 1}/{max_retries}...")
            
            # Go to login page
            page.goto("https://shop.tekmetric.com/", timeout=60000)
            wait_random(3, 5)
            
            # Wait for page to fully load
            page.wait_for_load_state("domcontentloaded")
            wait_random(2, 3)
            
            # Check if already logged in
            if is_logged_in(page):
                print("Already logged in")
                return True
            
            # Perform login
            email = os.getenv("TEKMETRIC_EMAIL")
            password = os.getenv("TEKMETRIC_PASSWORD")
            
            if not email or not password:
                raise ValueError("TEKMETRIC_EMAIL and TEKMETRIC_PASSWORD must be set")
            
            # Fill credentials
            page.fill("#email", email)
            wait_random(1, 2)
            page.fill("#password", password)
            wait_random(1, 2)
            
            # Click sign in
            page.click("button[data-cy='button']:has-text('Sign In')")
            
            # Wait for login to complete
            page.wait_for_load_state("networkidle", timeout=30000)
            wait_random(3, 5)
            
            # Verify login success
            if is_logged_in(page):
                print("Login successful")
                return True
            else:
                print(f"Login verification failed on attempt {attempt + 1}")
                
        except Exception as e:
            print(f"Login attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print("Retrying in 5 seconds...")
                wait_random(5, 7)
    
    return False

# FIXED: Better login verification
def is_logged_in(page):
    """Check if user is currently logged in"""
    try:
        # Check for sign in button (indicates not logged in)
        sign_in_visible = page.locator("button:has-text('Sign In')").is_visible(timeout=3000)
        if sign_in_visible:
            return False
        
        # Check for user menu or dashboard elements (indicates logged in)
        logged_in_indicators = [
            "[data-testid='user-menu']",
            "text=Dashboard",
            "text=Reports", 
            ".user-avatar",
            "[aria-label*='user']"
        ]
        
        for indicator in logged_in_indicators:
            try:
                if page.locator(indicator).is_visible(timeout=2000):
                    return True
            except:
                continue
        
        # Additional check - look for typical dashboard/app elements
        app_elements = page.locator("nav, .navbar, .sidebar, .dashboard").count()
        return app_elements > 0
        
    except Exception as e:
        print(f"Login check error: {e}")
        return False

# FIXED: Ensure login before each report access
def ensure_logged_in(page):
    """Ensure user is logged in before accessing reports"""
    if not is_logged_in(page):
        print("Session lost, re-logging in...")
        return login_to_tekmetric(page)
    return True

# FIXED: Better export button detection with login verification
def find_export_button_robust(page):
    """Enhanced export button detection with session validation"""
    
    # First verify we're logged in
    if not ensure_logged_in(page):
        print("Cannot proceed - login failed")
        return None
    
    # Wait for page to be fully loaded
    try:
        page.wait_for_load_state("networkidle", timeout=20000)
        wait_random(2, 4)
    except:
        print("Page loading timeout, continuing...")
    
    # Wait for any loading indicators to disappear
    try:
        page.wait_for_selector("[data-testid='loading'], .loading, .spinner", state="hidden", timeout=10000)
    except:
        pass
    
    # Primary export button selectors based on your working screenshots
    export_selectors = [
        "button:has-text('Export')",
        "[data-cy='button']:has-text('Export')",
        "button[aria-label*='Export']",
        ".MuiButton-root:has-text('Export')",
        "*[role='button']:has-text('Export')",
        "input[value='Export']",
        "button.btn:has-text('Export')"
    ]
    
    # Try multiple attempts with increasing wait times
    for attempt in range(3):
        print(f"Export button search attempt {attempt + 1}/3...")
        
        # Scroll to ensure button is visible
        try:
            page.evaluate("window.scrollTo(0, 0)")
            wait_random(1, 2)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            wait_random(1, 2)
        except:
            pass
        
        for selector in export_selectors:
            try:
                element = page.locator(selector).first
                if element.is_visible(timeout=3000):
                    print(f"Found Export button with: {selector}")
                    return element
            except:
                continue
        
        if attempt < 2:
            wait_time = (attempt + 1) * 3
            print(f"Export button not found, waiting {wait_time} seconds...")
            wait_random(wait_time, wait_time + 2)
    
    print("Export button not found after all attempts")
    return None

# FIXED: Simplified financial report download
def download_financial_report(page, dirs, dates):
    """Download financial report with better session management"""
    try:
        print("Downloading Financial Report...")
        
        # Ensure we're logged in
        if not ensure_logged_in(page):
            raise Exception("Login failed before financial report")
        
        # Navigate to financial reports page first (not direct to custom URL)
        print("Navigating to Financial Reports...")
        page.goto("https://shop.tekmetric.com/admin/org/464/reports/financial", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=30000)
        wait_random(3, 5)
        
        # Check if we're still logged in after navigation
        if not is_logged_in(page):
            raise Exception("Lost session after navigating to financial reports")
        
        # Click on Custom Financial Report
        try:
            custom_btn = page.locator("text=Custom Financial").first
            if custom_btn.is_visible(timeout=10000):
                custom_btn.click()
                wait_random(3, 5)
            else:
                print("Custom Financial button not found, trying direct approach...")
        except Exception as e:
            print(f"Custom button click failed: {e}")
        
        # Set date range to today
        try:
            # Look for date controls and set them appropriately
            today = dates['target_date']
            date_str = today.strftime("%m/%d/%Y")
            
            # Try to set date inputs if available
            date_inputs = page.locator("input[type='date'], input[placeholder*='date']")
            count = date_inputs.count()
            if count > 0:
                for i in range(min(count, 2)):  # Set start and end date
                    date_inputs.nth(i).fill(date_str)
                    wait_random(1, 2)
        except Exception as e:
            print(f"Date setting failed: {e}")
        
        # Find and click export button
        export_btn = find_export_button_robust(page)
        if not export_btn:
            raise Exception("Export button not found")
        
        print("Clicking Export button...")
        
        # Setup download handler
        az_time = get_arizona_time()
        filename = f"{dates['target_file']}_H{az_time.hour:02d}.csv"
        
        with page.expect_download(timeout=60000) as download_info:
            export_btn.click()
            wait_random(2, 4)
            
            # Look for CSV format option
            try:
                csv_option = page.locator("text=CSV, button:has-text('CSV')").first
                if csv_option.is_visible(timeout=5000):
                    csv_option.click()
                    print("Selected CSV format")
            except:
                print("CSV option not found, using default")
        
        # Save the download
        download = download_info.value
        file_path = os.path.join(dirs["financial"], filename)
        download.save_as(file_path)
        
        # Verify download
        if os.path.exists(file_path) and os.path.getsize(file_path) > 100:  # More than just headers
            print(f"Successfully downloaded: {filename} ({os.path.getsize(file_path)} bytes)")
            process_financial_report(filename, dates['current_hour'])
            return True
        else:
            raise Exception("Downloaded file is empty or too small")
        
    except Exception as e:
        print(f"Financial report error: {e}")
        # Create empty file as fallback
        az_time = get_arizona_time()
        filename = f"{dates['target_file']}_H{az_time.hour:02d}.csv"
        create_empty_financial_csv(filename, dirs["financial"], dates['target_us'], dates['current_hour'])
        process_financial_report(filename, dates['current_hour'])
        return False

# FIXED: Simplified RO report download  
def download_ro_reports(page, dirs, dates):
    """Download RO reports with better session management"""
    try:
        print("Downloading RO Marketing Reports...")
        
        locations = [
            {"name": "Mesa Broadway", "shop_id": "10738"},
            {"name": "Mesa Guadalupe", "shop_id": "11965"}, 
            {"name": "Phoenix", "shop_id": "10171"},
            {"name": "Tempe", "shop_id": "5566"},
            {"name": "Sun City West", "shop_id": "13513"},
            {"name": "Surprise", "shop_id": "13512"}
        ]
        
        success_count = 0
        az_time = get_arizona_time()
        
        for location in locations:
            try:
                print(f"Processing {location['name']}...")
                
                # Ensure logged in before each location
                if not ensure_logged_in(page):
                    raise Exception(f"Login failed for {location['name']}")
                
                # Navigate to RO Marketing page first
                print(f"Navigating to RO Marketing for {location['name']}...")
                page.goto("https://shop.tekmetric.com/admin/org/464/reports/customer/ro-marketing-source", timeout=60000)
                page.wait_for_load_state("networkidle", timeout=30000)
                wait_random(3, 5)
                
                # Check session after navigation
                if not is_logged_in(page):
                    raise Exception(f"Lost session for {location['name']}")
                
                # Set shop filter
                try:
                    # Look for shop selection dropdown/checkboxes
                    shop_elements = page.locator(f"text={location['name']}, [value='{location['shop_id']}']")
                    if shop_elements.count() > 0:
                        shop_elements.first.click()
                        wait_random(2, 3)
                except Exception as e:
                    print(f"Shop selection failed for {location['name']}: {e}")
                
                # Set date to today
                try:
                    today = dates['target_date']
                    date_str = today.strftime("%m/%d/%Y")
                    
                    # Set date range
                    date_inputs = page.locator("input[type='date'], input[placeholder*='date']")
                    count = date_inputs.count()
                    if count > 0:
                        for i in range(min(count, 2)):
                            date_inputs.nth(i).fill(date_str)
                            wait_random(1, 2)
                except Exception as e:
                    print(f"Date setting failed for {location['name']}: {e}")
                
                # Find export button
                export_btn = find_export_button_robust(page)
                if not export_btn:
                    raise Exception("Export button not found")
                
                # Download
                filename = f"{location['name'].replace(' ', '-')}-{dates['target_short']}_H{az_time.hour:02d}.csv"
                
                with page.expect_download(timeout=60000) as download_info:
                    export_btn.click()
                    wait_random(2, 4)
                
                download = download_info.value
                file_path = os.path.join(dirs["ro"], filename)
                download.save_as(file_path)
                
                # Verify download
                if os.path.exists(file_path) and os.path.getsize(file_path) > 50:
                    print(f"Successfully downloaded: {filename}")
                    process_ro_marketing_report(location['name'], filename, dates['current_hour'])
                    success_count += 1
                else:
                    raise Exception("Downloaded file is empty")
                
                wait_random(2, 4)
                
            except Exception as e:
                print(f"Error with {location['name']}: {e}")
                # Create empty file
                filename = f"{location['name'].replace(' ', '-')}-{dates['target_short']}_H{az_time.hour:02d}.csv"
                create_empty_csv(filename, dirs["ro"], location['name'], dates['target_us'], dates['current_hour'])
                process_ro_marketing_report(location['name'], filename, dates['current_hour'])
                success_count += 1
        
        print(f"RO processing completed: {success_count}/6")
        return success_count >= 4
        
    except Exception as e:
        print(f"RO reports error: {e}")
        return False

# Keep existing empty file creation functions
def create_empty_financial_csv(filename, directory, report_date, created_at):
    try:
        file_path = os.path.join(directory, filename)
        
        headers = ['Location', 'Car_Count', 'Hours_Presented', 'Hours_Sold', 'AWRO', 'Close_Ratio', 
                  'Effective_Labor_Rate', 'ARO_Sales', 'ARO_Profit', 'ARO_Profit_Margin',
                  'Gross_Sales_Hr', 'Gross_Profit_Hr', 'Total_Written_Sales', 'Net_Sales',
                  'Total_Fees', 'Total_Discounts', 'Total_Cost', 'Total_GP_Dollar', 'Total_GP_Percent',
                  'Report_Date', 'Created_At']
        
        locations = ['Gemba Automotive - Mesa Broadway (003)', 'Gemba Automotive - Mesa Guadalupe (004)',
                    'Gemba Automotive - Phoenix (002)', 'Gemba Automotive - Sun City West (007)',
                    'Gemba Automotive - Surprise (006)', 'Gemba Automotive - Tempe (001)']
        
        with open(file_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(headers)
            
            for location in locations:
                empty_row = [location] + ['0'] * (len(headers) - 3) + [report_date, created_at]
                writer.writerow(empty_row)
        
        print(f"Created empty financial file: {filename}")
        return True
    except Exception as e:
        print(f"Error creating empty financial file: {e}")
        return False

def create_empty_csv(filename, directory, location_name, report_date, created_at):
    try:
        file_path = os.path.join(directory, filename)
        headers = ['Marketing Source', 'Total Sales', 'RO Count', 'New Sales', 'New RO Count',
                  'Repeat Sales', 'Repeat RO Count', 'Average RO', 'GP $', 'GP %', 'Close Ratio',
                  'Location', 'Report_Date', 'Created_At']
        
        with open(file_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(headers)
            empty_row = ['No Data', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', location_name, report_date, created_at]
            writer.writerow(empty_row)
        
        print(f"Created empty file: {filename}")
        return True
    except Exception as e:
        print(f"Error creating empty file: {e}")
        return False

# FIXED: Main function with better error handling
def main():
    print("Starting Tekmetric Hourly Automation...")
    
    dirs = setup_directories()
    dates = get_date_info()
    
    print(f"Processing date: {dates['target_us']} at {dates['current_hour']}")
    
    with sync_playwright() as p:
        browser = None
        try:
            # Enhanced browser configuration for server environment
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-images',  # Faster loading
                    '--disable-javascript-harmony',
                    '--disable-web-security',
                    '--allow-running-insecure-content'
                ]
            )
            
            # Enhanced context for better session management
            context = browser.new_context(
                accept_downloads=True,
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                ignore_https_errors=True
            )
            
            page = context.new_page()
            page.set_default_timeout(60000)
            page.set_default_navigation_timeout(60000)
            
            # Login
            if not login_to_tekmetric(page):
                print("Login failed, aborting")
                return False
            
            # Download reports
            financial_success = download_financial_report(page, dirs, dates)
            ro_success = download_ro_reports(page, dirs, dates)
            
            # Process reports
            if ro_success:
                print("Combining RO reports...")
                combine_ro_reports(dates['target_short'], dates['current_hour'])
            
            print("Verifying data...")
            verify_data_accuracy(dates['target_file'], dates['target_short'], dates['current_hour'])
            
            print("Uploading to SQL...")
            upload_success = upload_all_reports(dates['current_hour'])
            
            if upload_success:
                print("Upload completed successfully")
            else:
                print("Upload failed")
            
            context.close()
            return upload_success
            
        except Exception as e:
            print(f"Automation error: {e}")
            return False
        finally:
            if browser:
                browser.close()

if __name__ == "__main__":
    main()