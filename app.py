from flask import Flask, render_template, request, flash, redirect, session
import mysql.connector
from mysql.connector import errorcode
from decimal import Decimal

from mock_data import get_mock_buyer_history, get_mock_top_sellers

app = Flask(__name__, template_folder='template')
# Thêm một "khóa bí mật" để Flask có thể gửi thông báo (flash messages)
app.config['SECRET_KEY'] = 'your_secret_key_12345' 
app.config['SESSION_PERMANENT'] = False

# Bật/tắt sử dụng CSDL. Để phát triển UI/UX trước, đặt False để dùng dữ liệu giả
USE_DB = False

# Cấu hình kết nối CSDL MySQL
# (Team của bạn sẽ điền thông tin thật vào đây sau)
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'MatKhauCuaBan', # <-- Sẽ thay đổi sau
    'database': 'ShopeeDB'
}

# Hàm giúp kết nối CSDL, có xử lý lỗi
def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as err:
        print(f"Lỗi kết nối CSDL: {err}")
        # Không thể dùng flash() ở đây vì không có request context
        # Lỗi sẽ được xử lý ở nơi gọi hàm này
        return None

# =================================================
# TRANG CỦA LEADER (Dashboard - Phần 3.3)
# =================================================
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    # Lấy dữ liệu đã lưu trong session (nếu có) để tránh bị reset khi bấm form khác
    seller_results = session.get('seller_results', [])
    buyer_history = session.get('buyer_history')
    buyer_id_lookup = session.get('buyer_id')

    def serialize_rows(rows):
        """Chuyển đổi các kiểu dữ liệu không tuần tự hóa được (ví dụ Decimal) sang kiểu chuẩn."""
        serialized = []
        for row in rows:
            serialized_row = {}
            for key, value in row.items():
                if isinstance(value, Decimal):
                    serialized_row[key] = float(value)
                else:
                    serialized_row[key] = value
            serialized.append(serialized_row)
        return serialized

    # Khi người dùng nhấn nút (gửi form)
    if request.method == 'POST':
        conn = None if not USE_DB else get_db_connection()
        
        # Nếu kết nối thất bại, hiển thị thông báo lỗi
        if conn is None and USE_DB:
            flash("Lỗi: Không thể kết nối đến cơ sở dữ liệu. Vui lòng kiểm tra cấu hình.", "error")
            return render_template('dashboard.html', 
                                   sellers=None, 
                                   history=None, 
                                   buyer_id=None)

        cursor = conn.cursor(dictionary=True) if conn else None

        try:
            # Kiểm tra xem form nào được gửi đi
            form_type = request.form.get('form_type')

            if form_type == 'top_sellers':
                # --- Xử lý Form 1: Top Sellers (Demo SP của Người 5) ---
                top_n = request.form.get('top_n', default=5, type=int)
                min_revenue = request.form.get('min_revenue', default=0, type=int)
                
                if conn and cursor:
                    # 1. Gọi SP 'sp_GetTopSellers'
                    cursor.callproc('sp_GetTopSellers', (top_n, min_revenue))
                    # 2. Lấy kết quả
                    collected = []
                    for result in cursor.stored_results():
                        rows = result.fetchall()
                        if rows:
                            collected.extend(rows)
                    seller_results = serialize_rows(collected)
                    flash(f"Đã tìm thấy {len(seller_results)} cửa hàng.", "success")
                else:
                    seller_results = get_mock_top_sellers(top_n, min_revenue)
                    flash("Đang dùng dữ liệu giả (mock) vì chưa kết nối DB.", "warning")

                session['seller_results'] = seller_results

            elif form_type == 'buyer_history':
                # --- Xử lý Form 2: Lịch sử mua (Demo Function của Người 6) ---
                buyer_id = request.form.get('buyer_id')
                buyer_id_lookup = buyer_id # Lưu lại để hiển thị trên form

                if buyer_id:
                    try:
                        buyer_id_int = int(buyer_id)
                    except ValueError:
                        flash("ID người mua phải là số nguyên.", "warning")
                        buyer_id_int = None

                    if buyer_id_int is not None:
                        if conn and cursor:
                            # 1. Gọi Function 'fn_GetBuyerPurchaseHistory'
                            query = "SELECT fn_GetBuyerPurchaseHistory(%s) AS history"
                            cursor.execute(query, (buyer_id_int,))
                            # 2. Lấy kết quả
                            result = cursor.fetchone()
                            if result is not None and 'history' in result:
                                buyer_history = result['history']
                                flash(f"Đã lấy lịch sử cho Buyer ID {buyer_id_int}.", "success")
                        else:
                            buyer_history = get_mock_buyer_history(buyer_id_int)
                            if buyer_history is None:
                                flash("Không tìm thấy lịch sử mua hàng trong dữ liệu mock.", "warning")
                            else:
                                flash("Đang dùng dữ liệu giả (mock) vì chưa kết nối DB.", "warning")
                        session['buyer_history'] = buyer_history
                        session['buyer_id'] = buyer_id_lookup
                else:
                    flash("Vui lòng nhập ID người mua.", "warning")

        except mysql.connector.Error as err:
            # Bắt lỗi nếu SP hoặc Function không tồn tại
            if err.errno == 1305: # 1305 = PROCEDURE/FUNCTION does not exist
                flash(f"Lỗi: {err.msg}. Team DB đã chạy file SQL logic chưa?", "error")
            else:
                flash(f"Lỗi SQL: {err.msg}", "error")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    # Render trang HTML (kể cả khi là 'GET' hay 'POST')
    return render_template(
        'dashboard.html', 
        sellers=seller_results, 
        history=buyer_history,
        buyer_id=buyer_id_lookup
    )

# Điều hướng trang chủ về dashboard để tiện truy cập
@app.route('/')
def index():
    return redirect('/dashboard')

# Thêm các route khác của nhóm bạn ở đây...
# @app.route('/products') ... (Trang của Người 5)
# @app.route('/product-form') ... (Trang của Người 4)


if __name__ == '__main__':
    # Chạy ổn định trên macOS: bind 127.0.0.1, port 5050, tắt reloader và debug
    app.run(host='127.0.0.1', port=5050, debug=False, use_reloader=False, threaded=True)