from flask import Flask, render_template, request, flash, redirect, session, url_for
import mysql.connector
from decimal import Decimal
from mock_data import get_mock_buyer_history, get_mock_top_sellers

app = Flask(__name__, template_folder='template')
app.config['SECRET_KEY'] = 'your_secret_key_12345' 
app.config['SESSION_PERMANENT'] = False

USE_DB = True

# --- CẤU HÌNH DB ---
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'giabao123', 
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
    if 'user_id' in session and session.get('role') == 'seller':
        return redirect('/productManagement')

    if request.method == 'GET':
        return render_template('login.html')
    
    user_id = request.form.get('user_id')
    role = request.form.get('role')

    conn = get_db_connection()
    if not conn:
        flash("Lỗi kết nối Database!", "error")
        return redirect('/login')
    
    cursor = conn.cursor(dictionary=True)
    if role == 'seller':
        try:
            cursor.execute("SELECT * FROM sellers WHERE user_id = %s", (user_id,))
            seller = cursor.fetchone()
            if seller:
                session['user_id'] = user_id
                session['role'] = 'seller'
                flash("Đăng nhập thành công!", "success")
                return redirect('/productManagement')
            else:
                flash(f"User ID {user_id} không hợp lệ.", "error")
        except Exception as e:
            flash(f"Lỗi: {e}", "error")
        finally:
            cursor.close()
            conn.close()
            
    return redirect('/login')

# =================================================
# DASHBOARD (Leader)
# =================================================
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

# =================================================
# PRODUCT MANAGEMENT 
# =================================================
@app.route('/productManagement', methods=['GET', 'POST'])
def product_management():
    if 'user_id' not in session or session.get('role') != 'seller':
        return redirect('/login')
    
    seller_id = session['user_id']
    conn = get_db_connection()
    products = []
    categories = []
    
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # Lấy danh sách categories để hiển thị dropdown
            cursor.execute("SELECT category_id, category_name FROM category ORDER BY category_id")
            categories = cursor.fetchall()
            
            # Xử lý tìm kiếm nếu có
            if request.method == 'POST' or (request.method == 'GET' and any([
                request.args.get('keyword'),
                request.args.get('category_id'),
                request.args.get('min_price'),
                request.args.get('max_price')
            ])):
                # Lấy các tham số từ form hoặc query string
                keyword = request.form.get('keyword') or request.args.get('keyword') or None
                category_id = request.form.get('category_id') or request.args.get('category_id') or None
                min_price = request.form.get('min_price') or request.args.get('min_price') or None
                max_price = request.form.get('max_price') or request.args.get('max_price') or None
                
                # Chuyển đổi kiểu dữ liệu
                if category_id:
                    try:
                        category_id = int(category_id)
                    except ValueError:
                        category_id = None
                
                if min_price:
                    try:
                        min_price = float(min_price)
                    except ValueError:
                        min_price = None
                
                if max_price:
                    try:
                        max_price = float(max_price)
                    except ValueError:
                        max_price = None
                
                # Gọi stored procedure sp_SearchProducts
                try:
                    cursor.callproc('sp_SearchProducts', (
                        keyword if keyword else None,
                        category_id if category_id else None,
                        min_price if min_price else None,
                        max_price if max_price else None
                    ))
                    
                    # Lấy kết quả từ stored procedure
                    search_results = []
                    for result in cursor.stored_results():
                        search_results.extend(result.fetchall())
                    
                    # Lấy danh sách product_id từ kết quả tìm kiếm
                    product_ids = [r['product_id'] for r in search_results] if search_results else []
                    
                    # Lấy thông tin chi tiết của các sản phẩm thuộc seller
                    if product_ids:
                        placeholders = ','.join(['%s'] * len(product_ids))
                        query = f"""
                            SELECT 
                                p.product_id, p.product_name, p.image_link, p.price,
                                c.quantity_in_stock, i.update_at, s.store_name
                            FROM sellers sel
                            JOIN store s ON sel.user_id = s.user_id
                            JOIN inventory i ON s.store_id = i.store_id
                            JOIN contain c ON i.inventory_id = c.inventory_id
                            JOIN products p ON c.product_id = p.product_id
                            WHERE sel.user_id = %s
                              AND p.product_id IN ({placeholders})
                              AND p.product_name NOT LIKE '%[DELETED]%'
                            ORDER BY p.product_id DESC
                        """
                        cursor.execute(query, (seller_id, *product_ids))
                        products = cursor.fetchall()
                    else:
                        products = []
                        
                except mysql.connector.Error as err:
                    flash(f"Lỗi tìm kiếm: {err.msg}", "error")
                    products = []
            else:
                # Hiển thị tất cả sản phẩm của seller (không tìm kiếm)
                query = """
                    SELECT 
                        p.product_id, p.product_name, p.image_link, p.price,
                        c.quantity_in_stock, i.update_at, s.store_name
                    FROM sellers sel
                    JOIN store s ON sel.user_id = s.user_id
                    JOIN inventory i ON s.store_id = i.store_id
                    JOIN contain c ON i.inventory_id = c.inventory_id
                    JOIN products p ON c.product_id = p.product_id
                    WHERE sel.user_id = %s
                      AND p.product_name NOT LIKE '%[DELETED]%'
                    ORDER BY p.product_id DESC
                """
                cursor.execute(query, (seller_id,))
                products = cursor.fetchall()
                
        except Exception as e:
            flash(f"Lỗi lấy danh sách: {e}", "error")
        finally:
            cursor.close()
            conn.close()

    return render_template('productManagement.html', products=products, categories=categories)

# =================================================
# MARKETPLACE (Thị Trường - Hiển thị tất cả sản phẩm)
# =================================================
@app.route('/marketplace', methods=['GET', 'POST'])
def marketplace():
    if 'user_id' not in session or session.get('role') != 'seller':
        return redirect('/login')
    
    conn = get_db_connection()
    products = []
    categories = []
    
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # Lấy danh sách categories để hiển thị dropdown
            cursor.execute("SELECT category_id, category_name FROM category ORDER BY category_id")
            categories = cursor.fetchall()
            
            # Xử lý tìm kiếm nếu có
            if request.method == 'POST' or (request.method == 'GET' and any([
                request.args.get('keyword'),
                request.args.get('category_id'),
                request.args.get('min_price'),
                request.args.get('max_price')
            ])):
                # Lấy các tham số từ form hoặc query string
                keyword = request.form.get('keyword') or request.args.get('keyword') or None
                category_id = request.form.get('category_id') or request.args.get('category_id') or None
                min_price = request.form.get('min_price') or request.args.get('min_price') or None
                max_price = request.form.get('max_price') or request.args.get('max_price') or None
                
                # Chuyển đổi kiểu dữ liệu
                if category_id:
                    try:
                        category_id = int(category_id)
                    except ValueError:
                        category_id = None
                
                if min_price:
                    try:
                        min_price = float(min_price)
                    except ValueError:
                        min_price = None
                
                if max_price:
                    try:
                        max_price = float(max_price)
                    except ValueError:
                        max_price = None
                
                # Gọi stored procedure sp_SearchProducts
                try:
                    cursor.callproc('sp_SearchProducts', (
                        keyword if keyword else None,
                        category_id if category_id else None,
                        min_price if min_price else None,
                        max_price if max_price else None
                    ))
                    
                    # Lấy kết quả từ stored procedure
                    search_results = []
                    for result in cursor.stored_results():
                        search_results.extend(result.fetchall())
                    
                    # Lấy danh sách product_id từ kết quả tìm kiếm
                    product_ids = [r['product_id'] for r in search_results] if search_results else []
                    
                    # Lấy thông tin chi tiết của TẤT CẢ sản phẩm (không filter theo seller)
                    if product_ids:
                        placeholders = ','.join(['%s'] * len(product_ids))
                        query = f"""
                            SELECT 
                                p.product_id, p.product_name, p.image_link, p.price,
                                p.product_description, c.category_name,
                                COALESCE(SUM(c2.quantity_in_stock), 0) as total_stock,
                                GROUP_CONCAT(DISTINCT s.store_name SEPARATOR ', ') as store_names
                            FROM products p
                            JOIN category c ON p.category_id = c.category_id
                            LEFT JOIN contain c2 ON p.product_id = c2.product_id
                            LEFT JOIN inventory i ON c2.inventory_id = i.inventory_id
                            LEFT JOIN store s ON i.store_id = s.store_id
                            WHERE p.product_id IN ({placeholders})
                              AND p.product_name NOT LIKE '%[DELETED]%'
                            GROUP BY p.product_id, p.product_name, p.image_link, p.price, p.product_description, c.category_name
                            ORDER BY p.price ASC
                        """
                        cursor.execute(query, tuple(product_ids))
                        products = cursor.fetchall()
                    else:
                        products = []
                        
                except mysql.connector.Error as err:
                    flash(f"Lỗi tìm kiếm: {err.msg}", "error")
                    products = []
            else:
                # Hiển thị TẤT CẢ sản phẩm (không filter theo seller)
                query = """
                    SELECT 
                        p.product_id, p.product_name, p.image_link, p.price,
                        p.product_description, c.category_name,
                        COALESCE(SUM(c2.quantity_in_stock), 0) as total_stock,
                        GROUP_CONCAT(DISTINCT s.store_name SEPARATOR ', ') as store_names
                    FROM products p
                    JOIN category c ON p.category_id = c.category_id
                    LEFT JOIN contain c2 ON p.product_id = c2.product_id
                    LEFT JOIN inventory i ON c2.inventory_id = i.inventory_id
                    LEFT JOIN store s ON i.store_id = s.store_id
                    WHERE p.product_name NOT LIKE '%[DELETED]%'
                    GROUP BY p.product_id, p.product_name, p.image_link, p.price, p.product_description, c.category_name
                    ORDER BY p.price ASC
                """
                cursor.execute(query)
                products = cursor.fetchall()
                
        except Exception as e:
            flash(f"Lỗi lấy danh sách: {e}", "error")
        finally:
            cursor.close()
            conn.close()

    return render_template('marketplace.html', products=products, categories=categories)

# =================================================
# INSERT PRODUCT
# =================================================
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

# =================================================
# UPDATE PRODUCT
# =================================================
@app.route('/updateProduct/<int:product_id>', methods=['GET', 'POST'])
def update_product(product_id):
    if 'user_id' not in session or session.get('role') != 'seller':
        return redirect('/login')

    conn = get_db_connection()
    if not conn:
        flash("Lỗi kết nối DB", "error")
        return redirect('/productManagement')

    cursor = conn.cursor(dictionary=True)

    if request.method == 'GET':
        try:
            cursor.execute("SELECT * FROM products WHERE product_id = %s", (product_id,))
            product = cursor.fetchone()
            
            if not product:
                flash("Sản phẩm không tồn tại.", "error")
                return redirect('/productManagement')
            
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

    except mysql.connector.Error as err:
        flash(f"Lỗi SQL khi Update: {err.msg}", "error")
    except Exception as e:
        flash(f"Lỗi: {e}", "error")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

    return redirect(url_for('updateProduct', product_id=product_id))

# =================================================
# DELETE PRODUCT 
# =================================================
@app.route('/deleteProduct/<int:product_id>', methods=['GET'])
def delete_product(product_id):
    if 'user_id' not in session or session.get('role') != 'seller':
        return redirect('/login')

    conn = get_db_connection()
    if not conn:
        flash("Lỗi hệ thống: Không thể kết nối Database.", "error")
        return redirect('/productManagement')

    try:
        cursor = conn.cursor()
        cursor.callproc('sp_DeleteProduct', (product_id,))
        conn.commit()
        
        flash(f"Đã xóa thành công sản phẩm #{product_id}", "success")
        
    except mysql.connector.Error as err:
        print(f"Lỗi MySQL: {err.msg}")
        flash(f"Không thể xóa: {err.msg}", "error")
        
    except Exception as e:
        print(f"Lỗi: {e}")
        flash(f"Lỗi không xác định: {e}", "error")
        
    finally:
        conn.close()
    
    return redirect('/productManagement')

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5050, debug=False, use_reloader=False, threaded=True)