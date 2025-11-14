"""
Script để chạy file SQL có chứa DELIMITER và tạo stored procedures/functions.
"""
import mysql.connector
import sys

# Cấu hình database - lấy từ app.py
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'giabao123',
    'database': 'ShoppeDB'
}

def execute_sql_file(file_path):
    """Đọc và thực thi file SQL có chứa DELIMITER."""
    try:
        # Kết nối database
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # Đọc file SQL
        with open(file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Xử lý DELIMITER: tách file thành các statement
        # DELIMITER $$ không được Python mysql-connector hỗ trợ trực tiếp
        # Nên ta sẽ xử lý thủ công: thay $$ bằng ; và bỏ qua dòng DELIMITER
        
        # Loại bỏ các dòng DELIMITER
        lines = sql_content.split('\n')
        processed_lines = []
        skip_delimiter = False
        
        for line in lines:
            stripped = line.strip().upper()
            # Bỏ qua dòng DELIMITER
            if stripped.startswith('DELIMITER'):
                skip_delimiter = True
                continue
            
            # Thay thế $$ thành ; khi gặp END$$
            if '$$' in line:
                line = line.replace('$$', ';')
                skip_delimiter = False
            
            processed_lines.append(line)
        
        # Nối lại thành SQL
        sql_processed = '\n'.join(processed_lines)
        
        # Tách thành các statement (dựa trên ;)
        statements = []
        current_statement = []
        
        for line in sql_processed.split('\n'):
            # Bỏ qua comment và dòng trống
            stripped = line.strip()
            if not stripped or stripped.startswith('--') or stripped.startswith('/*'):
                continue
            
            current_statement.append(line)
            
            # Nếu dòng kết thúc bằng ; thì kết thúc statement
            if stripped.endswith(';'):
                statement = '\n'.join(current_statement)
                if statement.strip():
                    statements.append(statement)
                current_statement = []
        
        # Thêm statement cuối cùng nếu còn
        if current_statement:
            statement = '\n'.join(current_statement)
            if statement.strip():
                statements.append(statement)
        
        # Thực thi từng statement
        success_count = 0
        error_count = 0
        
        for i, statement in enumerate(statements, 1):
            try:
                # Thực thi với multi_statement=True
                for result in cursor.execute(statement, multi=True):
                    pass
                success_count += 1
                print(f"✓ Đã thực thi statement {i}/{len(statements)}")
            except mysql.connector.Error as err:
                error_count += 1
                print(f"✗ Lỗi ở statement {i}: {err.msg}")
                # Vẫn tiếp tục với các statement khác
        
        # Commit changes
        conn.commit()
        
        print(f"\n{'='*50}")
        print(f"Hoàn thành: {success_count} statement thành công, {error_count} statement lỗi")
        
        cursor.close()
        conn.close()
        
        return error_count == 0
        
    except mysql.connector.Error as err:
        print(f"Lỗi kết nối database: {err}")
        return False
    except FileNotFoundError:
        print(f"Không tìm thấy file: {file_path}")
        return False
    except Exception as e:
        print(f"Lỗi: {e}")
        return False

if __name__ == '__main__':
    sql_file = 'database objects.sql'
    print(f"Đang chạy file SQL: {sql_file}")
    print(f"{'='*50}\n")
    
    if execute_sql_file(sql_file):
        print("\n✓ Tất cả stored procedures và functions đã được tạo thành công!")
    else:
        print("\n✗ Có lỗi xảy ra. Vui lòng kiểm tra lại.")
        sys.exit(1)

