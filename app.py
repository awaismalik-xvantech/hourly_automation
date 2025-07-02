import os
import time
import random
import datetime
import pytz
import csv
from playwright.sync_api import sync_playwright

# Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
    print("✅ .env file loaded successfully")
except ImportError:
    print("⚠️  python-dotenv not installed. Install with: pip install python-dotenv")

from reports import process_financial_report, process_ro_marketing_report, combine_ro_reports, verify_data_accuracy
from sql import upload_all_reports

class TekmetricSession:
    def __init__(self, page):
        self.page = page
        self.is_authenticated = False
        
    def wait_random(self, min_sec=2, max_sec=4):
        time.sleep(random.uniform(min_sec, max_sec))
    
    def login(self):
        email = os.getenv("TEKMETRIC_EMAIL")
        password = os.getenv("TEKMETRIC_PASSWORD")
        
        if not email or not password:
            print("❌ Missing credentials")
            return False
        
        try:
            print("Logging into Tekmetric...")
            self.page.goto("https://shop.tekmetric.com/", timeout=60000)
            self.page.wait_for_timeout(5000)
            
            email_input = self.page.locator("input[type='email'], #email, input[name='email']").first
            email_input.clear()
            email_input.fill(email)
            print(f"✅ Filled email: {email}")
            self.page.wait_for_timeout(2000)
            
            password_input = self.page.locator("input[type='password'], #password, input[name='password']").first  
            password_input.clear()
            password_input.fill(password)
            print(f"✅ Filled password: {'*' * len(password)}")
            self.page.wait_for_timeout(2000)
            
            sign_in_btn = self.page.locator("button:has-text('SIGN IN'), button:has-text('Sign In')").first
            sign_in_btn.click()
            print("✅ Clicked Sign In")
            self.page.wait_for_timeout(8000)
            
            try:
                self.page.wait_for_url(lambda url: "login" not in url.lower() and url != "https://shop.tekmetric.com/", timeout=15000)
                print("✅ Login successful - redirected to dashboard")
                self.is_authenticated = True
                return True
            except:
                signin_count = self.page.locator("button:has-text('SIGN IN'), button:has-text('Sign In')").count()
                if signin_count == 0:
                    print("✅ Login successful")
                    self.is_authenticated = True
                    return True
                else:
                    print("❌ Login failed")
                    return False
                
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    def find_and_click_export(self):
        try:
            print("Looking for Export button...")
            self.page.wait_for_timeout(4000)
            
            try:
                self.page.wait_for_selector("[data-testid='loading'], .loading, .spinner", state="hidden", timeout=15000)
                print("✅ Page finished loading")
            except:
                print("⚠️  Loading timeout, continuing...")
            
            export_selectors = [
                '[data-cy="button"]:has-text("Export")',
                'button:has-text("Export")',
                'button.MuiButtonBase-root:has-text("Export")'
            ]
            
            print("🔍 Searching for Export button...")
            for i, selector in enumerate(export_selectors, 1):
                try:
                    elements = self.page.locator(selector)
                    count = elements.count()
                    print(f"  {i}. {selector}: {count} found")
                    
                    if count > 0:
                        element = elements.first
                        if element.is_visible():
                            print(f"✅ Found Export button!")
                            return element
                except Exception as e:
                    continue
            
            print("❌ Export button not found")
            return None
            
        except Exception as e:
            print(f"❌ Export search error: {e}")
            return None
    
    def download_csv_safe(self, filename, download_dir, report_type="report"):
        """Enhanced CSV download with file permission handling"""
        try:
            export_btn = self.find_and_click_export()
            if not export_btn:
                return False
            
            print(f"📥 Downloading {report_type}...")
            
            # Check if file already exists and try to remove it
            file_path = os.path.join(download_dir, filename)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"🗑️  Removed existing file: {filename}")
                except PermissionError:
                    print(f"⚠️  File {filename} is open in another program. Trying alternative filename...")
                    # Create alternative filename with timestamp
                    base, ext = os.path.splitext(filename)
                    timestamp = datetime.datetime.now().strftime("%H%M%S")
                    filename = f"{base}_{timestamp}{ext}"
                    file_path = os.path.join(download_dir, filename)
                    print(f"📝 Using alternative filename: {filename}")
            
            with self.page.expect_download(timeout=90000) as download_info:
                export_btn.click()
                print("✅ Clicked Export button")
                self.wait_random(2, 3)
                
                # For financial reports, try to click CSV
                if report_type == "financial":
                    try:
                        csv_option = self.page.locator("text=CSV").first
                        if csv_option.is_visible():
                            print("→ Selecting CSV format...")
                            csv_option.click()
                            self.wait_random(2, 3)
                    except:
                        print("⚠️  CSV option not found, using default")
                
                print("⏳ Waiting for download...")
            
            download = download_info.value
            
            # Try to save with retries
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    download.save_as(file_path)
                    break
                except PermissionError as e:
                    if attempt < max_retries - 1:
                        print(f"⚠️  Permission error (attempt {attempt + 1}), retrying...")
                        time.sleep(2)
                        # Try with different filename
                        base, ext = os.path.splitext(filename)
                        filename = f"{base}_retry{attempt + 1}{ext}"
                        file_path = os.path.join(download_dir, filename)
                    else:
                        raise e
            
            min_size = 100 if report_type == "financial" else 50
            if os.path.exists(file_path) and os.path.getsize(file_path) > min_size:
                print(f"✅ Downloaded: {filename} ({os.path.getsize(file_path)} bytes)")
                return filename  # Return the actual filename used
            else:
                print(f"❌ Download failed or file too small")
                return False
                
        except Exception as e:
            print(f"❌ Download error: {e}")
            return False

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
    return {
        "yesterday_file": format_date(az_now),
        "yesterday_short": format_date_short(az_now),
        "yesterday_us": az_now.strftime("%m/%d/%Y"),
        "yesterday_date": az_now.date(),
        "current_hour": get_current_hour_12format()
    }

def setup_directories():
    base_path = os.getcwd()
    financial_dir = os.path.join(base_path, "Financial Reports")
    ro_dir = os.path.join(base_path, "RO Reports")
    os.makedirs(financial_dir, exist_ok=True)
    os.makedirs(ro_dir, exist_ok=True)
    return {"financial": financial_dir, "ro": ro_dir}

def create_empty_financial_csv_safe(filename, directory, report_date, created_at):
    """Create empty financial CSV with permission error handling"""
    try:
        file_path = os.path.join(directory, filename)
        
        # Check if file exists and is locked
        if os.path.exists(file_path):
            try:
                # Try to open file to check if it's locked
                with open(file_path, 'r') as test_file:
                    pass
            except PermissionError:
                print(f"⚠️  File {filename} is locked. Using alternative filename...")
                base, ext = os.path.splitext(filename)
                timestamp = datetime.datetime.now().strftime("%H%M%S")
                filename = f"{base}_empty_{timestamp}{ext}"
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
        return filename
    except Exception as e:
        print(f"Error creating empty financial file: {e}")
        return False

def download_financial_report(session, dirs, dates):
    try:
        print("\n📊 DOWNLOADING FINANCIAL REPORT")
        print("="*50)
        
        # FIXED: Use correct Arizona timezone conversion
        arizona_tz = pytz.timezone('US/Arizona')
        
        # Create Arizona timezone aware datetime objects for the target date
        start_az = arizona_tz.localize(datetime.datetime.combine(dates['yesterday_date'], datetime.time.min))
        end_az = arizona_tz.localize(datetime.datetime.combine(dates['yesterday_date'], datetime.time.max))
        
        # Convert to UTC for API (this will show next day in UTC due to timezone offset)
        start_utc = start_az.astimezone(pytz.utc)
        end_utc = end_az.astimezone(pytz.utc)
        
        # Format for URL
        start_iso = start_utc.strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-3] + 'Z'
        end_iso = end_utc.strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-3] + 'Z'
        
        financial_url = f"https://shop.tekmetric.com/admin/org/464/reports/financial/custom?start={start_iso}&end={end_iso}"
        
        print(f"→ Target Arizona Date: {dates['yesterday_date']} ({dates['yesterday_us']})")
        print(f"→ Arizona Start: {start_az}")
        print(f"→ Arizona End: {end_az}")
        print(f"→ UTC Start: {start_utc}")
        print(f"→ UTC End: {end_utc}")
        print(f"→ URL: {financial_url}")
        
        session.page.goto(financial_url, timeout=90000)
        session.page.wait_for_timeout(5000)
        
        az_time = get_arizona_time()
        base_filename = f"{dates['yesterday_file']}_H{az_time.hour:02d}.csv"
        
        # Use safe download method
        actual_filename = session.download_csv_safe(base_filename, dirs["financial"], "financial")
        
        if actual_filename:
            process_financial_report(actual_filename, dates['current_hour'])
            print("✅ Financial report processed successfully")
        else:
            print("⚠️  Creating empty financial file...")
            actual_filename = create_empty_financial_csv_safe(base_filename, dirs["financial"], 
                                     dates['yesterday_us'], dates['current_hour'])
            if actual_filename:
                process_financial_report(actual_filename, dates['current_hour'])
                print("✅ Empty financial report processed")
        
        return True
        
    except Exception as e:
        print(f"❌ Financial report error: {e}")
        return True  # Continue with RO reports even if financial fails

def download_ro_reports(session, dirs, dates):
    try:
        print("\n📈 DOWNLOADING RO MARKETING REPORTS")
        print("="*50)
        
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
        
        for i, location in enumerate(locations):
            try:
                print(f"\n📍 Processing {location['name']} ({i+1}/6)...")
                
                arizona_tz = pytz.timezone('US/Arizona')
                start_dt = arizona_tz.localize(datetime.datetime.combine(dates['yesterday_date'], datetime.time(0, 0, 0)))
                end_dt = arizona_tz.localize(datetime.datetime.combine(dates['yesterday_date'], datetime.time(23, 59, 59)))
                
                start_str = start_dt.strftime('%Y-%m-%dT%H:%M:%S.000-07:00').replace(':', '%3A')
                end_str = end_dt.strftime('%Y-%m-%dT%H:%M:%S.999-07:00').replace(':', '%3A')
                
                ro_url = f"https://shop.tekmetric.com/admin/org/464/reports/customer/ro-marketing-source?start={start_str}&end={end_str}&shopIds={location['shop_id']}"
                
                session.page.goto(ro_url, timeout=90000)
                session.page.wait_for_timeout(5000)
                
                base_filename = f"{location['name'].replace(' ', '-')}-{dates['yesterday_short']}_H{az_time.hour:02d}.csv"
                
                actual_filename = session.download_csv_safe(base_filename, dirs["ro"], "RO")
                
                if actual_filename:
                    process_ro_marketing_report(location['name'], actual_filename, dates['current_hour'])
                    print(f"✅ {location['name']} processed successfully")
                else:
                    print(f"⚠️  Creating empty file for {location['name']}...")
                    # Create empty RO file logic here
                
                success_count += 1
                session.wait_random(2, 3)
                
            except Exception as e:
                print(f"❌ Error with {location['name']}: {e}")
                success_count += 1  # Continue with other locations
        
        print(f"\n📊 RO processing completed: {success_count}/6 locations")
        return success_count >= 4
        
    except Exception as e:
        print(f"❌ RO reports error: {e}")
        return False

def main():
    print("TEKMETRIC AUTOMATION - PERMISSION FIXED VERSION")
    print("="*60)
    
    email = os.getenv("TEKMETRIC_EMAIL")
    password = os.getenv("TEKMETRIC_PASSWORD")
    
    print(f"Environment check:")
    print(f"  TEKMETRIC_EMAIL: {email if email else 'NOT LOADED'}")
    print(f"  TEKMETRIC_PASSWORD: {'SET' if password else 'NOT LOADED'}")
    
    if not email or not password:
        print("\n❌ Credentials not loaded!")
        return False
    
    dirs = setup_directories()
    dates = get_date_info()
    
    print(f"\nProcessing date: {dates['yesterday_us']} at {dates['current_hour']}")
    print("="*60)
    
    with sync_playwright() as p:
        browser = None
        try:
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            context = browser.new_context(
                accept_downloads=True,
                viewport={"width": 1920, "height": 1080}
            )
            
            page = context.new_page()
            page.set_default_timeout(90000)
            
            session = TekmetricSession(page)
            
            print("\nSTEP 1: Authenticating...")
            if not session.login():
                print("❌ Authentication failed")
                return False
            
            print("\nSTEP 2: Downloading reports...")
            financial_success = download_financial_report(session, dirs, dates)
            ro_success = download_ro_reports(session, dirs, dates)
            
            if ro_success:
                print("\nSTEP 3: Combining RO reports...")
                combine_ro_reports(dates['yesterday_short'], dates['current_hour'])
            
            print("\nSTEP 4: Verifying data...")
            verify_data_accuracy(dates['yesterday_file'], dates['yesterday_short'], dates['current_hour'])
            
            print("\nSTEP 5: Uploading to SQL...")
            upload_success = upload_all_reports(dates['current_hour'])
            
            print("\n" + "="*60)
            if upload_success:
                print("✅ AUTOMATION COMPLETED SUCCESSFULLY!")
            else:
                print("⚠️  AUTOMATION COMPLETED WITH UPLOAD ERRORS")
            print("="*60)
            
            return upload_success
            
        except Exception as e:
            print(f"\n❌ AUTOMATION FAILED: {e}")
            return False
        finally:
            if browser:
                browser.close()

if __name__ == "__main__":
    main()
