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
USE_DB = True

# Cấu hình kết nối CSDL MySQL
# LƯU Ý: Cần cập nhật thông tin kết nối database của bạn:
# 1. Đảm bảo đã chạy file SQL để tạo database ShoppeDB và các stored procedures/functions
# 2. Cập nhật host, user, password phù hợp với MySQL server của bạn
# 3. Database name phải là 'ShoppeDB' (khớp với file database objects.sql)
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'giabao123',  # <-- Cập nhật mật khẩu MySQL của bạn tại đây
    'database': 'ShoppeDB'  # Đã sửa từ ShopeeDB thành ShoppeDB để khớp với SQL file
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
                min_revenue = request.form.get('min_revenue', default=0, type=float)
                
                if conn and cursor:
                    # Kiểm tra tổng số sellers trong hệ thống
                    cursor.execute("SELECT COUNT(*) as total_sellers FROM sellers")
                    total_sellers_result = cursor.fetchone()
                    total_sellers = total_sellers_result['total_sellers'] if total_sellers_result else 0
                    
                    # 1. Gọi SP 'sp_GetTopSellers'
                    cursor.callproc('sp_GetTopSellers', (top_n, min_revenue))
                    # 2. Lấy kết quả
                    collected = []
                    for result in cursor.stored_results():
                        rows = result.fetchall()
                        if rows:
                            collected.extend(rows)
                    seller_results = serialize_rows(collected)
                    
                    # Hiển thị thông báo chi tiết
                    if len(seller_results) == 0:
                        flash(f"Không tìm thấy seller nào có doanh thu > {min_revenue:,.0f} VND. (Stored procedure chỉ trả về sellers có đơn hàng đã thanh toán - Paid)", "warning")
                    elif len(seller_results) < top_n:
                        flash(f"Đã tìm thấy {len(seller_results)}/{top_n} sellers có doanh thu > {min_revenue:,.0f} VND. (Chỉ có {len(seller_results)} sellers có đơn hàng đã thanh toán - Paid. Tổng số sellers trong hệ thống: {total_sellers})", "info")
                    else:
                        flash(f"Đã tìm thấy {len(seller_results)} sellers có doanh thu > {min_revenue:,.0f} VND.", "success")
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
                            # Kiểm tra buyer có tồn tại không
                            cursor.execute("SELECT 1 FROM buyers WHERE user_id = %s", (buyer_id_int,))
                            if not cursor.fetchone():
                                buyer_history = None
                                flash(f"Buyer ID {buyer_id_int} không tồn tại trong hệ thống.", "error")
                            else:
                                # Kiểm tra buyer có đơn hàng không
                                cursor.execute("""
                                    SELECT COUNT(*) as order_count 
                                    FROM orders o 
                                    WHERE o.user_id = %s
                                """, (buyer_id_int,))
                                order_result = cursor.fetchone()
                                has_orders = order_result['order_count'] > 0 if order_result else False
                                
                                # Kiểm tra đơn hàng đã thanh toán và giao hàng
                                cursor.execute("""
                                    SELECT COUNT(*) as delivered_count 
                                    FROM orders o
                                    JOIN payment p ON o.order_id = p.order_id
                                    JOIN shipment s ON o.order_id = s.order_id
                                    WHERE o.user_id = %s
                                      AND p.payment_status = 'Paid'
                                      AND s.status = 'Delivered'
                                """, (buyer_id_int,))
                                delivered_result = cursor.fetchone()
                                delivered_count = delivered_result['delivered_count'] if delivered_result else 0
                                
                                # 1. Gọi Function 'fn_GetBuyerPurchaseHistory'
                                query = "SELECT fn_GetBuyerPurchaseHistory(%s) AS history"
                                cursor.execute(query, (buyer_id_int,))
                                # 2. Lấy kết quả
                                result = cursor.fetchone()
                                if result is not None and 'history' in result:
                                    buyer_history = result['history']
                                    # Kiểm tra nếu kết quả là chuỗi rỗng hoặc None
                                    if buyer_history and buyer_history.strip():
                                        flash(f"Đã lấy lịch sử cho Buyer ID {buyer_id_int}. ({delivered_count} đơn đã giao hàng)", "success")
                                    else:
                                        buyer_history = None
                                        if has_orders:
                                            flash(f"Buyer ID {buyer_id_int} có đơn hàng nhưng chưa có đơn nào đã thanh toán và giao hàng thành công. (Function chỉ trả về đơn hàng đã Paid + Delivered)", "warning")
                                        else:
                                            flash(f"Buyer ID {buyer_id_int} chưa có đơn hàng nào.", "warning")
                                else:
                                    buyer_history = None
                                    if has_orders:
                                        flash(f"Buyer ID {buyer_id_int} có đơn hàng nhưng chưa có đơn nào đã thanh toán và giao hàng thành công.", "warning")
                                    else:
                                        flash(f"Buyer ID {buyer_id_int} chưa có đơn hàng nào.", "warning")
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