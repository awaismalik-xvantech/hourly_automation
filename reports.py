import csv
import os
import datetime
import pytz

def get_arizona_time():
    return datetime.datetime.now(pytz.timezone('US/Arizona'))

def format_date(dt):
    return f"{dt.month}.{dt.day}.{dt.year}"

def format_date_short(dt):
    return f"{dt.month:02d}.{dt.day:02d}.{dt.year-2000:02d}"

def read_csv_safe(filepath):
    """Safely read CSV file with error handling"""
    try:
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            return None
            
        if os.path.getsize(filepath) == 0:
            print(f"File is empty: {filepath}")
            return None
        
        with open(filepath, 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            rows = list(reader)
        
        if len(rows) <= 1:
            print(f"No data rows in file: {filepath}")
            return None
            
        return rows
        
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None

def write_csv_safe(filepath, rows):
    """Safely write CSV file with error handling"""
    try:
        with open(filepath, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerows(rows)
        return True
    except Exception as e:
        print(f"Error writing {filepath}: {e}")
        return False

def process_financial_report(filename=None, created_at_hour=None):
    """Process and transpose financial report data"""
    try:
        # Get current date (function kept for compatibility)
        today = get_arizona_time()
        today_file = format_date(today)
        today_formatted = today.strftime("%m/%d/%Y")
        
        # Set default filename if not provided
        if not filename:
            filename = f"{today_file}_H{today.hour:02d}.csv"
        
        # Set default created_at_hour if not provided
        if not created_at_hour:
            created_at_hour = today.strftime("%I %p").lstrip('0')
        
        financial_dir = os.path.join(os.getcwd(), "Financial Reports")
        filepath = os.path.join(financial_dir, filename)
        
        print(f"Processing financial file: {filepath}")
        
        rows = read_csv_safe(filepath)
        if not rows:
            print("❌ Financial file not found, empty, or has no data")
            return False
        
        headers = rows[0]
        data_rows = rows[1:]
        
        # Create transposed data structure
        transposed_headers = ['Location']
        for row in data_rows:
            if row and len(row) > 0:
                transposed_headers.append(row[0])
        transposed_headers.extend(['Report_Date', 'Created_At'])
        
        transposed_data = [transposed_headers]
        
        # Transpose the data
        for col_index in range(2, len(headers)):
            if col_index < len(headers):
                new_row = [headers[col_index]]
                
                for row in data_rows:
                    if col_index < len(row):
                        new_row.append(row[col_index])
                    else:
                        new_row.append('')
                
                # Add Report_Date and Created_At
                new_row.extend([today_formatted, created_at_hour])
                transposed_data.append(new_row)
        
        if write_csv_safe(filepath, transposed_data):
            print(f"✅ Financial report transposed: {len(transposed_data)-1} records")
            print(f"   Report Date: {today_formatted}, Created At: {created_at_hour}")
            return True
        
        return False
        
    except Exception as e:
        print(f"❌ Financial processing error: {e}")
        return False

def create_empty_ro_record(location_name, today_formatted, created_at_hour):
    """Create empty RO record structure"""
    headers = ['Marketing Source', 'Total Sales', 'RO Count', 'New Sales', 'New RO Count',
              'Repeat Sales', 'Repeat RO Count', 'Average RO', 'GP $', 'GP %', 'Close Ratio',
              'Location', 'Report_Date', 'Created_At']
    empty_row = ['No Data', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', 
                location_name, today_formatted, created_at_hour]
    return [headers, empty_row]

def process_ro_marketing_report(location_name, filename, created_at_hour=None):
    """Process RO marketing report and add metadata"""
    try:
        today_formatted = get_arizona_time().strftime("%m/%d/%Y")
        
        # Set default created_at_hour if not provided
        if not created_at_hour:
            created_at_hour = get_arizona_time().strftime("%I %p").lstrip('0')
        
        ro_dir = os.path.join(os.getcwd(), "RO Reports")
        filepath = os.path.join(ro_dir, filename)
        
        print(f"Processing RO file: {filepath}")
        
        rows = read_csv_safe(filepath)
        if not rows:
            print(f"⚠️ RO file not found or empty, creating with zero values")
            rows = create_empty_ro_record(location_name, today_formatted, created_at_hour)
            if not write_csv_safe(filepath, rows):
                return False
        
        headers = rows[0]
        
        # Ensure required columns exist
        required_columns = ['Location', 'Report_Date', 'Created_At']
        for col in required_columns:
            if col not in headers:
                headers.append(col)
        
        # Get column indices
        location_idx = headers.index('Location')
        date_idx = headers.index('Report_Date')
        created_at_idx = headers.index('Created_At')
        
        # If only headers exist, add empty data row
        if len(rows) == 1:
            empty_row = [''] * len(headers)
            empty_row[location_idx] = location_name
            empty_row[date_idx] = today_formatted
            empty_row[created_at_idx] = created_at_hour
            rows.append(empty_row)
        else:
            # Update existing data rows
            for i in range(1, len(rows)):
                # Ensure row has enough columns
                while len(rows[i]) < len(headers):
                    rows[i].append('')
                
                # Set metadata
                rows[i][location_idx] = location_name
                rows[i][date_idx] = today_formatted
                rows[i][created_at_idx] = created_at_hour
        
        # Update headers
        rows[0] = headers
        
        if write_csv_safe(filepath, rows):
            print(f"✅ RO report processed: {location_name}")
            print(f"   Records: {len(rows)-1}, Created At: {created_at_hour}")
            return True
        
        return False
        
    except Exception as e:
        print(f"❌ RO processing error for {location_name}: {e}")
        return False

def combine_ro_reports(yesterday_short, created_at_hour=None):
    """Combine all RO reports into single file"""
    try:
        # Set default created_at_hour if not provided
        if not created_at_hour:
            created_at_hour = get_arizona_time().strftime("%I %p").lstrip('0')
            
        ro_dir = os.path.join(os.getcwd(), "RO Reports")
        
        locations = [
            "Mesa-Broadway",
            "Mesa-Guadalupe", 
            "Phoenix",
            "Tempe",
            "Sun-City-West",
            "Surprise"
        ]
        
        # Generate filenames with hour
        az_time = get_arizona_time()
        ro_files = [f"{loc}-{yesterday_short}_H{az_time.hour:02d}.csv" for loc in locations]
        
        combined_filename = f"TekmetricGemba_RO_{yesterday_short}_H{az_time.hour:02d}.csv"
        combined_filepath = os.path.join(ro_dir, combined_filename)
        
        combined_data = []
        headers_set = False
        processed_count = 0
        files_to_delete = []
        
        print("Combining RO reports...")
        
        for i, filename in enumerate(ro_files):
            filepath = os.path.join(ro_dir, filename)
            location_name = locations[i].replace('-', ' ')
            
            rows = read_csv_safe(filepath)
            if not rows:
                print(f"⚠️ Missing file {filename}, creating empty record")
                today_formatted = get_arizona_time().strftime("%m/%d/%Y")
                rows = create_empty_ro_record(location_name, today_formatted, created_at_hour)
                write_csv_safe(filepath, rows)
            
            # Add headers only once
            if not headers_set:
                combined_data.append(rows[0])
                headers_set = True
            
            # Add data rows
            combined_data.extend(rows[1:])
            processed_count += 1
            files_to_delete.append(filepath)
            print(f"  ✅ Added {len(rows)-1} records from {location_name}")
        
        if processed_count == 0:
            print("❌ No RO files to combine")
            return None
        
        if write_csv_safe(combined_filepath, combined_data):
            # Clean up individual files
            for filepath in files_to_delete:
                try:
                    os.remove(filepath)
                except Exception as e:
                    print(f"⚠️ Could not delete {filepath}: {e}")
            
            print(f"✅ Combined {processed_count}/6 RO reports: {combined_filename}")
            print(f"   Total records: {len(combined_data)-1}, Created At: {created_at_hour}")
            return combined_filename
        
        return None
        
    except Exception as e:
        print(f"❌ Combine error: {e}")
        return None

def verify_data_accuracy(financial_filename, ro_filename, created_at_hour=None):
    """Verify data accuracy and completeness"""
    try:
        # Set default created_at_hour if not provided
        if not created_at_hour:
            created_at_hour = get_arizona_time().strftime("%I %p").lstrip('0')
            
        financial_dir = os.path.join(os.getcwd(), "Financial Reports")
        ro_dir = os.path.join(os.getcwd(), "RO Reports")
        
        # Generate file paths with hour
        az_time = get_arizona_time()
        financial_path = os.path.join(financial_dir, f"{financial_filename}_H{az_time.hour:02d}.csv")
        ro_path = os.path.join(ro_dir, f"TekmetricGemba_RO_{ro_filename}_H{az_time.hour:02d}.csv")
        
        print("📊 VERIFICATION REPORT")
        print("=" * 40)
        
        # Initialize counters
        financial_car_count = 0
        ro_total_count = 0
        ro_locations = set()
        created_at_records = 0
        
        # Verify financial data
        print("Checking Financial Report...")
        financial_rows = read_csv_safe(financial_path)
        if financial_rows:
            headers = financial_rows[0]
            created_at_idx = headers.index('Created_At') if 'Created_At' in headers else -1
            
            for row in financial_rows[1:]:
                if len(row) > 0 and row[0] == 'Car Count':
                    for i in range(1, len(row) - 2):  # Exclude Report_Date and Created_At
                        try:
                            if row[i].strip() and row[i].strip() != '0':
                                financial_car_count += int(float(row[i]))
                        except:
                            continue
                    break
                
                # Check Created_At column
                if created_at_idx >= 0 and len(row) > created_at_idx:
                    if row[created_at_idx] == created_at_hour:
                        created_at_records += 1
            
            print(f"  ✅ Financial file found and processed")
        else:
            print(f"  ❌ Financial file not found: {financial_path}")
        
        # Verify RO data
        print("Checking RO Report...")
        ro_rows = read_csv_safe(ro_path)
        if ro_rows:
            headers = ro_rows[0]
            ro_count_idx = None
            location_idx = None
            
            for i, header in enumerate(headers):
                if 'RO Count' in header:
                    ro_count_idx = i
                if 'Location' in header:
                    location_idx = i
            
            if ro_count_idx is not None and location_idx is not None:
                for row in ro_rows[1:]:
                    if len(row) > max(ro_count_idx, location_idx):
                        try:
                            if row[ro_count_idx].strip():
                                ro_total_count += int(float(row[ro_count_idx]))
                            if row[location_idx].strip():
                                ro_locations.add(row[location_idx])
                        except:
                            continue
            
            print(f"  ✅ RO file found and processed")
        else:
            print(f"  ❌ RO file not found: {ro_path}")
        
        # Print verification results
        print("\n📈 VERIFICATION RESULTS")
        print("-" * 40)
        print(f"Financial Car Count: {financial_car_count}")
        print(f"RO Total Count: {ro_total_count}")
        print(f"RO Locations Found: {len(ro_locations)}/6")
        print(f"Created_At Hour: {created_at_hour}")
        print(f"Records with correct Created_At: {created_at_records}")
        
        # Location details
        if ro_locations:
            print(f"Locations: {', '.join(sorted(ro_locations))}")
        
        # Determine success
        success = True
        warnings = []
        
        if len(ro_locations) < 6:
            warnings.append(f"Missing {6 - len(ro_locations)} locations")
            success = False
        
        if financial_car_count == 0:
            warnings.append("Financial car count is 0")
        
        if ro_total_count == 0:
            warnings.append("RO count is 0")
        
        if warnings:
            print("\n⚠️  WARNINGS:")
            for warning in warnings:
                print(f"  - {warning}")
        else:
            print("\n✅ All verifications passed!")
        
        print("=" * 40)
        return success
        
    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False
