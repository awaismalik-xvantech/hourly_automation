import csv
import os
import datetime
import pytz

SQL_CONFIG = {
    'server': os.getenv('SQL_SERVER', 'gembadb.database.windows.net'),
    'database': os.getenv('SQL_DATABASE', 'gemba'),
    'username': os.getenv('SQL_USERNAME', 'gembauser'),
    'password': os.getenv('SQL_PASSWORD', 'Karachi%007'),
    'port': int(os.getenv('SQL_PORT', '1433'))
}

def get_arizona_time():
    return datetime.datetime.now(pytz.timezone('US/Arizona'))

def get_yesterday():
    return get_arizona_time()

def format_date(dt):
    return f"{dt.month}.{dt.day}.{dt.year}"

def format_date_short(dt):
    return f"{dt.month:02d}.{dt.day:02d}.{dt.year-2000:02d}"

def create_connection():
    try:
        import pymssql
        
        conn = pymssql.connect(
            server=SQL_CONFIG['server'],
            user=SQL_CONFIG['username'],
            password=SQL_CONFIG['password'],
            database=SQL_CONFIG['database'],
            port=SQL_CONFIG['port'],
            timeout=30
        )
        
        print(f"Connected to SQL Server: {SQL_CONFIG['server']}")
        return conn
        
    except ImportError:
        print("pymssql not installed")
        return None
    except Exception as e:
        print(f"SQL connection failed: {e}")
        return None

def read_csv_data(filepath):
    try:
        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            print(f"File not found or empty: {filepath}")
            return None, None
        
        with open(filepath, 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            rows = list(reader)
        
        if len(rows) < 2:
            print("CSV has no data rows")
            return None, None
        
        headers = [h.strip().replace(' ', '_').replace('%', 'Percent').replace('$', 'Dollar') 
                  for h in rows[0]]
        data = rows[1:]
        
        print(f"CSV loaded: {len(data)} records, {len(headers)} columns")
        return headers, data
        
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return None, None

def sanitize_headers(headers):
    """Fixed version that handles duplicate column names properly"""
    clean_headers = []
    seen_headers = {}
    
    for i, header in enumerate(headers):
        # Basic cleaning
        clean = header.replace(' ', '_').replace('%', 'Percent').replace('$', 'Dollar')
        clean = ''.join(c for c in clean if c.isalnum() or c == '_')
        
        # Handle empty or invalid headers
        if not clean or clean[0].isdigit():
            clean = f"Column_{i+1}"
        
        # Handle duplicates by adding a number suffix
        if clean in seen_headers:
            seen_headers[clean] += 1
            clean = f"{clean}_{seen_headers[clean]}"
        else:
            seen_headers[clean] = 0
        
        clean_headers.append(clean)
    
    print(f"Sanitized headers: {len(clean_headers)} unique columns")
    
    # Debug: show any duplicates that were fixed
    original_count = len(headers)
    unique_count = len(set(clean_headers))
    if original_count != unique_count:
        print(f"⚠️  Fixed {original_count - unique_count} duplicate column names")
    
    return clean_headers

def table_exists(conn, table_name):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = %s", (table_name,))
        return cursor.fetchone()[0] > 0
    except:
        return False

def create_table(conn, table_name, headers):
    try:
        if table_exists(conn, table_name):
            print(f"Table '{table_name}' exists")
            return True
        
        cursor = conn.cursor()
        columns = [f"[{h}] NVARCHAR(255)" for h in headers]
        query = f"CREATE TABLE [{table_name}] ({', '.join(columns)})"
        
        cursor.execute(query)
        conn.commit()
        print(f"Table '{table_name}' created")
        return True
        
    except Exception as e:
        print(f"Table creation error: {e}")
        return False

def get_table_columns(conn, table_name):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = %s", (table_name,))
        columns = [row[0] for row in cursor.fetchall()]
        return columns
    except:
        return []

def add_missing_columns(conn, table_name, headers):
    """Fixed version that handles column name conflicts properly"""
    try:
        existing_columns = get_table_columns(conn, table_name)
        cursor = conn.cursor()
        
        added_count = 0
        for header in headers:
            if header not in existing_columns:
                try:
                    alter_query = f"ALTER TABLE [{table_name}] ADD [{header}] NVARCHAR(255)"
                    cursor.execute(alter_query)
                    added_count += 1
                    print(f"Added column [{header}] to table {table_name}")
                except Exception as e:
                    # Skip columns that cause conflicts
                    if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                        print(f"Skipped duplicate column [{header}]")
                    else:
                        print(f"Could not add column [{header}]: {e}")
        
        conn.commit()
        
        if added_count > 0:
            print(f"Successfully added {added_count} new columns to {table_name}")
        
        return True
    except Exception as e:
        print(f"Error adding columns: {e}")
        return False

def upsert_data_with_created_at(conn, table_name, headers, data, key_columns):
    """Fixed version that handles column conflicts properly"""
    try:
        if not add_missing_columns(conn, table_name, headers):
            print("Warning: Could not add all missing columns")
        
        existing_columns = get_table_columns(conn, table_name)
        valid_headers = [h for h in headers if h in existing_columns]
        
        if not valid_headers:
            print(f"No valid columns found for table {table_name}")
            return False
        
        # Remove duplicates from valid_headers while preserving order
        seen = set()
        unique_valid_headers = []
        for h in valid_headers:
            if h not in seen:
                seen.add(h)
                unique_valid_headers.append(h)
        
        valid_headers = unique_valid_headers
        print(f"Using {len(valid_headers)} valid unique columns for {table_name}")
        
        cursor = conn.cursor()
        
        for row in data:
            # Ensure row has enough values
            while len(row) < len(headers):
                row.append('')
            row = row[:len(headers)]
            
            # Create valid row data matching valid headers
            valid_row = []
            for header in valid_headers:
                if header in headers:
                    header_index = headers.index(header)
                    valid_row.append(row[header_index] if header_index < len(row) else '')
                else:
                    valid_row.append('')
            
            # Check if record exists based on key columns
            if key_columns:
                where_parts = []
                where_values = []
                for key_col in key_columns:
                    if key_col in valid_headers:
                        col_index = headers.index(key_col) if key_col in headers else -1
                        if col_index >= 0:
                            where_parts.append(f"ISNULL([{key_col}], '') = ISNULL(%s, '')")
                            where_values.append(row[col_index] if col_index < len(row) else '')
                
                if where_parts:
                    check_query = f"SELECT COUNT(*) FROM [{table_name}] WHERE {' AND '.join(where_parts)}"
                    cursor.execute(check_query, where_values)
                    exists = cursor.fetchone()[0] > 0
                    
                    if exists:
                        # Update existing record
                        set_parts = []
                        update_values = []
                        for header in valid_headers:
                            if header not in key_columns:
                                header_index = headers.index(header) if header in headers else -1
                                if header_index >= 0:
                                    set_parts.append(f"[{header}] = %s")
                                    update_values.append(row[header_index] if header_index < len(row) else '')
                        
                        if set_parts:
                            update_query = f"UPDATE [{table_name}] SET {', '.join(set_parts)} WHERE {' AND '.join(where_parts)}"
                            cursor.execute(update_query, update_values + where_values)
                            print(f"Updated existing record for: {', '.join([str(v) for v in where_values])}")
                        continue
            
            # Insert new record
            placeholders = ', '.join(['%s'] * len(valid_headers))
            insert_query = f"INSERT INTO [{table_name}] ([{'], ['.join(valid_headers)}]) VALUES ({placeholders})"
            cursor.execute(insert_query, valid_row)
        
        conn.commit()
        print(f"Data uploaded to {table_name}: {len(data)} records")
        return True
        
    except Exception as e:
        print(f"Upload error for {table_name}: {e}")
        try:
            conn.rollback()
        except:
            pass
        return False

def upload_financial_report(created_at_hour=None):
    try:
        print("Uploading Financial Report to custom_financials_2...")
        
        today = get_yesterday()
        today_file = format_date(today)
        
        az_time = get_arizona_time()
        if not created_at_hour:
            created_at_hour = az_time.strftime("%I %p").lstrip('0')
            
        filepath = os.path.join(os.getcwd(), "Financial Reports", f"{today_file}_H{az_time.hour:02d}.csv")
        
        headers, data = read_csv_data(filepath)
        if not headers:
            return False
        
        headers = sanitize_headers(headers)
        
        conn = create_connection()
        if not conn:
            return False
        
        try:
            if not create_table(conn, 'custom_financials_2', headers):
                return False
            
            key_columns = ['Location', 'Report_Date']
            success = upsert_data_with_created_at(conn, 'custom_financials_2', headers, data, key_columns)
            
            if success:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT Created_At FROM [custom_financials_2] WHERE Report_Date = %s", 
                             (today.strftime("%m/%d/%Y"),))
                created_at_values = [row[0] for row in cursor.fetchall()]
                print(f"Financial data uploaded with Created_At: {created_at_values}")
            
            return success
        finally:
            conn.close()
        
    except Exception as e:
        print(f"Financial upload error: {e}")
        return False

def upload_ro_reports(created_at_hour=None):
    try:
        print("Uploading RO Marketing Reports to ro_marketing_2...")
        
        today = get_yesterday()
        today_short = format_date_short(today)
        
        az_time = get_arizona_time()
        if not created_at_hour:
            created_at_hour = az_time.strftime("%I %p").lstrip('0')
            
        filepath = os.path.join(os.getcwd(), "RO Reports", f"TekmetricGemba_RO_{today_short}_H{az_time.hour:02d}.csv")
        
        headers, data = read_csv_data(filepath)
        if not headers:
            return False
        
        headers = sanitize_headers(headers)
        
        conn = create_connection()
        if not conn:
            return False
        
        try:
            if not create_table(conn, 'ro_marketing_2', headers):
                return False
            
            key_columns = ['Marketing_Source', 'Location', 'Report_Date']
            success = upsert_data_with_created_at(conn, 'ro_marketing_2', headers, data, key_columns)
            
            if success:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT Location, COUNT(*) as RecordCount, MAX(Created_At) as LatestCreatedAt
                    FROM [ro_marketing_2] 
                    WHERE Report_Date = %s 
                    GROUP BY Location
                    ORDER BY Location
                """, (today.strftime("%m/%d/%Y"),))
                
                location_info = cursor.fetchall()
                print(f"RO data uploaded for {len(location_info)} locations:")
                for location, count, latest_created_at in location_info:
                    print(f"  {location}: {count} records, Latest Created_At: {latest_created_at}")
            
            return success
        finally:
            conn.close()
        
    except Exception as e:
        print(f"RO upload error: {e}")
        return False

def upload_all_reports(created_at_hour=None):
    try:
        print("Starting SQL upload to new tables...")
        
        if not created_at_hour:
            az_time = get_arizona_time()
            created_at_hour = az_time.strftime("%I %p").lstrip('0')
        
        print(f"Uploading data with Created_At: {created_at_hour}")
        
        financial_success = upload_financial_report(created_at_hour)
        ro_success = upload_ro_reports(created_at_hour)
        
        if financial_success and ro_success:
            print("All reports uploaded successfully to new tables")
            
            # Summary report
            try:
                conn = create_connection()
                if conn:
                    cursor = conn.cursor()
                    today = get_yesterday()
                    today_formatted = today.strftime("%m/%d/%Y")
                    
                    cursor.execute("SELECT COUNT(*) FROM [custom_financials_2] WHERE Report_Date = %s AND Created_At = %s", 
                                 (today_formatted, created_at_hour))
                    financial_count = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(*) FROM [ro_marketing_2] WHERE Report_Date = %s AND Created_At = %s", 
                                 (today_formatted, created_at_hour))
                    ro_count = cursor.fetchone()[0]
                    
                    print(f"\nUpload Summary for {today_formatted} at {created_at_hour}:")
                    print(f"  custom_financials_2: {financial_count} records")
                    print(f"  ro_marketing_2: {ro_count} records")
                    
                    conn.close()
            except Exception as e:
                print(f"Summary report error: {e}")
            
            return True
        elif ro_success:
            print("RO uploaded successfully to ro_marketing_2, Financial failed")
            return False
        elif financial_success:
            print("Financial uploaded successfully to custom_financials_2, RO failed")
            return False
        else:
            print("Both uploads failed")
            return False
            
    except Exception as e:
        print(f"Upload process error: {e}")
        return False

if __name__ == "__main__":
    upload_all_reports()
