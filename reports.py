import csv
import os
import datetime
import pytz

def get_arizona_time():
    return datetime.datetime.now(pytz.timezone('US/Arizona'))

def get_today():
    return get_arizona_time()

def format_date(dt):
    return f"{dt.month}.{dt.day}.{dt.year}"

def format_date_short(dt):
    return f"{dt.month:02d}.{dt.day:02d}.{dt.year-2000:02d}"

def read_csv_safe(filepath):
    try:
        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            return None
        with open(filepath, 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            rows = list(reader)
        return rows if len(rows) > 1 else None
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None

def write_csv_safe(filepath, rows):
    try:
        with open(filepath, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerows(rows)
        return True
    except Exception as e:
        print(f"Error writing {filepath}: {e}")
        return False

def process_financial_report(created_at):
    try:
        today = get_today()
        today_file = format_date(today)
        today_formatted = today.strftime("%m/%d/%Y")
        financial_dir = os.path.join(os.getcwd(), "Financial Reports")
        filepath = os.path.join(financial_dir, f"{today_file}.csv")
        print(f"Processing financial file: {filepath}")
        rows = read_csv_safe(filepath)
        if not rows:
            print("Financial file not found or empty")
            return False
        headers = rows[0]
        data_rows = rows[1:]
        transposed_headers = ['Location']
        for row in data_rows:
            if row and len(row) > 0:
                transposed_headers.append(row[0])
        transposed_headers.append('Report_Date')
        transposed_headers.append('Created At')
        transposed_data = [transposed_headers]
        for col_index in range(2, len(headers)):
            if col_index < len(headers):
                new_row = [headers[col_index]]
                for row in data_rows:
                    if col_index < len(row):
                        new_row.append(row[col_index])
                    else:
                        new_row.append('')
                new_row.append(today_formatted)
                new_row.append(created_at)
                transposed_data.append(new_row)
        if write_csv_safe(filepath, transposed_data):
            print(f"Financial report transposed: {len(transposed_data)-1} records")
            return True
        return False
    except Exception as e:
        print(f"Financial processing error: {e}")
        return False

def create_empty_ro_record(location_name, today_formatted, created_at):
    headers = ['Marketing Source', 'Total Sales', 'RO Count', 'New Sales', 'New RO Count',
              'Repeat Sales', 'Repeat RO Count', 'Average RO', 'GP $', 'GP %', 'Close Ratio',
              'Location', 'Report_Date', 'Created At']
    empty_row = ['No Data', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', location_name, today_formatted, created_at]
    return [headers, empty_row]

def process_ro_marketing_report(location_name, filename, created_at):
    try:
        today_formatted = get_today().strftime("%m/%d/%Y")
        ro_dir = os.path.join(os.getcwd(), "RO Reports")
        filepath = os.path.join(ro_dir, filename)
        print(f"Processing RO file: {filepath}")
        rows = read_csv_safe(filepath)
        if not rows:
            print(f"RO file not found or empty, creating with 0 values: {filename}")
            rows = create_empty_ro_record(location_name, today_formatted, created_at)
            if not write_csv_safe(filepath, rows):
                return False
        headers = rows[0]
        if 'Location' not in headers:
            headers.append('Location')
        if 'Report_Date' not in headers:
            headers.append('Report_Date')
        if 'Created At' not in headers:
            headers.append('Created At')
        location_idx = headers.index('Location') if 'Location' in headers else len(headers) - 3
        date_idx = headers.index('Report_Date') if 'Report_Date' in headers else len(headers) - 2
        created_at_idx = headers.index('Created At') if 'Created At' in headers else len(headers) - 1
        if len(rows) == 1:
            empty_row = [''] * (len(headers) - 3) + [location_name, today_formatted, created_at]
            rows.append(empty_row)
        else:
            for i in range(1, len(rows)):
                while len(rows[i]) < len(headers):
                    rows[i].append('')
                rows[i][location_idx] = location_name
                rows[i][date_idx] = today_formatted
                rows[i][created_at_idx] = created_at
        rows[0] = headers
        if write_csv_safe(filepath, rows):
            print(f"RO report processed: {location_name} - {len(rows)-1} records")
            return True
        return False
    except Exception as e:
        print(f"RO processing error for {location_name}: {e}")
        return False

def combine_ro_reports(today_short):
    try:
        ro_dir = os.path.join(os.getcwd(), "RO Reports")
        locations = [
            "Mesa-Broadway",
            "Mesa-Guadalupe", 
            "Phoenix",
            "Tempe",
            "Sun-City-West",
            "Surprise"
        ]
        ro_files = [f"{loc}-{today_short}.csv" for loc in locations]
        combined_filename = f"TekmetricGemba_RO_{today_short}.csv"
        combined_filepath = os.path.join(ro_dir, combined_filename)
        combined_data = []
        headers_set = False
        processed_count = 0
        files_to_delete = []
        for i, filename in enumerate(ro_files):
            filepath = os.path.join(ro_dir, filename)
            location_name = locations[i].replace('-', ' ')
            rows = read_csv_safe(filepath)
            if not rows:
                print(f"Missing file {filename}, creating empty record")
                today_formatted = get_today().strftime("%m/%d/%Y")
                created_at = get_arizona_time().strftime("%I:%M %p")
                rows = create_empty_ro_record(location_name, today_formatted, created_at)
                write_csv_safe(filepath, rows)
            if not headers_set:
                combined_data.append(rows[0])
                headers_set = True
            combined_data.extend(rows[1:])
            processed_count += 1
            files_to_delete.append(filepath)
            print(f"Added {len(rows)-1} records from {location_name}")
        if processed_count == 0:
            print("No RO files to combine")
            return None
        if write_csv_safe(combined_filepath, combined_data):
            for filepath in files_to_delete:
                try:
                    os.remove(filepath)
                except:
                    pass
            print(f"Combined {processed_count}/6 RO reports: {combined_filename}")
            return combined_filename
        return None
    except Exception as e:
        print(f"Combine error: {e}")
        return None

def verify_data_accuracy(financial_filename, ro_filename):
    try:
        financial_dir = os.path.join(os.getcwd(), "Financial Reports")
        ro_dir = os.path.join(os.getcwd(), "RO Reports")
        financial_path = os.path.join(financial_dir, f"{financial_filename}.csv")
        ro_path = os.path.join(ro_dir, f"TekmetricGemba_RO_{ro_filename}.csv")
        financial_car_count = 0
        ro_total_count = 0
        ro_locations = set()
        financial_rows = read_csv_safe(financial_path)
        if financial_rows:
            for row in financial_rows[1:]:
                if len(row) > 0 and row[0] == 'Car Count':
                    for i in range(1, len(row) - 2):
                        try:
                            if row[i].strip() and row[i].strip() != '0':
                                financial_car_count += int(float(row[i]))
                        except:
                            continue
                    break
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
        print(f"Verification - Financial Car Count: {financial_car_count}")
        print(f"Verification - RO Total Count: {ro_total_count}")
        print(f"Verification - RO Locations: {len(ro_locations)}/6")
        success = True
        if len(ro_locations) < 6:
            print(f"Warning: Missing {6 - len(ro_locations)} locations")
            success = False
        else:
            print("All 6 locations found in RO data")
        if financial_car_count == 0:
            print("Note: Financial car count is 0 (could be valid for low activity days)")
        if ro_total_count == 0:
            print("Note: RO count is 0 (could be valid if no ROs for this date)")
        return success
    except Exception as e:
        print(f"Verification error: {e}")
        return False 