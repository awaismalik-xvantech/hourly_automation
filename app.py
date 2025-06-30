import os
import time
import random
import datetime
import pytz
import csv
from playwright.sync_api import sync_playwright
from .reports import process_financial_report, process_ro_marketing_report, combine_ro_reports, verify_data_accuracy
from .sql import upload_all_reports

def wait_random(min_sec=1, max_sec=2):
    time.sleep(random.uniform(min_sec, max_sec))

def get_arizona_time():
    return datetime.datetime.now(pytz.timezone('US/Arizona'))

def format_date(dt):
    return f"{dt.month}.{dt.day}.{dt.year}"

def format_date_short(dt):
    return f"{dt.month:02d}.{dt.day:02d}.{dt.year-2000:02d}"

def get_date_info():
    az_now = get_arizona_time()
    return {
        "today_file": format_date(az_now),
        "today_short": format_date_short(az_now),
        "today_us": az_now.strftime("%m/%d/%Y"),
        "today_date": az_now.date(),
        "created_at": az_now.strftime("%I:%M %p")
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
        page.wait_for_load_state("domcontentloaded", timeout=15000)
        wait_random(2, 3)
        return True
    except:
        wait_random(3, 4)
        return True

def find_export_button(page):
    selectors = [
        "button:has-text('Export')",
        "[data-cy='button']:has-text('Export')"
    ]
    for selector in selectors:
        try:
            element = page.locator(selector).first
            if element.is_visible():
                return element
        except:
            continue
    return None

def download_financial_csv(page, filename, download_dir):
    try:
        print(f"Looking for Export button...")
        export_btn = find_export_button(page)
        if not export_btn:
            print("Export button not found")
            return False
        print("Found Export button, clicking...")
        with page.expect_download(timeout=30000) as download_info:
            export_btn.click()
            wait_random(2, 3)
            print("Looking for CSV option...")
            csv_btn = page.locator("text=CSV").first
            try:
                csv_btn.wait_for(state="visible", timeout=5000)
                csv_btn.click()
                print("CSV option clicked")
            except:
                print("CSV option not found, using default")
        download = download_info.value
        file_path = os.path.join(download_dir, filename)
        download.save_as(file_path)
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            print(f"Downloaded: {filename} ({os.path.getsize(file_path)} bytes)")
            return True
        return False
    except Exception as e:
        print(f"Download error: {e}")
        return False

def download_ro_csv(page, filename, download_dir):
    try:
        print(f"Looking for Export button...")
        export_btn = find_export_button(page)
        if not export_btn:
            print("Export button not found")
            return False
        print("Found Export button, clicking...")
        with page.expect_download(timeout=30000) as download_info:
            export_btn.click()
            wait_random(1, 2)
        download = download_info.value
        file_path = os.path.join(download_dir, filename)
        download.save_as(file_path)
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            print(f"Downloaded: {filename} ({os.path.getsize(file_path)} bytes)")
            return True
        return False
    except Exception as e:
        print(f"Download error: {e}")
        return False

def create_empty_csv(filename, directory, location_name, report_date, created_at):
    try:
        file_path = os.path.join(directory, filename)
        headers = ['Marketing Source', 'Total Sales', 'RO Count', 'New Sales', 'New RO Count',
                  'Repeat Sales', 'Repeat RO Count', 'Average RO', 'GP $', 'GP %', 'Close Ratio',
                  'Location', 'Report_Date', 'Created At']
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
    try:
        page.goto("https://shop.tekmetric.com/", timeout=30000)
        wait_random(2, 3)
        page.fill("#email", os.getenv("TEKMETRIC_EMAIL", "arslan.thaheem@xvantech.com"))
        wait_random(1, 2)
        page.fill("#password", os.getenv("TEKMETRIC_PASSWORD", "$$xat123!@#"))
        wait_random(1, 2)
        page.click("button[data-cy='button']:has-text('Sign In')")
        simple_page_wait(page)
        print("Login completed")
        return True
    except Exception as e:
        print(f"Login failed: {e}")
        return False

def download_financial_report(page, dirs, dates):
    try:
        print("Downloading Financial Report...")
        financial_url = build_financial_url(dates['today_date'])
        print(f"Going to: {financial_url}")
        page.goto(financial_url, timeout=30000)
        simple_page_wait(page)
        filename = f"{dates['today_file']}.csv"
        success = download_financial_csv(page, filename, dirs["financial"])
        if success:
            print("Processing financial report...")
            process_financial_report(dates['created_at'])
            print("Financial report processed successfully")
        else:
            print("Financial report download failed")
        return success
    except Exception as e:
        print(f"Financial report error: {e}")
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
        for location in locations:
            try:
                print(f"Processing {location['name']}...")
                url = build_ro_url(location['shop_id'], dates['today_date'])
                print(f"Going to: {url}")
                page.goto(url, timeout=30000)
                simple_page_wait(page)
                filename = f"{location['name'].replace(' ', '-')}-{dates['today_short']}.csv"
                success = download_ro_csv(page, filename, dirs["ro"])
                if success:
                    process_ro_marketing_report(location['name'], filename, dates['created_at'])
                    success_count += 1
                    print(f"Successfully processed {location['name']}")
                else:
                    print(f"Download failed for {location['name']}, creating empty file")
                    create_empty_csv(filename, dirs["ro"], location['name'], dates['today_us'], dates['created_at'])
                    process_ro_marketing_report(location['name'], filename, dates['created_at'])
                    success_count += 1
                wait_random(1, 2)
            except Exception as e:
                print(f"Error with {location['name']}: {e}")
                filename = f"{location['name'].replace(' ', '-')}-{dates['today_short']}.csv"
                create_empty_csv(filename, dirs["ro"], location['name'], dates['today_us'], dates['created_at'])
                process_ro_marketing_report(location['name'], filename, dates['created_at'])
                success_count += 1
        print(f"RO processing completed: {success_count}/6")
        return success_count >= 4
    except Exception as e:
        print(f"RO reports error: {e}")
        return False

def main():
    print("Starting Tekmetric hourly automation...")
    dirs = setup_directories()
    dates = get_date_info()
    print(f"Processing date: {dates['today_us']} at {dates['created_at']}")
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
            if not login_to_tekmetric(page):
                print("Login failed, aborting")
                return False
            financial_success = download_financial_report(page, dirs, dates)
            ro_success = download_ro_reports(page, dirs, dates)
            if ro_success:
                combine_ro_reports(dates['today_short'])
            verify_data_accuracy(dates['today_file'], dates['today_short'])
            upload_success = upload_all_reports()
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