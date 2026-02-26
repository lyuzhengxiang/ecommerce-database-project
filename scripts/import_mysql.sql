SET GLOBAL local_infile = 1;
SET FOREIGN_KEY_CHECKS = 0;

LOAD DATA LOCAL INFILE '/tmp/data/users.csv'
INTO TABLE users FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 ROWS
(user_id, username, email, password_hash, first_name, last_name, phone, created_at, updated_at);

LOAD DATA LOCAL INFILE '/tmp/data/addresses.csv'
INTO TABLE addresses FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 ROWS
(address_id, user_id, address_type, street, city, state, zip_code, country, is_default);

LOAD DATA LOCAL INFILE '/tmp/data/categories.csv'
INTO TABLE categories FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 ROWS
(category_id, category_name, @parent, description)
SET parent_category_id = NULLIF(@parent, '');

LOAD DATA LOCAL INFILE '/tmp/data/products.csv'
INTO TABLE products FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 ROWS
(product_id, category_id, product_name, description, base_price, stock_quantity, created_at, updated_at);

LOAD DATA LOCAL INFILE '/tmp/data/carts.csv'
INTO TABLE carts FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 ROWS
(cart_id, user_id, session_id, device_type, created_at, updated_at, @active, @converted, @converted_at)
SET is_active = (@active = 'True'),
    converted_to_order = (@converted = 'True'),
    converted_at = NULLIF(@converted_at, '');

LOAD DATA LOCAL INFILE '/tmp/data/cart_items.csv'
INTO TABLE cart_items FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 ROWS
(cart_item_id, cart_id, product_id, quantity, added_at);

LOAD DATA LOCAL INFILE '/tmp/data/orders.csv'
INTO TABLE orders FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 ROWS
(order_id, user_id, order_date, status, total_amount, tax_amount, shipping_fee, shipping_option, shipping_address_id, expected_shipping_date, expected_delivery_date);

LOAD DATA LOCAL INFILE '/tmp/data/order_items.csv'
INTO TABLE order_items FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 ROWS
(order_item_id, order_id, product_id, product_name, unit_price, quantity, subtotal);

LOAD DATA LOCAL INFILE '/tmp/data/payments.csv'
INTO TABLE payments FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 ROWS
(payment_id, order_id, payment_method, payment_status, amount, transaction_date, @card, billing_address_id)
SET card_last_four = NULLIF(@card, '');

LOAD DATA LOCAL INFILE '/tmp/data/returns.csv'
INTO TABLE returns FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 ROWS
(return_id, order_id, user_id, return_date, status, reason);

LOAD DATA LOCAL INFILE '/tmp/data/return_items.csv'
INTO TABLE return_items FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 ROWS
(return_item_id, return_id, order_item_id, product_id, quantity, refund_amount, restocking_fee, refund_status);

SET FOREIGN_KEY_CHECKS = 1;

SELECT 'users' AS tbl, COUNT(*) AS cnt FROM users
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'orders', COUNT(*) FROM orders
UNION ALL SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL SELECT 'carts', COUNT(*) FROM carts
UNION ALL SELECT 'cart_items', COUNT(*) FROM cart_items
UNION ALL SELECT 'returns', COUNT(*) FROM returns
UNION ALL SELECT 'return_items', COUNT(*) FROM return_items
UNION ALL SELECT 'payments', COUNT(*) FROM payments;
