import time
import datetime
import pytz
from .app import main

START_HOUR = 0  # 12:00 AM
END_HOUR = 23  # 11:00 PM


def get_arizona_time():
    return datetime.datetime.now(pytz.timezone('US/Arizona'))


def run_automation():
    arizona_time = get_arizona_time()
    print(f"HOURLY AUTOMATION STARTED at {arizona_time.strftime('%Y-%m-%d %I:%M:%S %p')} AZ")
    print("=" * 50)
    try:
        success = main()
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
    print(f"Target hours: {START_HOUR:02d}:00 to {END_HOUR:02d}:00 Arizona Time")
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
            should_run = (
                START_HOUR <= current_hour <= END_HOUR and
                (last_run_hour != current_hour or last_run_date != current_date)
            )
            if should_run:
                print(f"Running automation at {current_hour:02d}:00...")
                run_automation()
                last_run_hour = current_hour
                last_run_date = current_date
            elif current_time.minute % 10 == 0:
                print(f"Waiting for next hour. Current: {current_time.strftime('%I:%M %p')}")
            time.sleep(60)
        except KeyboardInterrupt:
            print("\nScheduler stopped")
            break
        except Exception as e:
            print(f"Scheduler error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main_scheduler() 