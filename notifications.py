import os
import csv
import datetime
import pytz
import json
import requests
import msal

EMAIL_CONFIG = {
    'tenant_id': os.getenv('TENANT_ID', '55e7e814-58a0-4b3e-9915-66cd8d4adbd4'),
    'client_id': os.getenv('CLIENT_ID', 'ed7a0d5e-846f-4316-96cd-67fdfb915065'),
    'client_secret': os.getenv('CLIENT_SECRET', '66s8Q~Ybe2GiSph95lsbzcZaklvnCqkjjXj.aaDT'),
    'sender_email': os.getenv('SENDER_EMAIL', 'awais@xvantech.com'),
    'recipient_emails': [
        'awais@xvantech.com',
        'humayun@xvantech.com',
        'maaz@xvantech.com'
    ],
    'authority': os.getenv('AUTHORITY', 'https://login.microsoftonline.com/xvantech.com')
}

def get_arizona_time():
    """Get current Arizona time"""
    return datetime.datetime.now(pytz.timezone('US/Arizona'))

def format_date(dt):
    """Format date as M.D.YYYY"""
    return f"{dt.month}.{dt.day}.{dt.year}"

def format_date_short(dt):
    """Format date as MM.DD.YY"""
    return f"{dt.month:02d}.{dt.day:02d}.{dt.year-2000:02d}"

def get_current_hour_info():
    """Get current hour information for file paths and display"""
    az_now = get_arizona_time()
    return {
        'hour_24': az_now.hour,
        'hour_12': az_now.strftime("%I %p").lstrip('0'),
        'hour_padded': f"H{az_now.hour:02d}",
        'timestamp': az_now.strftime('%Y-%m-%d %I:%M:%S %p') + ' AZ'
    }

def read_csv_safe(filepath):
    """Safely read CSV file and return data"""
    try:
        if not os.path.exists(filepath):
            return None, f"File not found: {filepath}"
        
        if os.path.getsize(filepath) == 0:
            return None, f"File is empty: {filepath}"
        
        with open(filepath, 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            rows = list(reader)
        
        if len(rows) <= 1:
            return None, f"No data rows in file: {filepath}"
        
        return rows, None
    except Exception as e:
        return None, f"Error reading {filepath}: {str(e)}"

def check_hourly_file_existence():
    """Check if required hourly files exist and get basic info"""
    today = get_arizona_time()
    today_file = format_date(today)
    today_short = format_date_short(today)
    hour_info = get_current_hour_info()
    
    base_path = os.getcwd()
    financial_path = os.path.join(base_path, "Financial Reports", f"{today_file}_{hour_info['hour_padded']}.csv")
    ro_path = os.path.join(base_path, "RO Reports", f"TekmetricGemba_RO_{today_short}_{hour_info['hour_padded']}.csv")
    
    file_status = {
        'financial_exists': os.path.exists(financial_path),
        'ro_exists': os.path.exists(ro_path),
        'financial_path': financial_path,
        'ro_path': ro_path,
        'financial_size': 0,
        'ro_size': 0,
        'hour_info': hour_info
    }
    
    if file_status['financial_exists']:
        file_status['financial_size'] = os.path.getsize(financial_path)
    
    if file_status['ro_exists']:
        file_status['ro_size'] = os.path.getsize(ro_path)
    
    return file_status

def analyze_financial_data_hourly(filepath):
    """Analyze financial report data for hourly runs"""
    rows, error = read_csv_safe(filepath)
    if error:
        return {
            'success': False,
            'error': error,
            'car_count': 0,
            'locations': 0,
            'total_sales': 0
        }
    
    try:
        headers = rows[0]
        data_rows = rows[1:]
        
        car_count = 0
        total_sales = 0
        
        # Find the Car Count column index
        car_count_col_idx = None
        for i, header in enumerate(headers):
            if 'Car Count' in str(header) or 'Car_Count' in str(header):
                car_count_col_idx = i
                break
        
        if car_count_col_idx is not None:
            # Look for TOTAL row (first row should be TOTAL)
            for row in data_rows:
                if len(row) > car_count_col_idx:
                    first_col = str(row[0]).strip()
                    if first_col == 'TOTAL':
                        try:
                            car_count = int(float(row[car_count_col_idx]))
                            break
                        except:
                            continue
        
        # Count locations (excluding TOTAL row)
        locations = len([row for row in data_rows if not str(row[0]).strip() == 'TOTAL'])
        
        print(f"✅ Financial analysis: {car_count} car count, {locations} locations")
        
        return {
            'success': True,
            'car_count': car_count,
            'locations': locations,
            'total_sales': total_sales,
            'record_count': len(data_rows)
        }
    
    except Exception as e:
        print(f"❌ Financial analysis error: {e}")
        return {
            'success': False,
            'error': f"Analysis error: {str(e)}",
            'car_count': 0,
            'locations': 0,
            'total_sales': 0
        }

def analyze_ro_data_hourly(filepath):
    """Analyze RO marketing report data for hourly runs"""
    rows, error = read_csv_safe(filepath)
    if error:
        return {
            'success': False,
            'error': error,
            'total_ro_count': 0,
            'locations': 0,
            'marketing_sources': 0
        }
    
    try:
        headers = rows[0]
        data_rows = rows[1:]
        
        # Find the main RO Count column
        ro_count_idx = None
        location_idx = None
        
        for i, header in enumerate(headers):
            header_str = str(header).strip()
            # Look for exact "RO Count" column (not "New RO Count" or "Repeat RO Count")
            if header_str == 'RO Count':
                ro_count_idx = i
                break
        
        for i, header in enumerate(headers):
            header_str = str(header).strip()
            if 'Location' in header_str:
                location_idx = i
                break
        
        if ro_count_idx is None:
            return {
                'success': False,
                'error': "Main RO Count column not found",
                'total_ro_count': 0,
                'locations': 0,
                'marketing_sources': 0
            }
        
        total_ro_count = 0
        locations = set()
        marketing_sources = set()
        
        # Process ALL RO data rows
        for row in data_rows:
            if len(row) > ro_count_idx:
                try:
                    ro_value = str(row[ro_count_idx]).strip()
                    if ro_value and ro_value != '0' and ro_value != '':
                        count = int(float(ro_value))
                        total_ro_count += count
                except:
                    continue
            
            # Track locations
            if location_idx is not None and len(row) > location_idx:
                if row[location_idx] and str(row[location_idx]).strip():
                    locations.add(str(row[location_idx]).strip())
            
            # Track marketing sources
            if len(row) > 0 and row[0] and str(row[0]).strip():
                marketing_sources.add(str(row[0]).strip())
        
        print(f"✅ RO analysis: {total_ro_count} RO count, {len(locations)} locations")
        
        return {
            'success': True,
            'total_ro_count': total_ro_count,
            'locations': len(locations),
            'location_names': list(locations),
            'marketing_sources': len(marketing_sources),
            'record_count': len(data_rows)
        }
    
    except Exception as e:
        print(f"❌ RO analysis error: {e}")
        return {
            'success': False,
            'error': f"Analysis error: {str(e)}",
            'total_ro_count': 0,
            'locations': 0,
            'marketing_sources': 0
        }

def check_database_connectivity():
    """Check if database connection is possible"""
    try:
        import pymssql
        
        SQL_CONFIG = {
            'server': os.getenv('SQL_SERVER', 'gembadb.database.windows.net'),
            'database': os.getenv('SQL_DATABASE', 'gemba'),
            'username': os.getenv('SQL_USERNAME', 'gembauser'),
            'password': os.getenv('SQL_PASSWORD', 'Karachi%007'),
            'port': int(os.getenv('SQL_PORT', '1433'))
        }
        
        conn = pymssql.connect(
            server=SQL_CONFIG['server'],
            user=SQL_CONFIG['username'],
            password=SQL_CONFIG['password'],
            database=SQL_CONFIG['database'],
            port=SQL_CONFIG['port'],
            timeout=10
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME IN ('custom_financials_2', 'ro_marketing_2')")
        table_count = cursor.fetchone()[0]
        conn.close()
        
        return {
            'success': True,
            'tables_exist': table_count == 2,
            'message': f"Database accessible, {table_count}/2 tables found"
        }
    
    except ImportError:
        return {
            'success': False,
            'message': "pymssql not available"
        }
    except Exception as e:
        return {
            'success': False,
            'message': f"Database connection failed: {str(e)}"
        }

def generate_hourly_report_summary():
    """Generate comprehensive hourly automation report - SIMPLIFIED VERSION"""
    current_time = get_arizona_time()
    hour_info = get_current_hour_info()
    
    # Check files
    file_status = check_hourly_file_existence()
    
    # Analyze data
    financial_analysis = None
    ro_analysis = None
    
    if file_status['financial_exists']:
        financial_analysis = analyze_financial_data_hourly(file_status['financial_path'])
    
    if file_status['ro_exists']:
        ro_analysis = analyze_ro_data_hourly(file_status['ro_path'])
    
    # Check database
    db_status = check_database_connectivity()
    
    # Determine overall status and capture ONLY REAL CRITICAL errors
    overall_success = True
    issues = []
    login_status = "Unknown"
    
    # 1. PRIMARY CHECK: Login failure (NO files exist)
    if not file_status['financial_exists'] and not file_status['ro_exists']:
        login_status = "❌ Failed - Login timeout"
        overall_success = False
        issues.append("Login failed: Cannot access Tekmetric system")
        
        return {
            'overall_success': overall_success,
            'report_date': current_time.strftime('%m/%d/%Y'),
            'execution_time': hour_info['timestamp'],
            'hour_info': hour_info,
            'file_status': file_status,
            'financial_analysis': financial_analysis,
            'ro_analysis': ro_analysis,
            'database_status': db_status,
            'data_validation': False,
            'issues': issues,
            'login_status': login_status
        }
    
    # 2. Login was successful if we have files
    login_status = "✅ Successful"
    
    # 3. CRITICAL: Database connectivity is REQUIRED for success
    if not db_status['success']:
        overall_success = False
        issues.append(f"Database connection failed: {db_status['message']}")
    
    # 4. File analysis failures (not file existence - that's checked by downloads)
    if file_status['financial_exists'] and financial_analysis and not financial_analysis['success']:
        overall_success = False
        issues.append(f"Financial data analysis failed: {financial_analysis['error']}")
    
    if file_status['ro_exists'] and ro_analysis and not ro_analysis['success']:
        overall_success = False
        issues.append(f"RO data analysis failed: {ro_analysis['error']}")
    
    # 5. ONLY validate data IF both have actual data (not zero)
    data_validation_performed = False
    if (financial_analysis and financial_analysis['success'] and financial_analysis['car_count'] > 0 and
        ro_analysis and ro_analysis['success'] and ro_analysis['total_ro_count'] > 0):
        
        data_validation_performed = True
        data_match = financial_analysis['car_count'] == ro_analysis['total_ro_count']
        
        if not data_match:
            overall_success = False
            issues.append(f"Data mismatch: Financial car count ({financial_analysis['car_count']}) != RO count ({ro_analysis['total_ro_count']})")
    
    # 6. Check ONLY for missing locations (indicates real download failures)
    if financial_analysis and financial_analysis['success'] and financial_analysis['locations'] < 6:
        overall_success = False
        issues.append(f"Financial download failure: only {financial_analysis['locations']}/6 locations found")
    
    if ro_analysis and ro_analysis['success'] and ro_analysis['locations'] < 6:
        overall_success = False
        issues.append(f"RO download failure: only {ro_analysis['locations']}/6 locations found")
    
    return {
        'overall_success': overall_success,
        'report_date': current_time.strftime('%m/%d/%Y'),
        'execution_time': hour_info['timestamp'],
        'hour_info': hour_info,
        'file_status': file_status,
        'financial_analysis': financial_analysis,
        'ro_analysis': ro_analysis,
        'database_status': db_status,
        'data_validation': data_validation_performed,
        'issues': issues,
        'login_status': login_status
    }

def create_hourly_email(report_data):
    """Create simple success or critical failure alert email for hourly runs - SIMPLIFIED"""
    try:
        hour_display = report_data['hour_info']['hour_12']
        
        if report_data['overall_success']:
            # Simple success message
            return f"Hourly automation at {hour_display} was successful"
        else:
            # Critical failure alert - ONLY real issues
            alert_message = f"🚨 HOURLY AUTOMATION FAILED at {hour_display}\n\n"
            
            # Only show REAL critical issues
            for issue in report_data['issues']:
                if "Login failed" in issue:
                    alert_message += "❌ LOGIN SYSTEM FAILURE\n"
                    alert_message += "   • Cannot access Tekmetric website\n"
                    alert_message += "   • Check internet connection and website status\n\n"
                
                elif "Database connection failed" in issue:
                    alert_message += "❌ SQL DATABASE UNREACHABLE\n"
                    alert_message += "   • Cannot upload data to database\n"
                    alert_message += "   • Contact Azure admin to whitelist IP\n\n"
                
                elif "Data mismatch" in issue:
                    alert_message += "❌ DATA VALIDATION FAILED\n"
                    alert_message += f"   • {issue}\n"
                    alert_message += "   • Check Excel files for accuracy\n\n"
                
                elif "download failure" in issue.lower():
                    alert_message += "❌ DOWNLOAD FAILURES\n"
                    alert_message += f"   • {issue}\n"
                    alert_message += "   • Some locations did not download properly\n\n"
                
                elif "analysis failed" in issue.lower():
                    alert_message += "❌ FILE PROCESSING ERROR\n"
                    alert_message += f"   • {issue}\n"
                    alert_message += "   • Check file format and content\n\n"
            
            return alert_message.strip()
            
    except Exception as e:
        # Fallback error message
        return f"🚨 HOURLY AUTOMATION FAILED at {hour_display}\n\n❌ SYSTEM ERROR\n   • {str(e)}"

def get_access_token():
    """Get Microsoft Graph access token"""
    try:
        app = msal.ConfidentialClientApplication(
            EMAIL_CONFIG['client_id'],
            authority=EMAIL_CONFIG['authority'],
            client_credential=EMAIL_CONFIG['client_secret']
        )
        
        scopes = ["https://graph.microsoft.com/.default"]
        result = app.acquire_token_silent(scopes, account=None)
        
        if not result:
            result = app.acquire_token_for_client(scopes=scopes)
        
        if "access_token" in result:
            return result["access_token"]
        else:
            print(f"Token acquisition failed: {result}")
            return None
    
    except Exception as e:
        print(f"Error getting access token: {e}")
        return None

def send_email(subject, body):
    """Send email using Microsoft Graph API with multi-recipient support"""
    try:
        access_token = get_access_token()
        if not access_token:
            return False, "Failed to get access token"
        
        # Use users endpoint instead of /me for application authentication
        url = f"https://graph.microsoft.com/v1.0/users/{EMAIL_CONFIG['sender_email']}/sendMail"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Create recipient list
        recipients = []
        for email in EMAIL_CONFIG['recipient_emails']:
            recipients.append({
                "emailAddress": {
                    "address": email
                }
            })
        
        email_data = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "Text",
                    "content": body
                },
                "toRecipients": recipients
            }
        }
        
        response = requests.post(url, headers=headers, json=email_data)
        
        if response.status_code == 202:
            recipient_list = ", ".join(EMAIL_CONFIG['recipient_emails'])
            return True, f"Email sent successfully to: {recipient_list}"
        else:
            return False, f"Email failed: {response.status_code} - {response.text}"
    
    except Exception as e:
        return False, f"Email error: {str(e)}"

def send_hourly_automation_report():
    """Main function to send hourly automation report"""
    try:
        print("\n📧 GENERATING HOURLY AUTOMATION REPORT EMAIL")
        print("=" * 50)
        
        # Generate report
        report_data = generate_hourly_report_summary()
        
        # Create email content
        email_body = create_hourly_email(report_data)
        
        # Create subject with time
        hour_display = report_data['hour_info']['hour_12']
        if report_data['overall_success']:
            subject = f"gemba-automation SUCCESS {report_data['report_date']} {hour_display}"
        else:
            subject = f"gemba-automation FAILED {report_data['report_date']} {hour_display}"
        
        # Send email
        success, message = send_email(subject, email_body)
        
        if success:
            print("✅ Hourly automation report email sent successfully")
            print(f"   Recipients: {', '.join(EMAIL_CONFIG['recipient_emails'])}")
            print(f"   Subject: {subject}")
            if report_data['overall_success']:
                print("   Status: SUCCESS - Simple notification sent")
            else:
                print("   Status: FAILURE - Detailed error report sent")
        else:
            print(f"❌ Failed to send email: {message}")
        
        return success
    
    except Exception as e:
        print(f"❌ Report generation failed: {e}")
        return False

# Test function for manual testing
def test_hourly_notification():
    """Test the hourly notification system"""
    print("🧪 Testing hourly notification system...")
    return send_hourly_automation_report()

if __name__ == "__main__":
    test_hourly_notification()
