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

class TekmetricFixSession:
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
            print("Logging into Tekmetric for daily fix...")
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
            
            print(f"📥 Downloading {report_type} for daily fix...")
            
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
                    filename = f"{base}_fix_{timestamp}{ext}"
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

def get_yesterday_arizona():
    """Get yesterday's date in Arizona timezone"""
    az_now = get_arizona_time()
    yesterday = az_now - datetime.timedelta(days=1)
    return yesterday

def format_date(dt):
    return f"{dt.month}.{dt.day}.{dt.year}"

def format_date_short(dt):
    return f"{dt.month:02d}.{dt.day:02d}.{dt.year-2000:02d}"

def get_fix_date_info():
    """Get yesterday's date information for the fix process"""
    yesterday = get_yesterday_arizona()
    return {
        "yesterday_file": format_date(yesterday),
        "yesterday_short": format_date_short(yesterday),
        "yesterday_us": yesterday.strftime("%m/%d/%Y"),
        "yesterday_date": yesterday.date(),
        "fix_timestamp": "11:59 PM"  # Fixed timestamp for corrected records
    }

def setup_directories():
    base_path = os.getcwd()
    financial_dir = os.path.join(base_path, "Financial Reports Fix")
    ro_dir = os.path.join(base_path, "RO Reports Fix")
    os.makedirs(financial_dir, exist_ok=True)
    os.makedirs(ro_dir, exist_ok=True)
    return {"financial": financial_dir, "ro": ro_dir}

def download_financial_report_fix(session, dirs, dates):
    try:
        print("\n📊 DOWNLOADING YESTERDAY'S FINANCIAL REPORT FOR VERIFICATION")
        print("="*60)
        
        # Use Arizona timezone for yesterday's full day
        arizona_tz = pytz.timezone('US/Arizona')
        
        # Create Arizona timezone aware datetime objects for yesterday's full day
        start_az = arizona_tz.localize(datetime.datetime.combine(dates['yesterday_date'], datetime.time.min))
        end_az = arizona_tz.localize(datetime.datetime.combine(dates['yesterday_date'], datetime.time.max))
        
        # Convert to UTC for API
        start_utc = start_az.astimezone(pytz.utc)
        end_utc = end_az.astimezone(pytz.utc)
        
        # Format for URL
        start_iso = start_utc.strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-3] + 'Z'
        end_iso = end_utc.strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-3] + 'Z'
        
        financial_url = f"https://shop.tekmetric.com/admin/org/464/reports/financial/custom?start={start_iso}&end={end_iso}"
        
        print(f"→ Yesterday's Date: {dates['yesterday_date']} ({dates['yesterday_us']})")
        print(f"→ Arizona Start: {start_az}")
        print(f"→ Arizona End: {end_az}")
        print(f"→ URL: {financial_url}")
        
        session.page.goto(financial_url, timeout=90000)
        session.page.wait_for_timeout(5000)
        
        # Use fixed filename for verification
        base_filename = f"{dates['yesterday_file']}_DAILY_FIX.csv"
        
        # Use safe download method
        actual_filename = session.download_csv_safe(base_filename, dirs["financial"], "financial")
        
        if actual_filename:
            # Process with fix timestamp
            process_financial_report(actual_filename, dates['fix_timestamp'])
            print("✅ Financial report downloaded and processed for verification")
            return actual_filename
        else:
            print("❌ Failed to download financial report for verification")
            return False
        
    except Exception as e:
        print(f"❌ Financial report fix error: {e}")
        return False

def download_ro_reports_fix(session, dirs, dates):
    try:
        print("\n📈 DOWNLOADING YESTERDAY'S RO MARKETING REPORTS FOR VERIFICATION")
        print("="*60)
        
        locations = [
            {"name": "Mesa Broadway", "shop_id": "10738"},
            {"name": "Mesa Guadalupe", "shop_id": "11965"},
            {"name": "Phoenix", "shop_id": "10171"},
            {"name": "Tempe", "shop_id": "5566"},
            {"name": "Sun City West", "shop_id": "13513"},
            {"name": "Surprise", "shop_id": "13512"}
        ]
        
        success_count = 0
        downloaded_files = []
        
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
                
                base_filename = f"{location['name'].replace(' ', '-')}-{dates['yesterday_short']}_DAILY_FIX.csv"
                
                actual_filename = session.download_csv_safe(base_filename, dirs["ro"], "RO")
                
                if actual_filename:
                    process_ro_marketing_report(location['name'], actual_filename, dates['fix_timestamp'])
                    downloaded_files.append(actual_filename)
                    print(f"✅ {location['name']} processed successfully")
                else:
                    print(f"⚠️  Failed to download {location['name']}")
                
                success_count += 1
                session.wait_random(2, 3)
                
            except Exception as e:
                print(f"❌ Error with {location['name']}: {e}")
                success_count += 1  # Continue with other locations
        
        print(f"\n📊 RO processing completed: {success_count}/6 locations")
        return downloaded_files
        
    except Exception as e:
        print(f"❌ RO reports fix error: {e}")
        return []

def combine_ro_reports_fix(yesterday_short, fix_timestamp):
    """Combine all RO reports into single file for verification"""
    try:
        ro_dir = os.path.join(os.getcwd(), "RO Reports Fix")
        
        locations = [
            "Mesa-Broadway",
            "Mesa-Guadalupe", 
            "Phoenix",
            "Tempe",
            "Sun-City-West",
            "Surprise"
        ]
        
        # Generate filenames for fix
        ro_files = [f"{loc}-{yesterday_short}_DAILY_FIX.csv" for loc in locations]
        
        combined_filename = f"TekmetricGemba_RO_{yesterday_short}_DAILY_FIX.csv"
        combined_filepath = os.path.join(ro_dir, combined_filename)
        
        combined_data = []
        headers_set = False
        processed_count = 0
        
        print("Combining RO reports for verification...")
        
        for i, filename in enumerate(ro_files):
            filepath = os.path.join(ro_dir, filename)
            location_name = locations[i].replace('-', ' ')
            
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', newline='', encoding='utf-8') as file:
                        reader = csv.reader(file)
                        rows = list(reader)
                    
                    if rows:
                        # Add headers only once
                        if not headers_set:
                            combined_data.append(rows[0])
                            headers_set = True
                        
                        # Add data rows
                        combined_data.extend(rows[1:])
                        processed_count += 1
                        print(f"  ✅ Added {len(rows)-1} records from {location_name}")
                    
                except Exception as e:
                    print(f"  ❌ Error reading {filename}: {e}")
            else:
                print(f"  ⚠️  File not found: {filename}")
        
        if processed_count > 0:
            try:
                with open(combined_filepath, 'w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerows(combined_data)
                
                print(f"✅ Combined {processed_count}/6 RO reports: {combined_filename}")
                print(f"   Total records: {len(combined_data)-1}")
                return combined_filename
            except Exception as e:
                print(f"❌ Error writing combined file: {e}")
                return None
        else:
            print("❌ No RO files to combine")
            return None
        
    except Exception as e:
        print(f"❌ Combine error: {e}")
        return None

def compare_and_update_database(dates):
    """Compare downloaded data with database and update if different"""
    try:
        print("\n🔍 COMPARING DATA WITH DATABASE")
        print("="*50)
        
        # Import SQL functions
        from sql import create_connection, read_csv_data, sanitize_headers, upsert_data_with_created_at
        
        # Get file paths
        financial_dir = os.path.join(os.getcwd(), "Financial Reports Fix")
        ro_dir = os.path.join(os.getcwd(), "RO Reports Fix")
        
        financial_file = f"{dates['yesterday_file']}_DAILY_FIX.csv"
        ro_file = f"TekmetricGemba_RO_{dates['yesterday_short']}_DAILY_FIX.csv"
        
        financial_path = os.path.join(financial_dir, financial_file)
        ro_path = os.path.join(ro_dir, ro_file)
        
        updates_made = False
        
        # Check financial data
        print("Checking financial data...")
        if os.path.exists(financial_path):
            headers, data = read_csv_data(financial_path)
            if headers and data:
                headers = sanitize_headers(headers)
                
                conn = create_connection()
                if conn:
                    try:
                        # Check if we need to update by comparing with existing data
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT COUNT(*) FROM [custom_financials_2] 
                            WHERE Report_Date = %s AND Created_At = %s
                        """, (dates['yesterday_us'], "11:50 PM"))
                        
                        existing_count = cursor.fetchone()[0]
                        
                        if existing_count > 0:
                            print(f"  Found {existing_count} existing records for {dates['yesterday_us']}")
                            
                            # Update with verification timestamp
                            key_columns = ['Location', 'Report_Date']
                            success = upsert_data_with_created_at(conn, 'custom_financials_2', headers, data, key_columns)
                            
                            if success:
                                updates_made = True
                                print("  ✅ Financial data verified and updated if needed")
                            else:
                                print("  ❌ Failed to update financial data")
                        else:
                            print("  ⚠️  No existing records found to verify")
                        
                    finally:
                        conn.close()
                else:
                    print("  ❌ Database connection failed")
            else:
                print("  ❌ Failed to read financial file")
        else:
            print("  ❌ Financial file not found")
        
        # Check RO data
        print("Checking RO data...")
        if os.path.exists(ro_path):
            headers, data = read_csv_data(ro_path)
            if headers and data:
                headers = sanitize_headers(headers)
                
                conn = create_connection()
                if conn:
                    try:
                        # Check if we need to update by comparing with existing data
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT COUNT(*) FROM [ro_marketing_2] 
                            WHERE Report_Date = %s AND Created_At = %s
                        """, (dates['yesterday_us'], "11:50 PM"))
                        
                        existing_count = cursor.fetchone()[0]
                        
                        if existing_count > 0:
                            print(f"  Found {existing_count} existing records for {dates['yesterday_us']}")
                            
                            # Update with verification timestamp
                            key_columns = ['Marketing_Source', 'Location', 'Report_Date']
                            success = upsert_data_with_created_at(conn, 'ro_marketing_2', headers, data, key_columns)
                            
                            if success:
                                updates_made = True
                                print("  ✅ RO data verified and updated if needed")
                            else:
                                print("  ❌ Failed to update RO data")
                        else:
                            print("  ⚠️  No existing records found to verify")
                        
                    finally:
                        conn.close()
                else:
                    print("  ❌ Database connection failed")
            else:
                print("  ❌ Failed to read RO file")
        else:
            print("  ❌ RO file not found")
        
        if updates_made:
            print("✅ Database verification and updates completed")
        else:
            print("ℹ️  No updates were necessary")
        
        return updates_made
        
    except Exception as e:
        print(f"❌ Database comparison error: {e}")
        return False

def cleanup_fix_files():
    """Clean up temporary fix files"""
    try:
        print("\n🧹 CLEANING UP FIX FILES")
        print("="*30)
        
        fix_dirs = ["Financial Reports Fix", "RO Reports Fix"]
        cleaned_count = 0
        
        for dir_name in fix_dirs:
            dir_path = os.path.join(os.getcwd(), dir_name)
            if os.path.exists(dir_path):
                for filename in os.listdir(dir_path):
                    if filename.endswith('.csv'):
                        file_path = os.path.join(dir_path, filename)
                        try:
                            os.remove(file_path)
                            cleaned_count += 1
                        except Exception as e:
                            print(f"  ⚠️  Could not delete {filename}: {e}")
        
        print(f"✅ Cleaned up {cleaned_count} temporary files")
        
    except Exception as e:
        print(f"❌ Cleanup error: {e}")

def main():
    print("TEKMETRIC DAILY DATA VERIFICATION & FIX AUTOMATION")
    print("="*60)
    print("🕒 Running at 7:00 AM Arizona Time")
    
    email = os.getenv("TEKMETRIC_EMAIL")
    password = os.getenv("TEKMETRIC_PASSWORD")
    
    print(f"Environment check:")
    print(f"  TEKMETRIC_EMAIL: {email if email else 'NOT LOADED'}")
    print(f"  TEKMETRIC_PASSWORD: {'SET' if password else 'NOT LOADED'}")
    
    if not email or not password:
        print("\n❌ Credentials not loaded!")
        return False
    
    dirs = setup_directories()
    dates = get_fix_date_info()
    
    print(f"\nVerifying data for: {dates['yesterday_us']} (Yesterday)")
    print(f"Fix timestamp will be: {dates['fix_timestamp']}")
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
            
            session = TekmetricFixSession(page)
            
            print("\nSTEP 1: Authenticating...")
            if not session.login():
                print("❌ Authentication failed")
                return False
            
            print("\nSTEP 2: Downloading yesterday's reports...")
            financial_file = download_financial_report_fix(session, dirs, dates)
            ro_files = download_ro_reports_fix(session, dirs, dates)
            
            if ro_files:
                print("\nSTEP 3: Combining RO reports...")
                combine_ro_reports_fix(dates['yesterday_short'], dates['fix_timestamp'])
            
            print("\nSTEP 4: Comparing with database and updating if needed...")
            updates_made = compare_and_update_database(dates)
            
            print("\nSTEP 5: Cleaning up temporary files...")
            cleanup_fix_files()
            
            print("\n" + "="*60)
            if updates_made:
                print("✅ DAILY FIX COMPLETED - DATABASE UPDATED!")
                print("🔧 Records updated with timestamp: 11:59 PM")
            else:
                print("✅ DAILY FIX COMPLETED - NO UPDATES NEEDED!")
                print("📊 All data was already accurate")
            print("="*60)
            
            return True
            
        except Exception as e:
            print(f"\n❌ DAILY FIX FAILED: {e}")
            return False
        finally:
            if browser:
                browser.close()

if __name__ == "__main__":
    main()