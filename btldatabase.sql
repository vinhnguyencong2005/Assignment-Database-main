DROP DATABASE IF EXISTS ShoppeDB;
Create DATABASE ShoppeDB;
USE ShoppeDB;

##BUYER
create table users(
	user_id int PRIMARY KEY ,
    email VARCHAR(100) NOT NULL ,
    Phone_number VARCHAR(15) ,
    create_Date DATE ,
    CONSTRAINT UQ_USERS_EMAIL UNIQUE(email),
    CONSTRAINT UQ_USERS_PHONE UNIQUE(Phone_number)
    );

##BUYER(subtype of user)
create table buyers(
	user_id int PRIMARY KEY ,
    payment_method VARCHAR(50) ,
    shipping_address VARCHAR(255) NOT NULL ,
    loyalty_points INT DEFAULT 0 ,
    CONSTRAINT fk_buyers_user
    FOREIGN KEY(user_id) REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE ,
    CHECK (loyalty_points >= 0)
);
##SELLER(subtype of user)
create table sellers(
	user_id int PRIMARY KEY ,
    business_licenses VARCHAR(50) NOT NULL ,
    bank_code VARCHAR(20),
    bank_account VARCHAR(30) NOT NULL ,
    CONSTRAINT uq_business_licenses UNIQUE(business_licenses) ,
    CONSTRAINT uq_bank_account UNIQUE(bank_account) ,
    CONSTRAINT fk_sellers_user
    FOREIGN KEY(user_id) REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE
    );
## STORE
create table store(
	store_id INT PRIMARY KEY ,
    user_id INT NOT NULL ,
    store_name VARCHAR(50) NOT NULL ,
    store_rating DECIMAL(2,1) ,
    CONSTRAINT fk_store_seller
    FOREIGN KEY(user_id) REFERENCES sellers(user_id)
    ON DELETE RESTRICT ON UPDATE CASCADE ,
    CHECK (store_rating IS NULL OR store_rating BETWEEN 1 AND 5)
    );
## INVENTORY
create table inventory(
	inventory_id INT PRIMARY KEY ,
    store_id INT NOT NULL  ,
    update_at DATETIME DEFAULT CURRENT_TIMESTAMP 
			  ON UPDATE CURRENT_TIMESTAMP ,
	CONSTRAINT fk_inventory_store
    FOREIGN KEY(store_id) REFERENCES store(store_id)
    ON DELETE RESTRICT ON UPDATE CASCADE 
    );
## CATAGORY
create table category(
	category_id INT PRIMARY KEY ,
    category_name VARCHAR(100) NOT NULL
    );
## PRODUCT
create table products(
	product_id INT PRIMARY KEY ,
    category_id INT NOT NULL,
    image_link VARCHAR(255),
    product_name VARCHAR(255) NOT NULL ,
    product_description VARCHAR(1000) NOT NULL ,
    price DECIMAL(10) NOT NULL ,
    CONSTRAINT fk_product_catagory
    FOREIGN KEY(category_id) REFERENCES category(category_id)
    ON DELETE RESTRICT ON UPDATE CASCADE ,
    CHECK(price > 0)
    );
## REVIEW 

create table review(
	review_id INT PRIMARY KEY ,
    product_id INT NOT NULL  ,
    user_id INT NOT NULL  ,
    date DATE NOT NULL ,
    review_comment VARCHAR(1000) NOT NULL ,
    score INT NOT NULL ,
    CONSTRAINT fk_review_buyer
    FOREIGN KEY(user_id) REFERENCES buyers(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE ,
    CONSTRAINT fk_review_products
    FOREIGN KEY(product_id) REFERENCES products(product_id)
    ON DELETE CASCADE ON UPDATE CASCADE ,
    CONSTRAINT uq_review_once UNIQUE(user_id, product_id) ,
	CHECK(score between 1 and 5)
    );
## MAKE REPORT
create table reports(
	product_id INT  ,
    user_id INT  ,
    title VARCHAR(255) NOT NULL ,
    reason VARCHAR(1000) NOT NULL ,
    PRIMARY KEY (product_id, user_id) ,
    CONSTRAINT fk_reports_products
    FOREIGN KEY(product_id) REFERENCES products(product_id)
    ON DELETE CASCADE ON UPDATE CASCADE ,
    CONSTRAINT fk_reports_buyers
    FOREIGN KEY(user_id) REFERENCES buyers(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE 
    
    );

##VOUCHER
create table vouchers(
	voucher_id INT PRIMARY KEY ,
    descriptions VARCHAR(255) NOT NULL ,
    discount_value DECIMAL(10) NOT NULL ,
    start_date DATE NOT NULL ,
    end_date DATE NOT NULL ,
    voucher_status ENUM('Active','Expired','Disabled') Default 'Active' ,
    minimum_value DECIMAL(10) NOT NULL ,
    quantity INT NOT NULL ,
    check(start_date < end_date) ,
    check(discount_value > 0) ,
    check(minimum_value >= 0) ,
    check(quantity > 0)
    );

##ORDER
create table orders(
	order_id INT PRIMARY KEY ,
	user_id INT NOT NULL ,
	order_date DATE NOT NULL ,
	total_amount DECIMAL(10) NOT NULL ,
	 CONSTRAINT fk_order_buyer
	 FOREIGN KEY(user_id) REFERENCES buyers(user_id)
	 ON DELETE CASCADE ON UPDATE CASCADE ,
	 check(total_amount >= 0)
	 );
##PAYMENT
create table payment(
	payment_id INT PRIMARY KEY ,
    order_id INT NOT NULL ,
    payment_date DATE NOT NULL ,
    payment_method VARCHAR(50) NOT NULL ,
    amount DECIMAL(10) NOT NULL ,
    payment_status ENUM('Canceled','Pending', 'Paid') DEFAULT 'Pending' ,
    CONSTRAINT fk_payment_order
    FOREIGN KEY(order_id) REFERENCES orders(order_id)
    ON DELETE RESTRICT ON UPDATE CASCADE ,
    CHECK(amount >=0)
    );
##CARTITEM 
create table cartItem(
	cartItem_id INT PRIMARY KEY ,
    user_id INT NOT NULL ,
    product_id INT NOT NULL ,
    quantity INT NOT NULL ,
    unit_price DECIMAL(10) NOT NULL ,
    subtotal DECIMAL(10) GENERATED ALWAYS AS(unit_price * quantity) STORED ,
    CONSTRAINT fk_cartItem_buyer
    FOREIGN KEY(user_id) REFERENCES buyers(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE ,
    CONSTRAINT fk_cartItem_products
    FOREIGN KEY(product_id) REFERENCES products(product_id)
    ON DELETE CASCADE ON UPDATE CASCADE ,
    check(quantity > 0),
    check(unit_price > 0)
    );
##APPLY
create table apply(
	voucher_id INT NOT NULL ,
    order_id INT NOT NULL,
    PRIMARY KEY(voucher_id, order_id) ,
    CONSTRAINT fk_apply_vouchers
    FOREIGN KEY(voucher_id) REFERENCES vouchers(voucher_id)
    ON DELETE RESTRICT ON UPDATE CASCADE ,
	CONSTRAINT fk_apply_order
    FOREIGN KEY(order_id) REFERENCES orders(order_id)
    ON DELETE RESTRICT ON UPDATE CASCADE 
    );
##HOLD
create table hold(
	order_id INT NOT NULL,
    cartItem_id INT PRIMARY KEY,
    CONSTRAINT fk_hold_order
    FOREIGN KEY(order_id) REFERENCES orders(order_id)
    ON DELETE RESTRICT ON UPDATE CASCADE ,
    CONSTRAINT fk_hold_cartItem
    FOREIGN KEY(cartItem_id) REFERENCES cartItem(cartItem_id)
    ON DELETE RESTRICT ON UPDATE CASCADE 
    );
##CONTAIN
create table contain(
	inventory_id INT NOT NULL ,
    product_id INT NOT NULL ,
    quantity_in_stock INT NOT NULL ,
    PRIMARY KEY(inventory_id, product_id) ,
    CONSTRAINT fk_contain_inventory
    FOREIGN KEY(inventory_id) REFERENCES inventory(inventory_id)
    ON DELETE RESTRICT ON UPDATE CASCADE ,
    CONSTRAINT fk_contain_products
    FOREIGN KEY(product_id) REFERENCES products(product_id)
    ON DELETE CASCADE ON UPDATE CASCADE ,
    CHECK(quantity_in_stock >=0)
    );
##SHIPMENT
create table shipment(
	tracking_number INT PRIMARY KEY ,
	order_id INT NOT NULL UNIQUE ,
    address VARCHAR(100) NOT NULL ,
    delivery_date DATE NOT NULL ,
    receive_date DATE ,
    status ENUM('Pending','Shipping','Delivered','Cancelled') DEFAULT 'Pending' ,
    CONSTRAINT fk_shipment_order
    FOREIGN KEY(order_id) REFERENCES orders(order_id)
    ON DELETE RESTRICT ON UPDATE CASCADE ,
    check(receive_date IS NULL OR receive_date >= delivery_date)
    );
##DELIVERY LOG
create table delivery_log(
	track_number INT,
    log VARCHAR(30),
    create_date DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_log_shipment
    FOREIGN KEY(track_number) REFERENCES shipment(tracking_number)
    ON DELETE CASCADE ON UPDATE CASCADE,
    PRIMARY KEY (track_number, log)
    );

-- ========== USERS ==========
INSERT INTO users (user_id, email, Phone_number, create_Date) VALUES
(1, 'anh.nguyen@example.com', '0901000001', '2025-10-01'),
(2, 'binh.tran@example.com', '0901000002', '2025-10-02'),
(3, 'chi.le@example.com', '0901000003', '2025-10-03'),
(4, 'seller.tech@shop.vn', '0902000001', '2025-09-20'),
(5, 'seller.style@shop.vn', '0902000002', '2025-09-22'),
(6, 'duy.pham@example.com', '0901000004', '2025-10-05'),
(7, 'ha.ngo@example.com', '0901000005', '2025-10-07'),
(8, 'khanh.do@example.com', '0901000006', '2025-10-08');

-- ========== BUYERS (phân hệ người mua) ==========
INSERT INTO buyers (user_id, payment_method, shipping_address, loyalty_points) VALUES
(1, 'Bank Transfer', '123 Nguyễn Trãi, Quận 5, TP.HCM', 120),
(2, 'Bank Transfer', '45 Trần Hưng Đạo, Quận 1, TP.HCM', 40),
(3, 'Bank Transfer', '12 Võ Văn Kiệt, Quận 1, TP.HCM', 0),
(4, 'Bank Transfer', '88 Lý Thường Kiệt, Quận 10, TP.HCM', 10),
(8, 'Bank Transfer', '25 Lê Lợi, TP. Thủ Đức, TP.HCM', 5);

-- ========== SELLERS (phân hệ người bán) ==========
INSERT INTO sellers (user_id, business_licenses, bank_code, bank_account) VALUES
(4, 'BL-1001', 'VCB', '123456789'),
(5, 'BL-1002', 'VNPTMONEY', '987654321'),
(6, 'BL-1003', 'TCB', '9301983783'),
(7, 'BL-1004', 'ACB', '2348125792'),
(8, 'BL-1005', 'TPB', '4131285825');

-- ========== STORE (mỗi seller 1 store) ==========
INSERT INTO store (store_id, user_id, store_name, store_rating) VALUES
(10, 4, 'TechNest Official', NULL),
(11, 5, 'MetroStyle Outlet', NULL),
(12, 6, 'GreenLeaf Home Goods', NULL),
(13, 7, 'UrbanRide Motor Parts', NULL),
(14, 8, 'SmartChoice Gadgets', NULL),
(15, 4, 'VietWear Fashion', NULL),
(16, 4, 'FreshMart Organics', NULL),
(17, 7, 'Lumière Cosmetics', NULL),
(18, 6, 'PowerTools Pro', NULL),
(19, 5, 'PetZone Supplies', NULL);
-- ========== INVENTORY ==========
INSERT INTO inventory (inventory_id, store_id) VALUES
(100, 10),
(101, 11),
(102, 12),
(103, 13),
(104, 14),
(105, 15),
(106, 16),
(107, 17),
(108, 18),
(109, 19);

-- ========== CATEGORY ==========
INSERT INTO category (category_id, category_name) VALUES
(1, 'Điện tử'),
(2, 'Thời trang'),
(3, 'Nhà cửa'),
(4, 'Ngoài trời'),
(5, 'Làm đẹp');

-- ========== PRODUCTS (giá VND nguyên) ==========
INSERT INTO products (product_id, category_id, product_name, product_description, price, image_link) VALUES
(1000, 1, 'Chuột không dây Logitech MX Master 2S', 'Chuột không dây Logitech MX Master 2S thông qua Bluetooth giúp dễ dàng kết nối với hệ điều hành Windows 8, 10 trở lên, Mac OS 10.13 +, iPad 13.1 trở lên và Linux. Sản phẩm sở hữu cảm biến Darkfield và độ phân giải tối đa lên đến 4000 DPI giúp làm việc mượt mà trên mọi bề mặt phẳng. Kích thước sản phẩm 126,0 mm x 85,7 mm x 48,4 mm và trọng lượng chỉ 145g. Nhờ đó, Logitech MX Master 2S không chỉ nhỏ gọn, nhẹ nhàng mà còn êm tay với thiết kế chuột công thái học.', 159000, 'https://cdn2.cellphones.com.vn/insecure/rs:fill:0:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/c/h/chuot-khong-day-logitech-mx-master-2s_3.png'),
(1001, 1, 'Bàn phím cơ không dây AULA F75 đen', 'Bàn phím cơ không dây Aula F75 Đen có 80 phím với chất liệu keycap nhựa PBT, dùng loại switch Grey Wood V3 Switch cho độ bền tới 60 triệu lần bấm. Mẫu bàn phím Aula này có đèn nền LED RGB 16.8 triệu màu với hiệu ứng âm thanh khi gõ phím Linear. Aula F75 có không dây 2.4Ghz, Bluetooth, USB Type-C và tương thích được với Win XP/Win 7/Win 8/Win 10/Android/iOS/MAC.', 799000, 'https://cdn2.cellphones.com.vn/insecure/rs:fill:0:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/b/a/ban-phim-co-khong-day-aula-f75-den_3_.png'),
(1002, 2, 'Áo thun nam cổ trònc', '100% cotton, unisex, cổ tròn , áo phông ngắn tay trơn basic chất vải su dày co dãn 4 chiều mềm mại, chống xù nhiều màu siêu đẹp', 125000, 'https://down-vn.img.susercontent.com/file/d89b3a0f19afd7ca880bf45138af6a53.webp'),
(1003, 3, 'Máy hút bụi công nghiệp đa năng khô và ướt Yili YLW-6263A loại 12 lít công suất 1200W', 'Máy hút bụi công nghiệp mi ni cầm tay gia đình, Hút bụi cực mạnh đa chức năng khô và ướt Yili YLW-6263A loại 12 lít công suất 1200W - thùng inox hút chân không, ô tô, gia đình, nhà xưởng, ngoài trời ', 1290000, 'https://down-vn.img.susercontent.com/file/sg-11134201-22120-2rrjogodbflv6e.webp'),
(1004, 4, 'Bình nước thể thao 1L', 'Bình nước thể thao đa năng dung tích 1L – GUB Team, sản phẩm từ thương hiệu phụ kiện xe đạp hàng đầu, là lựa chọn hoàn hảo cho mọi hoạt động thể thao. Chất liệu nhựa cao cấp không màu, không mùi đảm bảo an toàn cho sức khỏe khi sử dụng.', 95000, 'https://zongvietnam.com/wp-content/uploads/2023/03/binh-nuoc-the-thao-da-nang-dung-tich-1l-gub-team-5.jpg'),
(1005, 3, 'Đèn LED Bàn Học Chống Cận 5W RD-RL-01.V2', 'Đèn LED Bàn Học Chống Cận 5W RD-RL-01.V2 của Rạng Đông mang đến ánh sáng ổn định, bảo vệ thị lực hiệu quả và tiết kiệm điện năng. Thiết kế hiện đại, tiện ích với nhiều tính năng thông minh, phù hợp cho học sinh và người làm việc lâu trên bàn. Mua ngay tại Rạng Đông Store để bảo vệ sức khỏe đôi mắt!', 179000, 'https://static.rangdongstore.vn/product/den-ban/RD-RL-01.V2/RD-RL-27.V2-6.jpg'),
(1006, 5, 'Sữa Rửa Mặt CeraVe Cho Da Thường Đến Khô 473ml', 'Sữa Rửa Mặt Cerave Sạch Sâu là sản phẩm sữa rửa mặt đến từ thương hiệu mỹ phẩm Cerave của Mỹ, với sự kết hợp của ba Ceramides thiết yếu, Hyaluronic Acid sản phẩm giúp làm sạch và giữ ẩm cho làn da mà không ảnh hưởng đến hàng rào bảo vệ da mặt và cơ thể.', 320000, 'https://media.hcdn.vn/wysiwyg/MaiQuynh/sua-rua-mat-cerave-sach-sau-2.jpg');

-- ========== CONTAIN (tồn kho theo inventory) ==========
INSERT INTO contain (inventory_id, product_id, quantity_in_stock) VALUES
(100, 1000, 50),
(101, 1001, 30),
(102, 1002, 200),
(101, 1003, 15),
(101, 1004, 120),
(102, 1005, 60),
(102, 1006, 100);

-- ========== VOUCHERS (giảm giá VND nguyên) ==========
INSERT INTO vouchers (voucher_id, descriptions, discount_value, start_date, end_date, voucher_status, minimum_value, quantity) VALUES
(2000, 'CHAO10K', 10000, '2025-10-01', '2025-12-31', 'Active', 100000, 100),
(2001, 'STYLE50K', 50000, '2025-09-01', '2025-11-30', 'Active', 300000,  50),
(2002, 'VUIVE', 30000, '2025-10-10', '2025-11-15', 'Disabled', 100000,  20),
(2003, 'SINHNHAT', 100000, '2025-10-11', '2025-10-13', 'Active', 0, 50),
(2004, 'HANHPHUC', 50000, '2025-10-11', '2025-10-13', 'Active', 100000, 1000);

-- ========== CART ITEMS (subtotal là cột GENERATED) ==========
INSERT INTO cartItem (cartItem_id, user_id, product_id, quantity, unit_price) VALUES
(5000, 1, 1000, 2, 159000),
(5001, 1, 1001, 1, 799000),
(5002, 2, 1002, 3, 125000),
(5003, 8, 1003, 1, 1290000),
(5004, 3, 1004, 2, 95000),
(5005, 4, 1005, 1, 179000),
(5006, 3, 1006, 3, 320000),
(5007, 8, 1000, 1, 159000);

-- ========== ORDERS (total_amount = sau giảm giá) ==========
INSERT INTO orders (order_id, user_id, order_date, total_amount) VALUES
(3000, 1, '2025-10-20', 1117000),
(3001, 2, '2025-10-22',  375000),
(3002, 8, '2025-10-24', 1290000),
(3003, 3, '2025-10-25', 1150000),
(3004, 8, '2025-10-26', 159000);

-- ========== APPLY (nếu muốn lưu mapping voucher↔order song song) ==========
INSERT INTO apply (voucher_id, order_id) VALUES
(2000, 3000),
(2001, 3002);

-- ========== HOLD (liên kết cartItem vào từng đơn) ==========
INSERT INTO hold (order_id, cartItem_id) VALUES
(3000, 5000),
(3000, 5001),
(3001, 5002),
(3002, 5003),
(3003, 5004),
(3003, 5006),
(3004, 5007);

-- ========== PAYMENT (số tiền = total_amount) ==========
INSERT INTO payment (payment_id, order_id, payment_date, payment_method, amount, payment_status) VALUES
(4000, 3000, '2025-10-21', 'Bank transfer', 1107000, 'Paid'),
(4001, 3001, '2025-10-22', 'Bank transfer', 375000, 'Pending'),
(4002, 3002, '2025-10-25', 'Bank transfer', 1240000, 'Paid'),
(4003, 3003, '2025-10-26', 'Bank transfer', 1150000, 'Canceled'),
(4004, 3004, '2025-10-27', 'Bank transfer', 159000, 'Canceled');


-- ========== REVIEW (mỗi người mua chỉ review 1 lần/1 sản phẩm) ==========
INSERT INTO review (review_id, product_id, user_id, date, review_comment, score) VALUES
(6000, 1000, 1, '2025-10-21', 'Chuột dùng ổn, pin rất trâu.', 5),
(6001, 1002, 2, '2025-10-23', 'Áo mặc rất ngứa.', 1);

-- ========== REPORTS (người mua báo cáo sản phẩm) ==========
INSERT INTO reports (product_id, user_id, title, reason) VALUES
(1002, 2, 'Hàng giả', 'Hàng giả, mặc vào hỏng hết người, yêu cầu shop nghỉ bán'),
(1001, 1, 'Giao sai hàng', 'Đặt bàn phím nhưng giao tivi');

-- ========== SHIPMENT (mỗi đơn 1 vận đơn) ==========
INSERT INTO shipment (tracking_number, order_id, address, delivery_date, receive_date, status) VALUES
(7000, 3000, '123 Nguyễn Trãi, Quận 5, TP.HCM', '2025-10-25', '2025-10-31', 'Delivered'),
(7001, 3001, '45 Trần Hưng Đạo, Quận 1, TP.HCM', '2025-10-24', NULL, 'Pending'),
(7002, 3002, '25 Lê Lợi, TP. Thủ Đức, TP.HCM',   '2025-10-28', '2025-11-01', 'Delivered');

-- ========== DELIVERY LOG ==========
INSERT INTO delivery_log (track_number, log, create_date) VALUES
(7000, 'Đơn hàng đã được tạo', '2025-10-28'),
(7000, 'Đã lấy hàng', '2025-10-29'),
(7000, 'Đang trung chuyển', '2025-10-30'),
(7000, 'Đang giao hàng', '2025-10-31'),
(7000, 'Giao hàng thành công', '2025-10-31'),

(7001, 'Đơn hàng đã được tạo', '2025-10-29'),
(7001, 'Đã lấy hàng', '2025-10-30'),
(7001, 'Đang trung chuyển', '2025-10-31'),
(7001, 'Đến kho Binh Duong', '2025-11-01'),

(7002, 'Đơn hàng đã được tạo', '2025-10-30'),
(7002, 'Đã lấy hàng', '2025-10-30'),
(7002, 'Đến kho TP.HCM', '2025-10-31'),
(7002, 'Đang giao hàng', '2025-11-01'),
(7002, 'Giao hàng thành công', '2025-11-01');



