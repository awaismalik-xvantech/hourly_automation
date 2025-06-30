import time
import datetime
import pytz
from app import main

# Run every hour at the top of the hour (XX:00)
TARGET_MINUTE = 0

def get_arizona_time():
    return datetime.datetime.now(pytz.timezone('US/Arizona'))

def run_automation():
    arizona_time = get_arizona_time()
    print(f"HOURLY AUTOMATION STARTED at {arizona_time.strftime('%Y-%m-%d %I:%M:%S %p')} AZ")
    print("=" * 50)
    
    try:
        success = main()  # Remove headless parameter
        
        finish_time = get_arizona_time()
        if success:
            print("HOURLY AUTOMATION COMPLETED SUCCESSFULLY")
            print(f"Finished at: {finish_time.strftime('%Y-%m-%d %I:%M:%S %p')} AZ")
        else:
            print("HOURLY AUTOMATION COMPLETED WITH ERRORS")
            print(f"Finished at: {finish_time.strftime('%Y-%m-%d %I:%M:%S %p')} AZ")
        
        print("=" * 50)
        return success
        
    except Exception as e:
        print(f"HOURLY AUTOMATION FAILED: {e}")
        print(f"Failed at: {get_arizona_time().strftime('%Y-%m-%d %I:%M:%S %p')} AZ")
        print("=" * 50)
        return False

def main_scheduler():
    print("TEKMETRIC HOURLY AUTOMATION SCHEDULER")
    print(f"Target: Every hour at :{TARGET_MINUTE:02d} Arizona Time")
    
    current_time = get_arizona_time()
    print(f"Current time: {current_time.strftime('%Y-%m-%d %I:%M:%S %p')} AZ")
    print("Checking every minute...")
    print("=" * 50)
    
    last_run_hour = None
    last_run_date = None
    
    while True:
        try:
            current_time = get_arizona_time()
            current_date = current_time.date()
            current_hour = current_time.hour
            
            # Check if it's time to run (top of the hour and haven't run this hour today)
            should_run = (
                current_time.minute == TARGET_MINUTE and 
                (last_run_hour != current_hour or last_run_date != current_date)
            )
            
            if should_run:
                print(f"Running hourly automation at {current_time.strftime('%I:%M %p')}...")
                success = run_automation()
                last_run_hour = current_hour
                last_run_date = current_date
                
                if success:
                    print(f"Next run: {(current_time + datetime.timedelta(hours=1)).strftime('%I:%M %p')}")
                else:
                    print("Automation failed, will retry next hour")
            
            # Status update every 10 minutes
            elif current_time.minute % 10 == 0:
                next_run = current_time.replace(minute=0, second=0, microsecond=0)
                if current_time.minute > 0:
                    next_run += datetime.timedelta(hours=1)
                
                if last_run_hour == current_hour and last_run_date == current_date:
                    print(f"Already ran this hour. Next: {next_run.strftime('%I:%M %p')}")
                else:
                    print(f"Waiting for next hour. Next run: {next_run.strftime('%I:%M %p')} (Current: {current_time.strftime('%I:%M %p')})")
            
            time.sleep(60)  # Check every minute
            
        except KeyboardInterrupt:
            print("\nHourly scheduler stopped")
            break
        except Exception as e:
            print(f"Scheduler error: {e}")
            time.sleep(60)

def test_immediate_run():
    """Function to test automation immediately without waiting for schedule"""
    print("TESTING IMMEDIATE HOURLY AUTOMATION")
    print("=" * 50)
    run_automation()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_immediate_run()
    else:
        main_scheduler()
