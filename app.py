from flask import Flask, render_template, request, flash, redirect, session, url_for
import mysql.connector
from decimal import Decimal
from datetime import date
from mock_data import get_mock_buyer_history, get_mock_top_sellers

app = Flask(__name__, template_folder='template')
app.config['SECRET_KEY'] = 'your_secret_key_12345' 
app.config['SESSION_PERMANENT'] = False

USE_DB = True

# --- CẤU HÌNH DB ---
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '22102005bobo', 
    'database': 'ShoppeDB',
    'charset': 'utf8mb4',
    'use_unicode': True
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as err:
        print(f"Lỗi kết nối CSDL: {err}")
        return None

# --- HÀM HỖ TRỢ: LẤY ID TIẾP THEO ---
def get_next_id(cursor, table, id_column):
    cursor.execute(f"SELECT MAX({id_column}) FROM {table}")
    res = cursor.fetchone()
    if res and res[f"MAX({id_column})"]:
        return res[f"MAX({id_column})"] + 1
    return 1000 # Bắt đầu từ 1000 nếu chưa có dữ liệu

# =================================================
# BASIC ROUTES
# =================================================
@app.route('/')
def index():
    return redirect('/login')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# =================================================
# LOGIN
# =================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        if session.get('role') == 'seller':
            return redirect('/productManagement')
        elif session.get('role') == 'buyer':
            return redirect('/buyer/home')

    if request.method == 'GET':
        return render_template('login.html')
    
    user_id = request.form.get('user_id')
    role = request.form.get('role')

    conn = get_db_connection()
    if not conn:
        flash("Lỗi kết nối Database!", "error")
        return redirect('/login')
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        if role == 'seller':
            cursor.execute("SELECT * FROM sellers WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()
            if user:
                session['user_id'] = user_id
                session['role'] = 'seller'
                flash("Xin chào Seller!", "success")
                return redirect('/productManagement')
            else:
                flash(f"ID {user_id} không phải là Seller.", "error")

        elif role == 'buyer':
            cursor.execute("SELECT * FROM buyers WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()
            if user:
                session['user_id'] = user_id
                session['role'] = 'buyer'
                flash("Xin chào Buyer!", "success")
                return redirect('/buyer/home')
            else:
                flash(f"ID {user_id} không phải là Buyer.", "error")

    except Exception as e:
        flash(f"Lỗi: {e}", "error")
    finally:
        cursor.close()
        conn.close()
            
    return redirect('/login')

# =================================================
# BUYER HOME PAGE 
# =================================================
@app.route('/buyer/home', methods=['GET'])
def buyer_home():
    if 'user_id' not in session or session.get('role') != 'buyer':
        return redirect('/login')

    keyword = request.args.get('keyword', None)
    category_id = int(request.args.get('category_id')) if request.args.get('category_id') else None
    min_price = float(request.args.get('min_price')) if request.args.get('min_price') else None
    max_price = float(request.args.get('max_price')) if request.args.get('max_price') else None

    products = []
    cart_count = 0
    conn = get_db_connection()
    
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # Lấy danh sách sản phẩm
            args = (keyword, category_id, min_price, max_price)
            cursor.callproc('sp_SearchProducts', args)
            for result in cursor.stored_results():
                products = result.fetchall()
            
            # Đếm số lượng trong giỏ hàng (Chưa nằm trong HOLD)
            # Logic: Cart = CartItem NOT IN (SELECT cartItem_id FROM hold)
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM cartItem 
                WHERE user_id = %s 
                AND cartItem_id NOT IN (SELECT cartItem_id FROM hold)
            """, (session['user_id'],))
            res = cursor.fetchone()
            cart_count = res['count'] if res else 0

        except Exception as e:
            flash(f"Lỗi: {e}", "error")
        finally:
            cursor.close()
            conn.close()

    return render_template('Homepage.html', products=products, cart_count=cart_count)

# =================================================
# ADD TO CART (Thêm vào giỏ)
# =================================================
@app.route('/addToCart', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session or session.get('role') != 'buyer':
        return redirect('/login')

    user_id = session['user_id']
    product_id = request.form.get('product_id')
    price = float(request.form.get('price'))
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # 1. Kiểm tra xem sản phẩm này đã có trong giỏ chưa (chưa vào HOLD)
            check_query = """
                SELECT cartItem_id, quantity 
                FROM cartItem 
                WHERE user_id = %s AND product_id = %s 
                AND cartItem_id NOT IN (SELECT cartItem_id FROM hold)
            """
            cursor.execute(check_query, (user_id, product_id))
            existing_item = cursor.fetchone()

            if existing_item:
                # Nếu có rồi -> Tăng số lượng lên 1
                new_qty = existing_item['quantity'] + 1
                cursor.execute("UPDATE cartItem SET quantity = %s WHERE cartItem_id = %s", 
                               (new_qty, existing_item['cartItem_id']))
                flash("Đã cập nhật số lượng trong giỏ!", "success")
            else:
                # Nếu chưa có -> Tạo dòng mới trong cartItem
                # Lấy ID mới
                new_id = get_next_id(cursor, "cartItem", "cartItem_id")
                
                # Insert
                # Lưu ý: subtotal là cột GENERATED ALWAYS nên không cần insert
                insert_query = """
                    INSERT INTO cartItem (cartItem_id, user_id, product_id, quantity, unit_price)
                    VALUES (%s, %s, %s, 1, %s)
                """
                cursor.execute(insert_query, (new_id, user_id, product_id, price))
                flash("Đã thêm vào giỏ hàng!", "success")

            conn.commit()
        except mysql.connector.Error as err:
            # Bắt lỗi Trigger check tồn kho
            flash(f"Không thể thêm: {err.msg}", "error")
        except Exception as e:
            flash(f"Lỗi: {e}", "error")
        finally:
            cursor.close()
            conn.close()

    return redirect('/buyer/home')

# =================================================
# VIEW CART (Xem giỏ hàng)
# =================================================
@app.route('/cart')
def view_cart():
    if 'user_id' not in session or session.get('role') != 'buyer':
        return redirect('/login')
    
    user_id = session['user_id']
    cart_items = []
    total_amount = 0
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # Lấy các item trong giỏ (Chưa nằm trong HOLD)
            query = """
                SELECT 
                    ci.cartItem_id, ci.quantity, ci.unit_price, ci.subtotal,
                    p.product_name, p.image_link
                FROM cartItem ci
                JOIN products p ON ci.product_id = p.product_id
                WHERE ci.user_id = %s
                AND ci.cartItem_id NOT IN (SELECT cartItem_id FROM hold)
            """
            cursor.execute(query, (user_id,))
            cart_items = cursor.fetchall()
            
            # Tính tổng tiền
            for item in cart_items:
                total_amount += item['subtotal']
                
        except Exception as e:
            flash(f"Lỗi: {e}", "error")
        finally:
            cursor.close()
            conn.close()

    return render_template('cart.html', cart_items=cart_items, total_amount=total_amount)

# =================================================
# DELETE CART ITEM
# =================================================
@app.route('/cart/delete/<int:item_id>')
def delete_cart_item(item_id):
    if 'user_id' not in session or session.get('role') != 'buyer':
        return redirect('/login')

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM cartItem WHERE cartItem_id = %s", (item_id,))
            conn.commit()
            flash("Đã xóa sản phẩm khỏi giỏ.", "success")
        except Exception as e:
            flash(f"Lỗi: {e}", "error")
        finally:
            cursor.close()
            conn.close()
    return redirect('/cart')

# =================================================
# CHECKOUT (Thanh toán)
# =================================================
@app.route('/checkout', methods=['POST'])
def checkout():
    if 'user_id' not in session or session.get('role') != 'buyer':
        return redirect('/login')
    
    user_id = session['user_id']
    conn = get_db_connection()
    
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # 1. Lấy lại items trong giỏ để tính tổng tiền và ID
            query = """
                SELECT cartItem_id, subtotal 
                FROM cartItem 
                WHERE user_id = %s 
                AND cartItem_id NOT IN (SELECT cartItem_id FROM hold)
            """
            cursor.execute(query, (user_id,))
            items = cursor.fetchall()
            
            if not items:
                flash("Giỏ hàng trống!", "error")
                return redirect('/cart')
            
            total = sum(item['subtotal'] for item in items)
            
            # 2. Tạo Order Mới
            new_order_id = get_next_id(cursor, "orders", "order_id")
            today = date.today()
            
            cursor.execute("""
                INSERT INTO orders (order_id, user_id, order_date, total_amount)
                VALUES (%s, %s, %s, %s)
            """, (new_order_id, user_id, today, total))
            
            # 3. Đưa CartItems vào bảng HOLD (Liên kết Order -> CartItem)
            for item in items:
                cursor.execute("""
                    INSERT INTO hold (order_id, cartItem_id) VALUES (%s, %s)
                """, (new_order_id, item['cartItem_id']))
                
            # 4. Tạo Payment (Mặc định Pending)
            new_payment_id = get_next_id(cursor, "payment", "payment_id")
            cursor.execute("""
                INSERT INTO payment (payment_id, order_id, payment_date, payment_method, amount, payment_status)
                VALUES (%s, %s, %s, 'Bank Transfer', %s, 'Pending')
            """, (new_payment_id, new_order_id, today, total))
            
            # 5. Tạo Shipment (Mặc định Pending)
            new_track_id = get_next_id(cursor, "shipment", "tracking_number")
            # Lấy địa chỉ buyer (đơn giản hóa lấy từ bảng buyers)
            cursor.execute("SELECT shipping_address FROM buyers WHERE user_id = %s", (user_id,))
            buyer_info = cursor.fetchone()
            address = buyer_info['shipping_address'] if buyer_info else "Store Address"
            
            cursor.execute("""
                INSERT INTO shipment (tracking_number, order_id, address, delivery_date, status)
                VALUES (%s, %s, %s, DATE_ADD(%s, INTERVAL 3 DAY), 'Pending')
            """, (new_track_id, new_order_id, address, today))

            conn.commit()
            flash(f"Đặt hàng thành công! Mã đơn: #{new_order_id}", "success")
            return redirect('/my-orders')
            
        except Exception as e:
            conn.rollback()
            flash(f"Lỗi thanh toán: {e}", "error")
        finally:
            cursor.close()
            conn.close()
            
    return redirect('/cart')

# =================================================
# MY ORDERS (Đơn mua)
# =================================================
@app.route('/my-orders')
def my_orders():
    if 'user_id' not in session or session.get('role') != 'buyer':
        return redirect('/login')
    
    user_id = session['user_id']
    orders = []
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # Lấy danh sách đơn hàng + trạng thái thanh toán + vận chuyển
            query = """
                SELECT 
                    o.order_id, o.order_date, o.total_amount,
                    p.payment_status,
                    s.status as delivery_status
                FROM orders o
                LEFT JOIN payment p ON o.order_id = p.order_id
                LEFT JOIN shipment s ON o.order_id = s.order_id
                WHERE o.user_id = %s
                ORDER BY o.order_date DESC
            """
            cursor.execute(query, (user_id,))
            orders = cursor.fetchall()
        except Exception as e:
            flash(f"Lỗi: {e}", "error")
        finally:
            cursor.close()
            conn.close()
            
    return render_template('orders.html', orders=orders)


# --- GIỮ NGUYÊN CÁC ROUTE CỦA SELLER & DASHBOARD NHƯ CŨ ---
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    seller_results = session.get('seller_results', [])
    buyer_history = session.get('buyer_history')
    buyer_id_lookup = session.get('buyer_id')

    def serialize_rows(rows):
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

    if request.method == 'POST':
        conn = get_db_connection() if USE_DB else None
        cursor = conn.cursor(dictionary=True) if conn else None

        try:
            form_type = request.form.get('form_type')
            if form_type == 'top_sellers':
                top_n = request.form.get('top_n', default=5, type=int)
                min_revenue = request.form.get('min_revenue', default=0, type=float)
                if conn:
                    cursor.callproc('sp_GetTopSellers', (top_n, min_revenue))
                    collected = []
                    for result in cursor.stored_results():
                        collected.extend(result.fetchall())
                    seller_results = serialize_rows(collected)
                    flash(f"Tìm thấy {len(seller_results)} kết quả.", "success")
                else:
                    seller_results = get_mock_top_sellers(top_n, min_revenue)
                    flash("Dữ liệu Mock.", "warning")
                session['seller_results'] = seller_results
            elif form_type == 'buyer_history':
                buyer_id = request.form.get('buyer_id')
                buyer_id_lookup = buyer_id
                if buyer_id and conn:
                    try:
                        bid = int(buyer_id)
                        cursor.execute("SELECT fn_GetBuyerPurchaseHistory(%s) AS history", (bid,))
                        res = cursor.fetchone()
                        buyer_history = res['history'] if res else None
                        if buyer_history: flash("Đã lấy lịch sử mua hàng.", "success")
                        else: flash("Không có lịch sử mua hàng.", "warning")
                    except ValueError: flash("ID phải là số.", "error")
                session['buyer_history'] = buyer_history
                session['buyer_id'] = buyer_id_lookup
        except Exception as e:
            flash(f"Lỗi: {e}", "error")
        finally:
            if cursor: cursor.close()
            if conn: conn.close()
    return render_template('dashboard.html', sellers=seller_results, history=buyer_history, buyer_id=buyer_id_lookup)

@app.route('/productManagement', methods=['GET', 'POST'])
def product_management():
    if 'user_id' not in session or session.get('role') != 'seller':
        return redirect('/login')
    seller_id = session['user_id']
    conn = get_db_connection()
    products = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            query = """
                SELECT p.product_id, p.product_name, p.image_link, p.price,
                    c.quantity_in_stock, i.update_at, s.store_name
                FROM sellers sel
                JOIN store s ON sel.user_id = s.user_id
                JOIN inventory i ON s.store_id = i.store_id
                JOIN contain c ON i.inventory_id = c.inventory_id
                JOIN products p ON c.product_id = p.product_id
                WHERE sel.user_id = %s AND p.product_name NOT LIKE '%%[DELETED]%%'
                ORDER BY p.product_id DESC
            """
            cursor.execute(query, (seller_id,))
            products = cursor.fetchall()
        except Exception as e:
            flash(f"Lỗi lấy danh sách: {e}", "error")
        finally:
            cursor.close()
            conn.close()
    return render_template('productManagement.html', products=products)

@app.route('/addProduct', methods=['GET', 'POST'])
def add_product():
    if 'user_id' not in session or session.get('role') != 'seller':
        return redirect('/login')
    if request.method == 'GET':
        return render_template('addProduct.html')
    conn = get_db_connection()
    try:
        p_id = int(request.form['product_id'])
        p_name = request.form['product_name']
        p_cat_id = int(request.form['category_id'])
        p_desc = request.form.get('description', '') 
        p_price = float(request.form['price'])
        p_image = request.form.get('image_link', '')
        p_inv_id = int(request.form['inventory_id'])
        p_stock = int(request.form['initial_stock'])
        if conn:
            cursor = conn.cursor()
            args = (p_id, p_cat_id, p_name, p_desc, p_price, p_image, p_inv_id, p_stock)
            cursor.callproc('sp_InsertProduct', args)
            conn.commit()
            flash(f"Thêm thành công sản phẩm: {p_name}", "success")
            return redirect('/productManagement')
    except mysql.connector.Error as err:
        flash(f"Lỗi SQL: {err.msg}", "error")
    except Exception as e:
        flash(f"Lỗi: {e}", "error")
    finally:
        if conn: conn.close()
    return render_template('addProduct.html')

@app.route('/updateProduct/<int:product_id>', methods=['GET', 'POST'])
def update_product(product_id):
    if 'user_id' not in session or session.get('role') != 'seller':
        return redirect('/login')
    conn = get_db_connection()
    if not conn: return redirect('/productManagement')
    cursor = conn.cursor(dictionary=True)
    if request.method == 'GET':
        try:
            cursor.execute("SELECT * FROM products WHERE product_id = %s", (product_id,))
            product = cursor.fetchone()
            if not product: return redirect('/productManagement')
            return render_template('updateProduct.html', product=product)
        finally:
            cursor.close()
            conn.close()
    try:
        p_name = request.form['product_name']
        p_cat_id = int(request.form['category_id'])
        p_desc = request.form.get('description', '')
        p_price = float(request.form['price'])
        p_image = request.form.get('image_link', '')
        args = (product_id, p_cat_id, p_name, p_desc, p_price, p_image)
        cursor.callproc('sp_UpdateProduct', args)
        conn.commit()
        flash(f"Cập nhật thành công sản phẩm #{product_id}", "success")
        return redirect('/productManagement')
    except Exception as e:
        flash(f"Lỗi: {e}", "error")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
    return redirect(url_for('updateProduct', product_id=product_id))

@app.route('/deleteProduct/<int:product_id>', methods=['GET'])
def delete_product(product_id):
    if 'user_id' not in session or session.get('role') != 'seller':
        return redirect('/login')
    conn = get_db_connection()
    if not conn: return redirect('/productManagement')
    try:
        cursor = conn.cursor()
        cursor.callproc('sp_DeleteProduct', (product_id,))
        conn.commit()
        flash(f"Đã xóa thành công sản phẩm #{product_id}", "success")
    except Exception as e:
        flash(f"Lỗi: {e}", "error")
    finally:
        conn.close()
    return redirect('/productManagement')

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5050, debug=False, use_reloader=False, threaded=True)