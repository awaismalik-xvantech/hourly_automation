import os
import time
import random
import datetime
import pytz
import csv
from playwright.sync_api import sync_playwright
from reports import process_financial_report, process_ro_marketing_report, combine_ro_reports, verify_data_accuracy
from sql import upload_all_reports

def wait_random(min_sec=2, max_sec=4):
    time.sleep(random.uniform(min_sec, max_sec))

def get_arizona_time():
    return datetime.datetime.now(pytz.timezone('US/Arizona'))

def format_date(dt):
    return f"{dt.month}.{dt.day}.{dt.year}"

def format_date_short(dt):
    return f"{dt.month:02d}.{dt.day:02d}.{dt.year-2000:02d}"

def get_current_hour_12format():
    az_now = get_arizona_time()
    return az_now.strftime("%I %p").lstrip('0')

def get_date_info():
    az_now = get_arizona_time()
    az_today = az_now
    
    return {
        "yesterday_file": format_date(az_today),
        "yesterday_short": format_date_short(az_today),
        "yesterday_us": az_today.strftime("%m/%d/%Y"),
        "yesterday_date": az_today.date(),
        "current_hour": get_current_hour_12format()
    }

def setup_directories():
    base_path = os.getcwd()
    financial_dir = os.path.join(base_path, "Financial Reports")
    ro_dir = os.path.join(base_path, "RO Reports")
    os.makedirs(financial_dir, exist_ok=True)
    os.makedirs(ro_dir, exist_ok=True)
    return {"financial": financial_dir, "ro": ro_dir}

def build_financial_url(date_obj):
    arizona_tz = pytz.timezone('US/Arizona')
    start_az = arizona_tz.localize(datetime.datetime.combine(date_obj, datetime.time.min))
    end_az = arizona_tz.localize(datetime.datetime.combine(date_obj, datetime.time.max))
    
    start_utc = start_az.astimezone(pytz.utc)
    end_utc = end_az.astimezone(pytz.utc)
    
    start_iso = start_utc.strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-3] + 'Z'
    end_iso = end_utc.strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-3] + 'Z'
    
    return f"https://shop.tekmetric.com/admin/org/464/reports/financial/custom?start={start_iso}&end={end_iso}"

def build_ro_url(shop_id, date_obj):
    arizona_tz = pytz.timezone('US/Arizona')
    start_dt = arizona_tz.localize(datetime.datetime.combine(date_obj, datetime.time(0, 0, 0)))
    end_dt = arizona_tz.localize(datetime.datetime.combine(date_obj, datetime.time(23, 59, 59)))
    
    start_str = start_dt.strftime('%Y-%m-%dT%H:%M:%S.000-07:00').replace(':', '%3A')
    end_str = end_dt.strftime('%Y-%m-%dT%H:%M:%S.999-07:00').replace(':', '%3A')
    
    return f"https://shop.tekmetric.com/admin/org/464/reports/customer/ro-marketing-source?start={start_str}&end={end_str}&shopIds={shop_id}"

def simple_page_wait(page):
    try:
        page.wait_for_load_state("domcontentloaded", timeout=60000)
        wait_random(5, 8)
        return True
    except:
        wait_random(8, 12)
        return True

def is_logged_in(page):
    try:
        page.wait_for_timeout(3000)
        # Simple check - just look for sign in button
        sign_in_count = page.locator("button:has-text('Sign In')").count()
        return sign_in_count == 0
    except:
        return True

def ensure_logged_in(page):
    if not is_logged_in(page):
        print("Session lost, re-logging in...")
        return login_to_tekmetric(page)
    return True

def find_export_button(page):
    selectors = [
        "button:has-text('Export')",
        "[data-cy='button']:has-text('Export')", 
        "button[class*='export' i]",
        ".export-button",
        "button:has-text('export')",
        "span:has-text('Export')",
        "[role='button']:has-text('Export')",
        "button[type='button']:has-text('Export')",
        ".MuiButton-root:has-text('Export')",
        "[data-testid*='export']",
        "button[aria-label*='Export']",
        "*:has-text('Export'):visible",
        "button.btn:has-text('Export')",
        ".btn-primary:has-text('Export')",
        "input[value='Export']",
        "[title*='Export']"
    ]
    
    for attempt in range(6):
        print(f"  Export button search attempt {attempt + 1}/6...")
        wait_random(6, 10)
        
        if not ensure_logged_in(page):
            print("  Lost session during export search")
            return None
        
        try:
            page.evaluate("window.scrollTo(0, 0)")
            wait_random(2, 3)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            wait_random(2, 3)
            page.evaluate("window.scrollTo(0, 0)")
            wait_random(2, 3)
        except:
            pass
        
        for selector in selectors:
            try:
                elements = page.locator(selector)
                count = elements.count()
                if count > 0:
                    for i in range(count):
                        element = elements.nth(i)
                        if element.is_visible():
                            print(f"  Found Export button with: {selector}")
                            return element
            except:
                continue
        
        if attempt < 5:
            print("  Export button not found, waiting longer...")
            wait_random(8, 12)
    
    try:
        all_buttons = page.locator("button, input[type='button'], [role='button']")
        button_count = all_buttons.count()
        print(f"  DEBUG: Found {button_count} total buttons on page")
        for i in range(min(button_count, 10)):
            try:
                button_text = all_buttons.nth(i).text_content()
                print(f"    Button {i+1}: '{button_text}'")
            except:
                pass
    except:
        pass
    
    return None

def download_financial_csv(page, filename, download_dir):
    try:
        if not ensure_logged_in(page):
            print("Session check failed before financial download")
            return False
        
        print("Looking for Export button...")
        print("Waiting for page to fully load...")
        
        wait_random(12, 18)
        
        try:
            page.wait_for_load_state("networkidle", timeout=30000)
            wait_random(5, 8)
        except:
            print("  NetworkIdle timeout, continuing...")
        
        try:
            page.wait_for_selector("[data-testid='loading'], .loading, .spinner", state="hidden", timeout=20000)
            print("  Loading indicators cleared")
            wait_random(3, 5)
        except:
            print("  No loading indicators found")
        
        try:
            page.wait_for_selector("table, .data-table, .report-table", timeout=15000)
            print("  Data table detected")
            wait_random(4, 6)
        except:
            print("  No data table detected")
        
        try:
            screenshot_path = f"/app/debug_financial_page.png"
            page.screenshot(path=screenshot_path)
            print(f"  Debug screenshot saved: {screenshot_path}")
        except:
            pass
        
        export_btn = find_export_button(page)
        if not export_btn:
            print("Export button not found after all attempts")
            return False
        
        print("Found Export button, clicking...")
        
        with page.expect_download(timeout=90000) as download_info:
            export_btn.click()
            wait_random(5, 8)
            
            print("Looking for CSV option...")
            csv_btn = page.locator("text=CSV").first
            try:
                csv_btn.wait_for(state="visible", timeout=15000)
                csv_btn.click()
                print("CSV option clicked")
                wait_random(3, 5)
            except:
                print("CSV option not found, using default download")
        
        download = download_info.value
        file_path = os.path.join(download_dir, filename)
        download.save_as(file_path)
        
        if os.path.exists(file_path) and os.path.getsize(file_path) >= 100:
            print(f"Downloaded: {filename} ({os.path.getsize(file_path)} bytes)")
            return True
        
        return False
        
    except Exception as e:
        print(f"Download error: {e}")
        return False

def download_ro_csv(page, filename, download_dir):
    try:
        if not ensure_logged_in(page):
            print("Session check failed before RO download")
            return False
        
        print("Looking for Export button...")
        print("Waiting for RO page to fully load...")
        wait_random(5, 8)
        
        try:
            page.wait_for_selector("[data-testid='loading'], .loading, .spinner", state="hidden", timeout=12000)
            wait_random(3, 5)
        except:
            pass
        
        export_btn = find_export_button(page)
        if not export_btn:
            print("Export button not found after all attempts")
            return False
        
        print("Found Export button, clicking...")
        
        with page.expect_download(timeout=90000) as download_info:
            export_btn.click()
            wait_random(4, 6)
        
        download = download_info.value
        file_path = os.path.join(download_dir, filename)
        download.save_as(file_path)
        
        if os.path.exists(file_path) and os.path.getsize(file_path) >= 50:
            print(f"Downloaded: {filename} ({os.path.getsize(file_path)} bytes)")
            return True
        
        return False
        
    except Exception as e:
        print(f"Download error: {e}")
        return False

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

def login_to_tekmetric(page):
    print("DEBUG: Starting login function")
    
    email = os.getenv("TEKMETRIC_EMAIL")
    password = os.getenv("TEKMETRIC_PASSWORD")
    
    print(f"DEBUG: Email set: {email is not None}")
    print(f"DEBUG: Password set: {password is not None}")
    
    if not email or not password:
        print("ERROR: Missing credentials")
        return False
    
    try:
        print("DEBUG: Going to Tekmetric...")
        page.goto("https://shop.tekmetric.com/", timeout=60000)
        print("DEBUG: Page loaded")
        
        page.wait_for_timeout(5000)
        print("DEBUG: Waited 5 seconds")
        
        # Check what we see on the page
        print(f"DEBUG: Current URL: {page.url}")
        
        # Try to fill email
        print("DEBUG: Looking for email input...")
        email_inputs = page.locator("input[type='email'], #email, input[name='email']")
        print(f"DEBUG: Found {email_inputs.count()} email inputs")
        
        if email_inputs.count() > 0:
            email_inputs.first.fill(email)
            print("DEBUG: Email filled")
            page.wait_for_timeout(2000)
        else:
            print("ERROR: No email input found")
            return False
        
        # Try to fill password
        print("DEBUG: Looking for password input...")
        password_inputs = page.locator("input[type='password'], #password, input[name='password']")
        print(f"DEBUG: Found {password_inputs.count()} password inputs")
        
        if password_inputs.count() > 0:
            password_inputs.first.fill(password)
            print("DEBUG: Password filled")
            page.wait_for_timeout(2000)
        else:
            print("ERROR: No password input found")
            return False
        
        # Try to click sign in
        print("DEBUG: Looking for sign in button...")
        sign_in_buttons = page.locator("button:has-text('SIGN IN'), button:has-text('Sign In'), input[type='submit']")
        print(f"DEBUG: Found {sign_in_buttons.count()} sign in buttons")
        
        if sign_in_buttons.count() > 0:
            print("DEBUG: Clicking sign in...")
            sign_in_buttons.first.click()
            print("DEBUG: Sign in clicked")
            page.wait_for_timeout(10000)
        else:
            print("ERROR: No sign in button found")
            return False
        
        # Check result
        new_url = page.url
        print(f"DEBUG: URL after login: {new_url}")
        
        if "login" not in new_url.lower():
            print("DEBUG: Login successful - URL changed")
            return True
        
        # Check for sign in button still visible
        still_sign_in = page.locator("button:has-text('SIGN IN'), button:has-text('Sign In')").count()
        print(f"DEBUG: Sign in buttons still visible: {still_sign_in}")
        
        if still_sign_in == 0:
            print("DEBUG: Login successful - no sign in button visible")
            return True
        
        print("DEBUG: Login failed - still on login page")
        return False
        
    except Exception as e:
        print(f"ERROR: Login exception: {e}")
        return False

def download_financial_report(page, dirs, dates):
    try:
        print("Downloading Financial Report...")
        
        if not ensure_logged_in(page):
            raise Exception("Login verification failed before financial report")
        
        financial_url = build_financial_url(dates['yesterday_date'])
        print(f"Going to: {financial_url}")
        
        page.goto(financial_url, timeout=90000)
        simple_page_wait(page)
        wait_random(5, 8)
        
        if not is_logged_in(page):
            print("Lost session after navigation, re-logging...")
            if not login_to_tekmetric(page):
                raise Exception("Re-login failed")
            page.goto(financial_url, timeout=90000)
            simple_page_wait(page)
        
        az_time = get_arizona_time()
        filename = f"{dates['yesterday_file']}_H{az_time.hour:02d}.csv"
        success = download_financial_csv(page, filename, dirs["financial"])
        
        if success:
            print("Processing financial report...")
            process_financial_report(filename, dates['current_hour'])
            print("Financial report processed successfully")
        else:
            print("Financial report download failed, creating empty file with zero data...")
            create_empty_financial_csv(filename, dirs["financial"], dates['yesterday_us'], dates['current_hour'])
            print("Processing empty financial report...")
            process_financial_report(filename, dates['current_hour'])
            print("Empty financial report processed successfully")
            success = True
        
        return success
        
    except Exception as e:
        print(f"Financial report error: {e}")
        try:
            az_time = get_arizona_time()
            filename = f"{dates['yesterday_file']}_H{az_time.hour:02d}.csv"
            create_empty_financial_csv(filename, dirs["financial"], dates['yesterday_us'], dates['current_hour'])
            process_financial_report(filename, dates['current_hour'])
            print("Created and processed empty financial file after error")
            return True
        except:
            return False

def download_ro_reports(page, dirs, dates):
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
                
                if not ensure_logged_in(page):
                    raise Exception(f"Login verification failed for {location['name']}")
                
                url = build_ro_url(location['shop_id'], dates['yesterday_date'])
                print(f"Going to: {url}")
                
                page.goto(url, timeout=90000)
                simple_page_wait(page)
                wait_random(4, 6)
                
                if not is_logged_in(page):
                    print(f"Lost session for {location['name']}, re-logging...")
                    if not login_to_tekmetric(page):
                        raise Exception(f"Re-login failed for {location['name']}")
                    page.goto(url, timeout=90000)
                    simple_page_wait(page)
                
                filename = f"{location['name'].replace(' ', '-')}-{dates['yesterday_short']}_H{az_time.hour:02d}.csv"
                
                success = download_ro_csv(page, filename, dirs["ro"])
                
                if success:
                    process_ro_marketing_report(location['name'], filename, dates['current_hour'])
                    success_count += 1
                    print(f"Successfully processed {location['name']}")
                else:
                    print(f"Download failed for {location['name']}, creating empty file")
                    create_empty_csv(filename, dirs["ro"], location['name'], dates['yesterday_us'], dates['current_hour'])
                    process_ro_marketing_report(location['name'], filename, dates['current_hour'])
                    success_count += 1
                
                wait_random(4, 6)
                
            except Exception as e:
                print(f"Error with {location['name']}: {e}")
                filename = f"{location['name'].replace(' ', '-')}-{dates['yesterday_short']}_H{az_time.hour:02d}.csv"
                create_empty_csv(filename, dirs["ro"], location['name'], dates['yesterday_us'], dates['current_hour'])
                process_ro_marketing_report(location['name'], filename, dates['current_hour'])
                success_count += 1
        
        print(f"RO processing completed: {success_count}/6")
        return success_count >= 4
        
    except Exception as e:
        print(f"RO reports error: {e}")
        return False

def main():
    print("Starting Tekmetric Hourly Automation...")
    
    dirs = setup_directories()
    dates = get_date_info()
    
    print(f"Processing date: {dates['yesterday_us']} (TODAY) at {dates['current_hour']}")
    
    with sync_playwright() as p:
        browser = None
        try:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox', 
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-extensions'
                ]
            )
            
            context = browser.new_context(
                accept_downloads=True,
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            page = context.new_page()
            page.set_default_timeout(90000)
            page.set_default_navigation_timeout(90000)
            
            if not login_to_tekmetric(page):
                print("Login failed, aborting")
                return False
            
            financial_success = download_financial_report(page, dirs, dates)
            ro_success = download_ro_reports(page, dirs, dates)
            
            if ro_success:
                print("Combining RO reports...")
                combine_ro_reports(dates['yesterday_short'], dates['current_hour'])
            
            print("Verifying data...")
            verify_data_accuracy(dates['yesterday_file'], dates['yesterday_short'], dates['current_hour'])
            
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
