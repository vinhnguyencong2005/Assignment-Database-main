"""
Script để chạy file SQL và tạo database hoàn chỉnh.
Hỗ trợ cả file SQL thường và file có DELIMITER (stored procedures/functions).
"""
import mysql.connector
import sys
import re

# Cấu hình database
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '22102005bobo',
    'charset': 'utf8mb4',
    'use_unicode': True
}

def connect_db(database=None):
    """Kết nối database với hoặc không có database name"""
    config = db_config.copy()
    if database:
        config['database'] = database
    return mysql.connector.connect(**config)

def execute_regular_sql(file_path, database=None):
    """Thực thi file SQL thông thường (không có DELIMITER)"""
    print(f"\n{'='*60}")
    print(f"Đang chạy file: {file_path}")
    print(f"{'='*60}")
    
    try:
        conn = connect_db(database)
        cursor = conn.cursor()
        
        # Đọc file SQL
        with open(file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Thực thi file SQL với multi=True
        statements = 0
        for result in cursor.execute(sql_content, multi=True):
            statements += 1
            if result.with_rows:
                result.fetchall()
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✓ Đã thực thi thành công {statements} statement(s)")
        return True
        
    except mysql.connector.Error as err:
        print(f"✗ Lỗi MySQL: {err}")
        return False
    except Exception as e:
        print(f"✗ Lỗi: {e}")
        return False

def execute_delimiter_sql(file_path, database):
    """Thực thi file SQL có chứa DELIMITER (stored procedures/functions/triggers)"""
    print(f"\n{'='*60}")
    print(f"Đang chạy file: {file_path}")
    print(f"{'='*60}")
    
    try:
        conn = connect_db(database)
        cursor = conn.cursor()
        
        # Đọc file SQL
        with open(file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Tách các object SQL dựa trên DELIMITER
        # Pattern: tìm các block giữa DELIMITER $$ và $$
        objects = []
        
        # Loại bỏ các dòng DELIMITER
        sql_content = re.sub(r'DELIMITER\s+\$\$', '', sql_content, flags=re.IGNORECASE)
        sql_content = re.sub(r'DELIMITER\s+;', '', sql_content, flags=re.IGNORECASE)
        
        # Thay thế $$ thành ;
        sql_content = sql_content.replace('$$', ';')
        
        # Tách các statement dựa trên các từ khóa
        # Tìm các DROP và CREATE statements
        pattern = r'(DROP\s+(?:TRIGGER|PROCEDURE|FUNCTION)\s+.*?;|CREATE\s+(?:TRIGGER|PROCEDURE|FUNCTION)\s+.*?END\s*;)'
        matches = re.finditer(pattern, sql_content, re.IGNORECASE | re.DOTALL)
        
        for match in matches:
            statement = match.group(1).strip()
            if statement:
                objects.append(statement)
        
        # Nếu không tìm thấy bằng regex, thử parse thủ công
        if not objects:
            print("⚠ Không tìm thấy objects bằng regex, thử parse thủ công...")
            lines = sql_content.split('\n')
            current_statement = []
            in_object = False
            
            for line in lines:
                stripped = line.strip()
                
                # Bỏ qua comment và dòng trống
                if not stripped or stripped.startswith('--'):
                    continue
                
                # Kiểm tra bắt đầu object
                if re.match(r'(DROP|CREATE)\s+(TRIGGER|PROCEDURE|FUNCTION)', stripped, re.IGNORECASE):
                    in_object = True
                    current_statement = [line]
                    continue
                
                if in_object:
                    current_statement.append(line)
                    # Kiểm tra kết thúc object
                    if re.match(r'END\s*;', stripped, re.IGNORECASE) or stripped.endswith(';'):
                        statement = '\n'.join(current_statement)
                        if 'CREATE' in statement.upper() or 'DROP' in statement.upper():
                            objects.append(statement)
                        current_statement = []
                        in_object = False
        
        # Thực thi từng object
        success_count = 0
        error_count = 0
        
        for i, obj in enumerate(objects, 1):
            try:
                # Loại bỏ khoảng trắng thừa
                obj = obj.strip()
                if not obj:
                    continue
                
                # Thực thi statement
                cursor.execute(obj)
                
                # Lấy tên object để hiển thị
                match = re.search(r'(DROP|CREATE)\s+(TRIGGER|PROCEDURE|FUNCTION)\s+(?:IF\s+EXISTS\s+)?(\w+)', 
                                obj, re.IGNORECASE)
                if match:
                    action = match.group(1).upper()
                    obj_type = match.group(2).upper()
                    obj_name = match.group(3)
                    print(f"  ✓ [{i}/{len(objects)}] {action} {obj_type}: {obj_name}")
                else:
                    print(f"  ✓ [{i}/{len(objects)}] Statement executed")
                
                success_count += 1
                
            except mysql.connector.Error as err:
                error_count += 1
                print(f"  ✗ [{i}/{len(objects)}] Lỗi: {err.msg}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"\n{'='*60}")
        print(f"Hoàn thành: {success_count} thành công, {error_count} lỗi")
        print(f"{'='*60}")
        
        return error_count == 0
        
    except mysql.connector.Error as err:
        print(f"✗ Lỗi MySQL: {err}")
        return False
    except Exception as e:
        print(f"✗ Lỗi: {e}")
        import traceback
        traceback.print_exc()
        return False

def setup_database():
    """Setup toàn bộ database từ đầu"""
    print("\n" + "="*60)
    print("🚀 BẮT ĐẦU SETUP DATABASE SHOPPEDB")
    print("="*60)
    
    all_success = True
    
    # Bước 1: Chạy btldatabase.sql (tạo database, tables, insert data)
    print("\n📦 BƯỚC 1: Tạo database và tables...")
    if not execute_regular_sql('btldatabase.sql'):
        print("❌ Lỗi khi tạo database và tables!")
        all_success = False
    else:
        print("✅ Database và tables đã được tạo thành công!")
    
    # Bước 2: Chạy database objects.sql (tạo triggers, procedures, functions)
    print("\n⚙️  BƯỚC 2: Tạo triggers, stored procedures và functions...")
    if not execute_delimiter_sql('database objects.sql', 'ShoppeDB'):
        print("❌ Lỗi khi tạo database objects!")
        all_success = False
    else:
        print("✅ Triggers, stored procedures và functions đã được tạo thành công!")
    
    print("\n" + "="*60)
    if all_success:
        print("🎉 HOÀN TẤT! Database ShoppeDB đã sẵn sàng!")
        print("="*60)
        print("\n📝 Bạn có thể chạy Flask app bằng lệnh:")
        print("   python app.py")
        print("\n🌐 Sau đó truy cập: http://127.0.0.1:5050/dashboard")
    else:
        print("⚠️  CÓ LỖI XẢY RA! Vui lòng kiểm tra lại.")
        print("="*60)
    
    return all_success

if __name__ == '__main__':
    # Kiểm tra tham số command line
    if len(sys.argv) > 1:
        # Chạy file cụ thể
        file_path = sys.argv[1]
        database = sys.argv[2] if len(sys.argv) > 2 else None
        
        if 'DELIMITER' in open(file_path, 'r').read():
            success = execute_delimiter_sql(file_path, database)
        else:
            success = execute_regular_sql(file_path, database)
        
        sys.exit(0 if success else 1)
    else:
        # Chạy setup toàn bộ
        success = setup_database()
        sys.exit(0 if success else 1)
