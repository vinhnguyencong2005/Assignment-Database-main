-- 04_tests.sql
USE ShoppeDB;

-- Xem triggers
SHOW TRIGGERS;

-- Test Trigger 1: thiếu hàng -> phải báo lỗi
-- (tăng quantity vượt tổng tồn của product 1002 là 200)
START TRANSACTION;
  INSERT INTO cartItem (cartItem_id, user_id, product_id, quantity, unit_price)
  VALUES (5009, 3, 1002, 300, 125000);   -- EXPECT: lỗi "Không đủ hàng tồn kho"
ROLLBACK;

-- Thêm cartItem đủ hàng -> OK
INSERT INTO cartItem (cartItem_id, user_id, product_id, quantity, unit_price)
VALUES (5010, 3, 1002, 3, 125000);

-- Test Trigger 2: thêm review mới -> cập nhật store_rating của store bán sản phẩm đó
SELECT DISTINCT i.store_id
FROM inventory i
JOIN contain c ON c.inventory_id = i.inventory_id
WHERE c.product_id = 1000;

SELECT s.store_id, s.store_rating
FROM store s
ORDER BY s.store_id;

START TRANSACTION;
  INSERT INTO review (review_id, product_id, user_id, `date`, review_comment, score)
  VALUES (6002, 1000, 2, '2025-10-21', 'Chuột lởm, pin trâu.', 3);
  -- Kiểm tra rating sau khi thêm review
  SELECT s.store_id, s.store_rating
  FROM store s
  WHERE s.store_id IN (
    SELECT DISTINCT i.store_id
    FROM inventory i
    JOIN contain c ON c.inventory_id = i.inventory_id
    WHERE c.product_id = 1000
  )
  ORDER BY s.store_id;
ROLLBACK;

-- 1. TEST INSERT PRODUCT
CALL sp_InsertProduct(
    2012,                
    1,                   
    'Loa Bluetooth Mini',
    'Loa chống nước, bass mạnh',
    250000,
    'https://example.com/loa.jpg',
    100,                 
    20                   
);

SELECT 'KẾT QUẢ SAU INSERT (products)' AS Message;
SELECT * FROM products WHERE product_id = 2012;

SELECT 'KẾT QUẢ SAU INSERT (contain)' AS Message;
SELECT * FROM contain WHERE product_id = 2012;

-- 2. TEST UPDATE PRODUCT
CALL sp_UpdateProduct(
    2012,
    1,
    'Loa Bluetooth Pro',
    'Loa to hơn, pin 12 tiếng, chống nước IPX7',
    350000,
    'https://example.com/loapro.jpg'
);

SELECT 'KẾT QUẢ SAU UPDATE' AS Message;
SELECT * FROM products WHERE product_id = 2012;

-- 3. TEST DELETE PRODUCT
CALL sp_DeleteProduct(2012);

SELECT 'KẾT QUẢ SAU DELETE' AS Message;
SELECT * FROM products WHERE product_id = 2012;

-- 1. Test xem TẤT CẢ sản phẩm (7 sản phẩm)
-- (Gửi NULL cho mọi bộ lọc)
CALL sp_SearchProducts(NULL, NULL, NULL, NULL);

-- 2. Test lọc theo TỪ KHÓA
-- (Tìm 'bàn')
CALL sp_SearchProducts('bàn', NULL, NULL, NULL);

-- 3. Test lọc theo DANH MỤC
-- (Tìm 'Điện tử' - CategoryID = 1)
CALL sp_SearchProducts(NULL, 1, NULL, NULL);

-- 4. Test lọc theo KHOẢNG GIÁ
-- (Tìm sản phẩm giá dưới 200,000)
CALL sp_SearchProducts(NULL, NULL, 0, 200000);

-- 5. Test lọc KẾT HỢP
-- (Tìm 'chuột' (keyword) thuộc 'Điện tử' (Cat 1) giá dưới 200,000)
CALL sp_SearchProducts('chuột', 1, 0, 200000);

-- Buyer 1 (user_id=1) có order 3000: Paid và Delivered, chứa product 1000 và 1001.
-- => Return chuỗi: "Chuột không dây Logitech MX Master 2S, Bàn phím cơ không dây AULA F75 đen"
SELECT fn_GetBuyerPurchaseHistory(1) AS PurchaseHistory;

-- Buyer 8 (user_id=8) có order 3002: Paid và Delivered, chứa product 1003.
-- => Return chuỗi: "Máy hút bụi công nghiệp đa năng khô và ướt Yili YLW-6263A loại 12 lít công suất 1200W"
SELECT fn_GetBuyerPurchaseHistory(8) AS PurchaseHistory;
##ANH KIET
-- CALL sp_GetTopSellers(10, 1);
-- top 5 sellers doanh thu toi thieu 100000
CALL sp_GetTopSellers(5, 100000);

-- Test kiểm tra tổng doanh thu của seller có sellerID = 4 từ ngày 20-10-2025 đến 31-10-2025 và lưu biến vào revenue
SELECT fn_CalculateSellerRevenue(4, '2025-10-20', '2025-10-31') AS revenue;