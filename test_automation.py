import datetime
import pytz
import os
from app import main

def get_arizona_time():
    return datetime.datetime.now(pytz.timezone('US/Arizona'))

def check_environment():
    print("ENVIRONMENT CHECK")
    print("=" * 40)
    
    current_dir = os.getcwd()
    print(f"Working directory: {current_dir}")
    
    required_files = ['app.py', 'reports.py', 'sql.py', 'scheduler.py']
    for file in required_files:
        status = "✓" if os.path.exists(file) else "✗"
        print(f"{status} {file}")
    
    try:
        test_file = os.path.join(current_dir, "test_write.tmp")
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        print("✓ Write permissions OK")
    except Exception as e:
        print(f"✗ Write permission error: {e}")
    
    # Check environment variables
    env_vars = ['TEKMETRIC_EMAIL', 'TEKMETRIC_PASSWORD', 'SQL_SERVER', 'SQL_DATABASE', 'SQL_USERNAME', 'SQL_PASSWORD']
    print("\nEnvironment Variables:")
    for var in env_vars:
        value = os.getenv(var, 'Not Set')
        if 'PASSWORD' in var:
            display_value = '***' if value != 'Not Set' else 'Not Set'
        else:
            display_value = value
        status = "✓" if value != 'Not Set' else "✗"
        print(f"{status} {var}: {display_value}")
    
    print("=" * 40)

def show_results():
    print("\nFILES CREATED:")
    
    current_dir = os.getcwd()
    az_time = get_arizona_time()
    
    financial_dir = os.path.join(current_dir, "Financial Reports")
    if os.path.exists(financial_dir):
        files = os.listdir(financial_dir)
        print(f"Financial Reports ({len(files)} files):")
        for f in sorted(files):
            size = os.path.getsize(os.path.join(financial_dir, f))
            print(f"  - {f} ({size} bytes)")
    else:
        print("No Financial Reports directory")
    
    ro_dir = os.path.join(current_dir, "RO Reports")
    if os.path.exists(ro_dir):
        files = os.listdir(ro_dir)
        print(f"RO Reports ({len(files)} files):")
        for f in sorted(files):
            size = os.path.getsize(os.path.join(ro_dir, f))
            print(f"  - {f} ({size} bytes)")
    else:
        print("No RO Reports directory")

def test_sql_connection():
    print("\nTESTING SQL CONNECTION:")
    try:
        from sql import create_connection
        conn = create_connection()
        if conn:
            print("✓ SQL Server connection successful")
            
            # Test table access
            cursor = conn.cursor()
            
            # Check if new tables exist
            cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME IN ('custom_financials_2', 'ro_marketing_2')")
            table_count = cursor.fetchone()[0]
            
            if table_count == 2:
                print("✓ Both target tables (custom_financials_2, ro_marketing_2) exist")
            elif table_count == 1:
                print("⚠ Only one target table exists")
            else:
                print("⚠ Target tables do not exist (will be created during upload)")
            
            conn.close()
            return True
        else:
            print("✗ SQL Server connection failed")
            return False
    except Exception as e:
        print(f"✗ SQL connection error: {e}")
        return False

def show_hourly_schedule():
    print("\nHOURLY SCHEDULE INFO:")
    az_time = get_arizona_time()
    print(f"Current Arizona Time: {az_time.strftime('%Y-%m-%d %I:%M:%S %p')}")
    print(f"Next scheduled run: {az_time.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=1)}")
    print(f"Created_At value for this run: {az_time.strftime('%I %p').lstrip('0')}")
    
    yesterday = az_time - datetime.timedelta(days=1)
    print(f"Processing data for: {yesterday.strftime('%m/%d/%Y')} (yesterday)")

def test_automation():
    arizona_time = get_arizona_time()
    print(f"TESTING HOURLY AUTOMATION")
    print(f"Arizona Time: {arizona_time.strftime('%Y-%m-%d %I:%M:%S %p')}")
    print("=" * 50)
    
    check_environment()
    test_sql_connection()
    show_hourly_schedule()
    
    try:
        print("\n" + "=" * 50)
        print("STARTING HOURLY AUTOMATION TEST...")
        print("=" * 50)
        
        # Run without headless parameter
        success = main()
        
        finish_time = get_arizona_time()
        print("\n" + "=" * 50)
        
        if success:
            print("TEST HOURLY AUTOMATION COMPLETED SUCCESSFULLY!")
            print("✓ Financial and RO reports downloaded")
            print("✓ Data processed with Created_At column")
            print("✓ Data uploaded to custom_financials_2 and ro_marketing_2")
        else:
            print("TEST HOURLY AUTOMATION COMPLETED WITH ERRORS!")
            print("✗ Some steps failed - check logs above")
        
        print(f"Finished at: {finish_time.strftime('%Y-%m-%d %I:%M:%S %p')} AZ")
        
        show_results()
        
        # Show database verification
        print("\nDATABASE VERIFICATION:")
        try:
            from sql import create_connection
            conn = create_connection()
            if conn:
                cursor = conn.cursor()
                yesterday = (get_arizona_time() - datetime.timedelta(days=1)).strftime("%m/%d/%Y")
                current_hour = get_arizona_time().strftime("%I %p").lstrip('0')
                
                # Check financial records
                cursor.execute("SELECT COUNT(*) FROM [custom_financials_2] WHERE Report_Date = %s AND Created_At = %s", 
                             (yesterday, current_hour))
                financial_count = cursor.fetchone()[0]
                print(f"  custom_financials_2: {financial_count} records for {yesterday} at {current_hour}")
                
                # Check RO records
                cursor.execute("SELECT COUNT(*) FROM [ro_marketing_2] WHERE Report_Date = %s AND Created_At = %s", 
                             (yesterday, current_hour))
                ro_count = cursor.fetchone()[0]
                print(f"  ro_marketing_2: {ro_count} records for {yesterday} at {current_hour}")
                
                # Show locations
                cursor.execute("SELECT DISTINCT Location FROM [ro_marketing_2] WHERE Report_Date = %s AND Created_At = %s", 
                             (yesterday, current_hour))
                locations = [row[0] for row in cursor.fetchall()]
                print(f"  Locations processed: {', '.join(locations) if locations else 'None'}")
                
                conn.close()
        except Exception as e:
            print(f"  Database verification error: {e}")
        
    except Exception as e:
        print(f"\nTEST HOURLY AUTOMATION FAILED: {e}")
        print(f"Failed at: {get_arizona_time().strftime('%Y-%m-%d %I:%M:%S %p')} AZ")
        
        import traceback
        print("\nERROR DETAILS:")
        traceback.print_exc()

def show_usage():
    print("HOURLY AUTOMATION TEST USAGE:")
    print("=" * 40)
    print("python test_automation.py           - Run full test")
    print("python scheduler.py --test          - Test via scheduler")
    print("python scheduler.py                 - Start hourly scheduler")
    print("=" * 40)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        show_usage()
    else:
        test_automation()
