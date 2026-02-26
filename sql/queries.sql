-- ============================================================
-- Fetching Data — SQL Queries (MySQL 8.0+)
-- ============================================================

-- ---------------------------------------------------------------
-- Q1: All products in "fashion" category with attributes
--     (SQL fetches core data; pair with MongoDB query for attributes)
-- ---------------------------------------------------------------
SELECT p.product_id,
       p.product_name,
       p.base_price,
       p.stock_quantity,
       p.description
FROM   products p
JOIN   categories c ON p.category_id = c.category_id
WHERE  c.category_name = 'fashion';


-- ---------------------------------------------------------------
-- Q3: Items with low stock (< 5)
-- ---------------------------------------------------------------
SELECT p.product_id,
       p.product_name,
       c.category_name,
       p.stock_quantity
FROM   products p
JOIN   categories c ON p.category_id = c.category_id
WHERE  p.stock_quantity < 5
ORDER  BY p.stock_quantity ASC;


-- ---------------------------------------------------------------
-- Q4: Fashion products available in blue OR large size
--     (SQL provides product IDs; MongoDB filters by attribute)
-- ---------------------------------------------------------------
SELECT p.product_id,
       p.product_name,
       p.base_price
FROM   products p
JOIN   categories c ON p.category_id = c.category_id
WHERE  c.category_name = 'fashion';
-- Then filter in MongoDB: see mongodb/queries.js Q4


-- ---------------------------------------------------------------
-- Q7: Cart info — device type, item count, total amount
-- ---------------------------------------------------------------
SELECT c.cart_id,
       c.user_id,
       c.device_type,
       COUNT(ci.cart_item_id)                    AS item_count,
       SUM(ci.quantity * p.base_price)           AS total_amount,
       c.created_at,
       c.is_active
FROM   carts c
JOIN   cart_items ci ON c.cart_id = ci.cart_id
JOIN   products p    ON ci.product_id = p.product_id
GROUP  BY c.cart_id, c.user_id, c.device_type, c.created_at, c.is_active
ORDER  BY c.created_at DESC;


-- ---------------------------------------------------------------
-- Q8: All orders placed by Sarah with full details
-- ---------------------------------------------------------------
SELECT o.order_id,
       o.order_date,
       o.status            AS order_status,
       oi.product_name,
       oi.quantity,
       oi.unit_price,
       oi.subtotal,
       py.payment_method,
       py.payment_status,
       o.shipping_option,
       o.total_amount,
       o.tax_amount,
       o.shipping_fee,
       o.expected_delivery_date
FROM   orders o
JOIN   order_items oi ON o.order_id  = oi.order_id
JOIN   payments py    ON o.order_id  = py.order_id
JOIN   users u        ON o.user_id   = u.user_id
WHERE  u.username = 'sarah'
ORDER  BY o.order_date DESC, oi.order_item_id;


-- ---------------------------------------------------------------
-- Q9: All returned items with refund status
-- ---------------------------------------------------------------
SELECT r.return_id,
       r.return_date,
       r.status            AS return_status,
       ri.product_id,
       p.product_name,
       ri.quantity,
       ri.refund_amount,
       ri.restocking_fee,
       ri.refund_status,
       r.reason
FROM   returns r
JOIN   return_items ri ON r.return_id  = ri.return_id
JOIN   products p      ON ri.product_id = p.product_id
JOIN   users u         ON r.user_id    = u.user_id
WHERE  u.username = 'sarah'
ORDER  BY r.return_date DESC;


-- ---------------------------------------------------------------
-- Q10: Average days between purchases for Sarah
-- ---------------------------------------------------------------
WITH sarah_orders AS (
    SELECT o.order_date,
           LAG(o.order_date) OVER (ORDER BY o.order_date) AS prev_order_date
    FROM   orders o
    JOIN   users u ON o.user_id = u.user_id
    WHERE  u.username = 'sarah'
      AND  o.status != 'cancelled'
)
SELECT ROUND(AVG(DATEDIFF(order_date, prev_order_date)), 1)
           AS avg_days_between_purchases
FROM   sarah_orders
WHERE  prev_order_date IS NOT NULL;


-- ---------------------------------------------------------------
-- Q11: Percentage of carts NOT converted to orders (past 30 days)
-- ---------------------------------------------------------------
SELECT ROUND(
    100.0 * SUM(CASE WHEN converted_to_order = FALSE THEN 1 ELSE 0 END)
          / NULLIF(COUNT(*), 0),
    2
) AS cart_abandonment_pct
FROM carts
WHERE created_at >= NOW() - INTERVAL 30 DAY;


-- ---------------------------------------------------------------
-- Q13: For each user — days since last purchase & total order count
-- ---------------------------------------------------------------
SELECT u.user_id,
       u.username,
       COUNT(o.order_id)                              AS total_orders,
       DATEDIFF(NOW(), MAX(o.order_date))             AS days_since_last_purchase
FROM   users u
LEFT   JOIN orders o ON u.user_id = o.user_id AND o.status != 'cancelled'
GROUP  BY u.user_id, u.username
ORDER  BY days_since_last_purchase IS NULL, days_since_last_purchase ASC;
