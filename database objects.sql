USE ShoppeDB;

DROP TRIGGER IF EXISTS trg_CheckStockBeforeOrder;
DROP TRIGGER IF EXISTS trg_UpdateStoreRating;
DROP PROCEDURE IF EXISTS sp_InsertProduct;
DROP PROCEDURE IF EXISTS sp_UpdateProduct;
DROP PROCEDURE IF EXISTS sp_DeleteProduct;
DROP PROCEDURE IF EXISTS sp_SearchProducts;
DROP PROCEDURE IF EXISTS sp_GetTopSellers;
DROP FUNCTION IF EXISTS fn_GetBuyerPurchaseHistory;
DROP FUNCTION IF EXISTS fn_CalculateSellerRevenue;
DELIMITER $$

/* Trigger 1: Check tồn kho trước khi thêm cartItem */
CREATE TRIGGER trg_CheckStockBeforeOrder
BEFORE INSERT ON cartItem
FOR EACH ROW
BEGIN
  DECLARE available INT;
  SELECT COALESCE(SUM(c.quantity_in_stock), 0)
    INTO available
  FROM contain c
  WHERE c.product_id = NEW.product_id;

  IF NEW.quantity > available THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Không đủ hàng tồn kho';
  END IF;
END$$

/* Trigger 2: Cập nhật StoreRating sau khi có review mới */
CREATE TRIGGER trg_UpdateStoreRating
AFTER INSERT ON review
FOR EACH ROW
BEGIN
  UPDATE store s
  JOIN (
        SELECT i.store_id, ROUND(AVG(r.score), 1) AS avg_score
        FROM inventory i
        JOIN contain c ON c.inventory_id = i.inventory_id
        JOIN review  r ON r.product_id   = c.product_id
        GROUP BY i.store_id
       ) t ON t.store_id = s.store_id
  JOIN (
        SELECT DISTINCT i2.store_id
        FROM inventory i2
        JOIN contain c2 ON c2.inventory_id = i2.inventory_id
        WHERE c2.product_id = NEW.product_id
       ) hit ON hit.store_id = s.store_id
  SET s.store_rating = t.avg_score;

END$$

-- 1. INSERT PRODUCT
CREATE PROCEDURE sp_InsertProduct (
    IN p_product_id INT,
    IN p_category_id INT,
    IN p_name VARCHAR(255),
    IN p_desc VARCHAR(1000),
    IN p_price DECIMAL(10,2),
    IN p_image VARCHAR(255),
    IN p_inventory_id INT,
    IN p_initial_stock INT
)
BEGIN
    -- Check category tồn tại
    IF NOT EXISTS (SELECT 1 FROM category WHERE category_id = p_category_id) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Category không tồn tại';
    END IF;

    -- Check inventory tồn tại
    IF NOT EXISTS (SELECT 1 FROM inventory WHERE inventory_id = p_inventory_id) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Inventory không tồn tại';
    END IF;

    -- Check giá và số lượng
    IF (p_price <= 0 OR p_initial_stock < 0) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Giá và số lượng phải lớn hơn 0';
    END IF;

    -- Insert product
    INSERT INTO products (product_id, category_id, product_name, product_description, price, image_link)
    VALUES (p_product_id, p_category_id, p_name, p_desc, p_price, p_image);

    -- Insert tồn kho vào contain
    INSERT INTO contain (inventory_id, product_id, quantity_in_stock)
    VALUES (p_inventory_id, p_product_id, p_initial_stock);
END$$


-- 2. UPDATE PRODUCT
CREATE PROCEDURE sp_UpdateProduct (
    IN p_product_id INT,
    IN p_category_id INT,
    IN p_name VARCHAR(255),
    IN p_desc VARCHAR(1000),
    IN p_price DECIMAL(10,2),
    IN p_image VARCHAR(255)
)
BEGIN
    IF NOT EXISTS (SELECT 1 FROM products WHERE product_id = p_product_id) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Product không tồn tại';
    END IF;

    UPDATE products
    SET category_id = p_category_id,
        product_name = p_name,
        product_description = p_desc,
        price = p_price,
        image_link = p_image
    WHERE product_id = p_product_id;
END$$


-- 3. DELETE PRODUCT (Soft delete)
CREATE PROCEDURE sp_DeleteProduct (
    IN p_product_id INT
)
BEGIN
    -- Không cho xoá nếu còn trong đơn hàng HOLD
    IF EXISTS (
        SELECT 1
        FROM hold h
        JOIN cartItem c ON h.cartItem_id = c.cartItem_id
        WHERE c.product_id = p_product_id
    ) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Không thể xoá - sản phẩm đang trong đơn HOLD';
    END IF;

    -- Soft delete: cập nhật mô tả để đánh dấu thay vì xoá
    UPDATE products
    SET product_name = CONCAT(product_name, ' [DELETED]'),
        product_description = CONCAT(product_description, ' | Sản phẩm đã bị vô hiệu')
    WHERE product_id = p_product_id;
END$$

CREATE PROCEDURE sp_SearchProducts(
    IN p_Keyword VARCHAR(255),
    IN p_CategoryID INT,
    IN p_MinPrice DECIMAL(10,0),
    IN p_MaxPrice DECIMAL(10,0)
)
BEGIN
    SELECT 
        p.product_id,
        p.product_name,
        p.price,
        c.category_name,
        p.image_link,
        p.product_description
    FROM 
        products p
    JOIN 
        category c ON p.category_id = c.category_id
    WHERE
        -- 1. Lọc theo Từ khóa (Keyword)
        (p_Keyword IS NULL OR p_Keyword = '' OR 
         p.product_name LIKE CONCAT('%', p_Keyword, '%') OR 
         p.product_description LIKE CONCAT('%', p_Keyword, '%'))
        
    AND
        -- 2. Lọc theo Danh mục (Category)
        (p_CategoryID IS NULL OR p.category_id = p_CategoryID)
        
    AND
        -- 3. Lọc theo Khoảng giá (Price Range)
        (p.price BETWEEN IFNULL(p_MinPrice, 0) AND IFNULL(p_MaxPrice, 9999999999))
        
    ORDER BY
		p.price ASC; -- Sắp xếp theo giá tăng dần

END$$

CREATE FUNCTION fn_GetBuyerPurchaseHistory (BuyerID INT)
RETURNS TEXT
DETERMINISTIC
BEGIN
    DECLARE ProductList TEXT DEFAULT '';
    DECLARE ProductID INT;
    DECLARE ProductName VARCHAR(255);
    DECLARE done INT DEFAULT 0;

    DECLARE product_cursor CURSOR FOR
        SELECT DISTINCT ci.product_id
        FROM orders o
        JOIN hold h ON o.order_id = h.order_id
        JOIN cartItem ci ON h.cartItem_id = ci.cartItem_id
        JOIN payment p ON o.order_id = p.order_id
        JOIN shipment s ON o.order_id = s.order_id
        WHERE o.user_id = BuyerID
          AND p.payment_status = 'Paid'
          AND s.status = 'Delivered';

	DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = 1;

    OPEN product_cursor;
    read_loop: LOOP
        FETCH product_cursor INTO ProductID;
        IF done = 1 THEN
            LEAVE read_loop;
        END IF;

        SELECT product_name INTO ProductName
        FROM products
        WHERE product_id = ProductID;

        IF ProductName IS NOT NULL THEN
            SET ProductList = CONCAT(ProductList, ProductName, ', ');
        END IF;
    END LOOP;

    CLOSE product_cursor;

    RETURN TRIM(TRAILING ', ' FROM ProductList);
END$$

CREATE PROCEDURE sp_GetTopSellers(
    IN p_TopN INT,                 
    IN p_MinRevenue DECIMAL(12, 2) 
)
BEGIN
    SELECT
        s.user_id AS SellerID,
        GROUP_CONCAT(DISTINCT st.store_name SEPARATOR ', ') AS StoreNames,
        SUM(ci.subtotal) AS TotalRevenue,
        COUNT(DISTINCT o.order_id) AS TotalOrders
    FROM
        sellers s
    JOIN
        store st ON s.user_id = st.user_id
    JOIN
        inventory i ON st.store_id = i.store_id
    JOIN
        contain c ON i.inventory_id = c.inventory_id
    JOIN
        cartItem ci ON c.product_id = ci.product_id
    JOIN
        hold h ON ci.cartItem_id = h.cartItem_id
    JOIN
        orders o ON h.order_id = o.order_id
    JOIN
        payment p ON o.order_id = p.order_id
    WHERE
        p.payment_status = 'Paid'
    GROUP BY
        s.user_id
    HAVING
        TotalRevenue > p_MinRevenue
    ORDER BY
        TotalRevenue DESC
    LIMIT p_TopN;
END$$
DELIMITER ;


DELIMITER $$
CREATE FUNCTION fn_CalculateSellerRevenue(
    p_SellerID  INT,
    p_StartDate DATE,
    p_EndDate   DATE
)
RETURNS DECIMAL(10)
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE v_done      INT DEFAULT 0;
    DECLARE v_order_id  INT;
    DECLARE v_revenue   DECIMAL(10) DEFAULT 0;
    DECLARE v_add       DECIMAL(10) DEFAULT 0;

    -- CURSOR browse all order from start to end date
    DECLARE cur_orders CURSOR FOR
        SELECT o.order_id
        FROM orders o
        JOIN payment p  ON p.order_id = o.order_id
        WHERE p.payment_status = 'Paid'
          AND o.order_date BETWEEN p_StartDate AND p_EndDate;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_done = 1;

    OPEN cur_orders;
    read_loop: LOOP
        FETCH cur_orders INTO v_order_id;
        IF v_done = 1 THEN
            LEAVE read_loop;
        END IF;

        -- Update the revenue of seller on the current order amount
        -- Query from HOLD -> CARTITEM -> (EXISTS) CONTAIN -> INVENTORY -> STORE -> SELLER
        -- Use EXISTS to avoid adding the same product in order inventory.
        SELECT COALESCE(SUM(ci.subtotal), 0) INTO v_add
        FROM hold h
        JOIN cartItem ci ON ci.cartItem_id = h.cartItem_id
        WHERE h.order_id = v_order_id
          AND EXISTS (
                SELECT 1
                FROM contain c
                JOIN inventory i ON i.inventory_id = c.inventory_id
                JOIN store     s ON s.store_id     = i.store_id
                -- seller chính là s.user_id (khóa đến sellers.user_id)
                WHERE c.product_id = ci.product_id
                  AND s.user_id    = p_SellerID
          );

        SET v_revenue = v_revenue + v_add;
    END LOOP;

    CLOSE cur_orders;

    RETURN v_revenue;
END $$
