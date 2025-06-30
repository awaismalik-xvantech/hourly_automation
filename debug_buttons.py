import os
import time
import random
import datetime
import pytz
from playwright.sync_api import sync_playwright

def wait_random(min_sec=1, max_sec=2):
    time.sleep(random.uniform(min_sec, max_sec))

def get_arizona_time():
    return datetime.datetime.now(pytz.timezone('US/Arizona'))

def get_yesterday():
    return get_arizona_time() - datetime.timedelta(days=1)

def get_current_hour_12format():
    """Get current Arizona time in 12-hour format for Created_At column"""
    az_now = get_arizona_time()
    return az_now.strftime("%I %p").lstrip('0')  # Remove leading zero and add AM/PM

def build_ro_url(shop_id, date_obj):
    arizona_tz = pytz.timezone('US/Arizona')
    start_dt = arizona_tz.localize(datetime.datetime.combine(date_obj, datetime.time(0, 0, 0)))
    end_dt = arizona_tz.localize(datetime.datetime.combine(date_obj, datetime.time(23, 59, 59)))
    
    start_str = start_dt.strftime('%Y-%m-%dT%H:%M:%S.000-07:00').replace(':', '%3A')
    end_str = end_dt.strftime('%Y-%m-%dT%H:%M:%S.999-07:00').replace(':', '%3A')
    
    return f"https://shop.tekmetric.com/admin/org/464/reports/customer/ro-marketing-source?start={start_str}&end={end_str}&shopIds={shop_id}"

def debug_page_elements(page, page_name):
    print(f"\n=== DEBUGGING {page_name} ===")
    
    # Take screenshot
    screenshot_path = f"/app/debug_{page_name.lower().replace(' ', '_')}.png"
    page.screenshot(path=screenshot_path)
    print(f"Screenshot saved: {screenshot_path}")
    
    # Check for various button selectors
    export_selectors = [
        "button[data-cy='button']",
        "button:has-text('Export')",
        "button.MuiButtonBase-root",
        "[data-cy='button']:has-text('Export')",
        "button.MuiButtonBase-root:has-text('Export')",
        "*[role='button']:has-text('Export')"
    ]
    
    print("Checking export button selectors:")
    for i, selector in enumerate(export_selectors):
        try:
            elements = page.locator(selector)
            count = elements.count()
            print(f"  {i+1}. {selector}: {count} elements found")
            
            if count > 0:
                for j in range(min(count, 3)):  # Check first 3 elements
                    element = elements.nth(j)
                    visible = element.is_visible()
                    text = element.text_content() if visible else "N/A"
                    print(f"     Element {j+1}: visible={visible}, text='{text}'")
        except Exception as e:
            print(f"  {i+1}. {selector}: ERROR - {e}")
    
    # Check for CSV selectors
    csv_selectors = [
        "button:has-text('CSV')",
        "text=CSV",
        "button.MuiButtonBase-root:has-text('CSV')",
        "[role='button']:has-text('CSV')"
    ]
    
    print("\nChecking CSV button selectors:")
    for i, selector in enumerate(csv_selectors):
        try:
            elements = page.locator(selector)
            count = elements.count()
            print(f"  {i+1}. {selector}: {count} elements found")
            
            if count > 0:
                element = elements.first
                visible = element.is_visible()
                text = element.text_content() if visible else "N/A"
                print(f"     First element: visible={visible}, text='{text}'")
        except Exception as e:
            print(f"  {i+1}. {selector}: ERROR - {e}")
    
    # Save page content for analysis
    content_path = f"/app/debug_{page_name.lower().replace(' ', '_')}_content.html"
    with open(content_path, 'w', encoding='utf-8') as f:
        f.write(page.content())
    print(f"Page content saved: {content_path}")

def main():
    print("HOURLY AUTOMATION BUTTON DETECTION DEBUG TOOL")
    print("=" * 60)
    
    arizona_time = get_arizona_time()
    yesterday = get_yesterday()
    yesterday_date = yesterday.date()
    current_hour = get_current_hour_12format()
    
    print(f"Current Arizona Time: {arizona_time.strftime('%Y-%m-%d %I:%M:%S %p')}")
    print(f"Processing data for: {yesterday.strftime('%m/%d/%Y')} (yesterday)")
    print(f"Created_At value: {current_hour}")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # Make visible for debugging
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        
        context = browser.new_context(
            accept_downloads=True,
            viewport={"width": 1920, "height": 1080}
        )
        
        page = context.new_page()
        
        try:
            print("Logging into Tekmetric...")
            page.goto("https://shop.tekmetric.com/", timeout=30000)
            wait_random(2, 3)
            
            page.fill("#email", os.getenv("TEKMETRIC_EMAIL", "arslan.thaheem@xvantech.com"))
            wait_random(1, 2)
            page.fill("#password", os.getenv("TEKMETRIC_PASSWORD", "$$xat123!@#"))
            wait_random(1, 2)
            
            page.click("button[data-cy='button']:has-text('Sign In')")
            page.wait_for_load_state("networkidle")
            wait_random(4, 5)
            
            print("Login completed")
            
            # Debug Financial Report page
            print("\n" + "="*60)
            print("DEBUGGING FINANCIAL REPORT PAGE")
            print("="*60)
            
            page.goto("https://shop.tekmetric.com/admin/org/464/reports/financial", timeout=30000)
            wait_random(4, 5)
            
            # Click Custom Financial
            custom_btn = page.locator("text=Custom Financial").first
            if custom_btn.is_visible():
                custom_btn.click()
                wait_random(4, 5)
            
            # Click COMPARE
            compare_btn = page.locator("button:has-text('COMPARE')").first
            if compare_btn.is_visible():
                compare_btn.click()
                wait_random(2, 3)
                
                # Click Yesterday
                yesterday_btn = page.locator("text=Yesterday").first
                if yesterday_btn.is_visible():
                    yesterday_btn.click()
                    wait_random(4, 5)
            
            debug_page_elements(page, "Financial Report")
            
            # Debug RO Marketing page
            print("\n" + "="*60)
            print("DEBUGGING RO MARKETING PAGE")
            print("="*60)
            
            # Go to Mesa Broadway RO page
            ro_url = build_ro_url("10738", yesterday_date)  # Mesa Broadway
            print(f"Navigating to RO URL: {ro_url}")
            
            page.goto(ro_url, timeout=30000)
            page.wait_for_load_state("networkidle")
            wait_random(5, 6)
            
            debug_page_elements(page, "RO Marketing")
            
            print("\n" + "="*60)
            print("HOURLY DEBUG COMPLETED")
            print(f"Created_At Hour: {current_hour}")
            print("Check the saved screenshots and HTML files in /app/")
            print("="*60)
            
            # Keep browser open for manual inspection
            input("Press Enter to close browser...")
            
        except Exception as e:
            print(f"Debug error: {e}")
            page.screenshot(path="/app/debug_error.png")
        
        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    main()