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

def get_today():
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
        headers = [h.strip().replace(' ', '_').replace('%', 'Percent').replace('$', 'Dollar') for h in rows[0]]
        data = rows[1:]
        print(f"CSV loaded: {len(data)} records, {len(headers)} columns")
        return headers, data
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return None, None

def sanitize_headers(headers):
    clean_headers = []
    for header in headers:
        clean = header.replace(' ', '_').replace('%', 'Percent').replace('$', 'Dollar')
        clean = ''.join(c for c in clean if c.isalnum() or c == '_')
        if clean and clean[0].isdigit():
            clean = f"Col_{clean}"
        clean_headers.append(clean or "Unknown_Column")
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
    try:
        existing_columns = get_table_columns(conn, table_name)
        cursor = conn.cursor()
        for header in headers:
            if header not in existing_columns:
                try:
                    alter_query = f"ALTER TABLE [{table_name}] ADD [{header}] NVARCHAR(255)"
                    cursor.execute(alter_query)
                    print(f"Added column [{header}] to table {table_name}")
                except Exception as e:
                    print(f"Could not add column [{header}]: {e}")
        conn.commit()
        return True
    except Exception as e:
        print(f"Error adding columns: {e}")
        return False

def upsert_data(conn, table_name, headers, data, key_columns):
    try:
        if not add_missing_columns(conn, table_name, headers):
            print("Warning: Could not add all missing columns")
        existing_columns = get_table_columns(conn, table_name)
        valid_headers = [h for h in headers if h in existing_columns]
        if not valid_headers:
            print(f"No valid columns found for table {table_name}")
            return False
        cursor = conn.cursor()
        for row in data:
            while len(row) < len(headers):
                row.append('')
            row = row[:len(headers)]
            valid_row = []
            for i, header in enumerate(headers):
                if header in valid_headers:
                    valid_row.append(row[i] if i < len(row) else '')
            if key_columns:
                where_parts = []
                where_values = []
                for key_col in key_columns:
                    if key_col in valid_headers:
                        col_index = headers.index(key_col)
                        where_parts.append(f"ISNULL([{key_col}], '') = ISNULL(%s, '')")
                        where_values.append(row[col_index] if col_index < len(row) else '')
                if where_parts:
                    check_query = f"SELECT COUNT(*) FROM [{table_name}] WHERE {' AND '.join(where_parts)}"
                    cursor.execute(check_query, where_values)
                    exists = cursor.fetchone()[0] > 0
                    if exists:
                        set_parts = []
                        update_values = []
                        for i, header in enumerate(headers):
                            if header not in key_columns and header in valid_headers:
                                set_parts.append(f"[{header}] = %s")
                                update_values.append(row[i] if i < len(row) else '')
                        if set_parts:
                            update_query = f"UPDATE [{table_name}] SET {', '.join(set_parts)} WHERE {' AND '.join(where_parts)}"
                            cursor.execute(update_query, update_values + where_values)
                        continue
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

def upload_financial_report():
    try:
        print("Uploading Financial Report...")
        today = get_today()
        today_file = format_date(today)
        filepath = os.path.join(os.getcwd(), "Financial Reports", f"{today_file}.csv")
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
            key_columns = ['Location', 'Report_Date', 'Created_At']
            success = upsert_data(conn, 'custom_financials_2', headers, data, key_columns)
            return success
        finally:
            conn.close()
    except Exception as e:
        print(f"Financial upload error: {e}")
        return False

def upload_ro_reports():
    try:
        print("Uploading RO Marketing Reports...")
        today = get_today()
        today_short = format_date_short(today)
        filepath = os.path.join(os.getcwd(), "RO Reports", f"TekmetricGemba_RO_{today_short}.csv")
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
            key_columns = ['Marketing_Source', 'Location', 'Report_Date', 'Created_At']
            success = upsert_data(conn, 'ro_marketing_2', headers, data, key_columns)
            return success
        finally:
            conn.close()
    except Exception as e:
        print(f"RO upload error: {e}")
        return False

def upload_all_reports():
    try:
        print("Starting SQL upload...")
        financial_success = upload_financial_report()
        ro_success = upload_ro_reports()
        if financial_success and ro_success:
            print("All reports uploaded successfully")
            return True
        elif ro_success:
            print("RO uploaded successfully, Financial failed")
            return False
        elif financial_success:
            print("Financial uploaded successfully, RO failed")
            return False
        else:
            print("Both uploads failed")
            return False
    except Exception as e:
        print(f"Upload process error: {e}")
        return False

if __name__ == "__main__":
    upload_all_reports() 