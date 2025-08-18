import time
import datetime
import pytz
from app import main

TARGET_MINUTE = 50  # Run at the top of each hour (XX:50)

def get_arizona_time():
    """Get current Arizona time"""
    return datetime.datetime.now(pytz.timezone('US/Arizona'))

def run_automation():
    """Execute the automation and return success status"""
    arizona_time = get_arizona_time()
    print(f"\n🚀 AUTOMATION STARTED")
    print(f"Time: {arizona_time.strftime('%Y-%m-%d %I:%M:%S %p')} AZ")
    print("=" * 60)
    
    try:
        success = main()
        
        finish_time = get_arizona_time()
        duration = finish_time - arizona_time
        
        print("\n" + "=" * 60)
        if success:
            print("✅ AUTOMATION COMPLETED SUCCESSFULLY")
        else:
            print("⚠️  AUTOMATION COMPLETED WITH ERRORS")
        
        print(f"Duration: {duration.total_seconds():.1f} seconds")
        print(f"Finished: {finish_time.strftime('%Y-%m-%d %I:%M:%S %p')} AZ")
        print("=" * 60)
        
        return success
        
    except Exception as e:
        print(f"\n❌ AUTOMATION FAILED: {e}")
        print(f"Failed at: {get_arizona_time().strftime('%Y-%m-%d %I:%M:%S %p')} AZ")
        
        import traceback
        print("\nError Details:")
        traceback.print_exc()
        print("=" * 60)
        return False

def run_daily_fix():
    """Execute the daily fix automation at 7 AM"""
    try:
        from fix import main as fix_main
        arizona_time = get_arizona_time()
        print(f"\n🔧 DAILY FIX STARTED")
        print(f"Time: {arizona_time.strftime('%Y-%m-%d %I:%M:%S %p')} AZ")
        print("=" * 60)
        
        success = fix_main()
        
        finish_time = get_arizona_time()
        duration = finish_time - arizona_time
        
        print("\n" + "=" * 60)
        if success:
            print("✅ DAILY FIX COMPLETED SUCCESSFULLY")
        else:
            print("⚠️  DAILY FIX COMPLETED WITH ERRORS")
        
        print(f"Duration: {duration.total_seconds():.1f} seconds")
        print(f"Finished: {finish_time.strftime('%Y-%m-%d %I:%M:%S %p')} AZ")
        print("=" * 60)
        
        return success
    except Exception as e:
        print(f"❌ DAILY FIX FAILED: {e}")
        import traceback
        print("\nError Details:")
        traceback.print_exc()
        print("=" * 60)
        return False

def calculate_next_run(current_time):
    """Calculate next scheduled run time"""
    next_run = current_time.replace(minute=TARGET_MINUTE, second=0, microsecond=0)
    if current_time.minute >= TARGET_MINUTE:
        next_run += datetime.timedelta(hours=1)
    return next_run

def main_scheduler():
    """Main scheduler loop - runs automation every hour at :50 and daily fix at 7:00 AM"""
    print("\n" + "="*60)
    print("🕒 TEKMETRIC DUAL AUTOMATION SCHEDULER")
    print("="*60)
    print(f"Hourly Schedule: Every hour at :{TARGET_MINUTE:02d} Arizona Time")
    print(f"Daily Fix Schedule: Every day at 7:00 AM Arizona Time")
    
    current_time = get_arizona_time()
    next_run = calculate_next_run(current_time)
    
    print(f"Current time: {current_time.strftime('%Y-%m-%d %I:%M:%S %p')} AZ")
    print(f"Next hourly run: {next_run.strftime('%Y-%m-%d %I:%M:%S %p')} AZ")
    print("="*60)
    print("Monitoring... (Press Ctrl+C to stop)")
    
    last_run_hour = None
    last_run_date = None
    last_fix_date = None
    
    while True:
        try:
            current_time = get_arizona_time()
            current_date = current_time.date()
            current_hour = current_time.hour
            
            # Check if it's time for daily fix (7:00 AM)
            should_run_fix = (
                current_time.hour == 7 and 
                current_time.minute == 0 and 
                current_time.second < 30 and
                last_fix_date != current_date  # Only once per day
            )
            
            if should_run_fix:
                print(f"\n🕖 Daily fix triggered at {current_time.strftime('%I:%M:%S %p')}")
                success = run_daily_fix()
                last_fix_date = current_date
                if success:
                    print(f"✅ Daily fix completed. Next fix: tomorrow at 7:00 AM")
                else:
                    print(f"⚠️  Daily fix had errors. Next retry: tomorrow at 7:00 AM")
            
            # Check if it's time for hourly run (:50 minutes)
            should_run = (
                current_time.minute == TARGET_MINUTE and 
                current_time.second < 30 and  # Run only in first 30 seconds of the minute
                (last_run_hour != current_hour or last_run_date != current_date)
            )
            
            if should_run:
                print(f"\n⏰ Scheduled hourly run triggered at {current_time.strftime('%I:%M:%S %p')}")
                
                success = run_automation()
                last_run_hour = current_hour
                last_run_date = current_date
                
                # Calculate next run
                next_run = calculate_next_run(current_time)
                
                if success:
                    print(f"✅ Next scheduled run: {next_run.strftime('%I:%M %p')}")
                else:
                    print(f"⚠️  Automation had errors. Next retry: {next_run.strftime('%I:%M %p')}")
            
            # Status update every 10 minutes (but not during run minutes)
            elif (current_time.minute % 10 == 0 and 
                  current_time.minute != TARGET_MINUTE and 
                  current_time.minute != 0 and
                  current_time.second < 30):
                
                next_run = calculate_next_run(current_time)
                
                if last_run_hour == current_hour and last_run_date == current_date:
                    print(f"✅ Completed this hour. Next run: {next_run.strftime('%I:%M %p')} "
                          f"({current_time.strftime('%I:%M %p')} now)")
                else:
                    minutes_until = int((next_run - current_time).total_seconds() / 60)
                    print(f"⏳ Waiting for next run: {next_run.strftime('%I:%M %p')} "
                          f"({minutes_until} minutes)")
            
            # Check every 30 seconds
            time.sleep(30)
            
        except KeyboardInterrupt:
            print(f"\n\n🛑 Scheduler stopped by user at {get_arizona_time().strftime('%I:%M:%S %p')} AZ")
            break
        except Exception as e:
            print(f"\n❌ Scheduler error: {e}")
            print("Continuing in 60 seconds...")
            time.sleep(60)

def test_immediate_run():
    """Test function to run automation immediately"""
    print("\n" + "="*60)
    print("🧪 IMMEDIATE TEST RUN")
    print("="*60)
    print("Running automation immediately for testing...")
    
    success = run_automation()
    
    if success:
        print("\n✅ Test completed successfully!")
    else:
        print("\n⚠️  Test completed with errors!")
    
    print("Use 'python scheduler.py' to start the dual scheduler")
    return success

def test_daily_fix():
    """Test function to run daily fix immediately"""
    print("\n" + "="*60)
    print("🔧 IMMEDIATE DAILY FIX TEST")
    print("="*60)
    print("Running daily fix immediately for testing...")
    
    success = run_daily_fix()
    
    if success:
        print("\n✅ Daily fix test completed successfully!")
    else:
        print("\n⚠️  Daily fix test completed with errors!")
    
    return success

def show_status():
    """Show current status and next run time"""
    current_time = get_arizona_time()
    next_run = calculate_next_run(current_time)
    
    print("\n📊 DUAL SCHEDULER STATUS")
    print("=" * 40)
    print(f"Current time: {current_time.strftime('%Y-%m-%d %I:%M:%S %p')} AZ")
    print(f"Next hourly run: {next_run.strftime('%Y-%m-%d %I:%M:%S %p')} AZ")
    print(f"Schedule: Every hour at :{TARGET_MINUTE:02d}")
    print(f"Daily fix: Every day at 7:00 AM")
    print("=" * 40)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == "--test":
            test_immediate_run()
        elif command == "--test-fix":
            test_daily_fix()
        elif command == "--status":
            show_status()
        elif command == "--help":
            print("\n📖 SCHEDULER COMMANDS")
            print("=" * 40)
            print("python scheduler.py            - Start dual scheduler")
            print("python scheduler.py --test     - Run hourly automation immediately")
            print("python scheduler.py --test-fix - Run daily fix immediately")
            print("python scheduler.py --status   - Show current status")
            print("python scheduler.py --help     - Show this help")
            print("=" * 40)
        else:
            print(f"Unknown command: {command}")
            print("Use --help to see available commands")
    else:
        main_scheduler()
