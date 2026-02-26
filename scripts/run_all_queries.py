"""Run all 13 e-commerce queries and measure performance."""

import time
import subprocess
import json
from datetime import datetime, timedelta

MYSQL_CMD = ["docker", "exec", "ecommerce_mysql", "mysql", "-uroot", "-proot123", "ecommerce", "-e"]
MONGO_CMD = ["docker", "exec", "ecommerce_mongo", "mongosh", "ecommerce", "--quiet", "--eval"]


def run_mysql(label, sql):
    start = time.perf_counter()
    result = subprocess.run(MYSQL_CMD + [sql], capture_output=True, text=True)
    elapsed = (time.perf_counter() - start) * 1000
    output = result.stdout.strip()
    lines = output.split('\n') if output else []
    row_count = max(len(lines) - 1, 0)
    print(f"\n{'='*70}")
    print(f"  {label}  [{elapsed:.0f} ms, {row_count} rows]")
    print(f"{'='*70}")
    if lines:
        for line in lines[:12]:
            print(f"  {line}")
        if len(lines) > 12:
            print(f"  ... ({row_count} rows total)")
    if result.stderr and "Warning" not in result.stderr:
        print(f"  ERROR: {result.stderr.strip()}")
    return {"label": label, "rows": row_count, "ms": round(elapsed, 1)}


def run_mongo(label, js):
    start = time.perf_counter()
    result = subprocess.run(MONGO_CMD + [js], capture_output=True, text=True)
    elapsed = (time.perf_counter() - start) * 1000
    output = result.stdout.strip()
    print(f"\n{'='*70}")
    print(f"  {label}  [{elapsed:.0f} ms]")
    print(f"{'='*70}")
    lines = output.split('\n') if output else []
    for line in lines[:15]:
        print(f"  {line}")
    if len(lines) > 15:
        print(f"  ... (truncated)")
    if result.stderr:
        for line in result.stderr.strip().split('\n'):
            if 'Warning' not in line and 'DeprecationWarning' not in line:
                print(f"  STDERR: {line}")
    return {"label": label, "ms": round(elapsed, 1)}


def main():
    results = []
    print("\n" + "#"*70)
    print("  RUNNING ALL 13 QUERIES")
    print("#"*70)

    # Q1: Fashion products with attributes (MySQL + MongoDB)
    results.append(run_mysql("Q1-SQL: Fashion products (core data)", """
        SELECT p.product_id, p.product_name, p.base_price, p.stock_quantity
        FROM products p JOIN categories c ON p.category_id = c.category_id
        WHERE c.category_name = 'fashion'
        LIMIT 10;
    """))
    results.append(run_mongo("Q1-Mongo: Fashion product attributes", """
        let r = db.product_catalog.find(
          {category: "fashion"},
          {product_id:1, "attributes.material":1, "attributes.style":1, variants:1, _id:0}
        ).limit(5).toArray();
        print("Found: " + db.product_catalog.countDocuments({category:"fashion"}) + " fashion products");
        printjson(r.slice(0,3));
    """))

    # Q2: Last 5 products viewed by Sarah (past 6 months)
    results.append(run_mongo("Q2: Last 5 products viewed by Sarah", """
        let sixMonthsAgo = new Date();
        sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6);
        let r = db.user_events.aggregate([
          {$match: {user_id: 1, event_type: "page_view", timestamp: {$gte: sixMonthsAgo.toISOString()}}},
          {$sort: {timestamp: -1}},
          {$group: {_id: "$data.product_id", last_viewed: {$first: "$timestamp"}, category: {$first: "$data.category"}}},
          {$sort: {last_viewed: -1}},
          {$limit: 5},
          {$project: {product_id: "$_id", last_viewed: 1, category: 1, _id: 0}}
        ]).toArray();
        printjson(r);
    """))

    # Q3: Low stock items
    results.append(run_mysql("Q3: Low stock items (< 5 units)", """
        SELECT p.product_id, p.product_name, c.category_name, p.stock_quantity
        FROM products p JOIN categories c ON p.category_id = c.category_id
        WHERE p.stock_quantity < 5
        ORDER BY p.stock_quantity ASC
        LIMIT 15;
    """))

    # Q4: Fashion products blue OR large
    results.append(run_mongo("Q4: Fashion products — blue color OR large size", """
        let r = db.product_catalog.find({
          category: "fashion",
          $or: [
            {"variants.color": {$in: ["blue", "aqua-blue"]}},
            {"variants.size": "L"}
          ]
        }, {product_id:1, variants:1, _id:0}).limit(5).toArray();
        let total = db.product_catalog.countDocuments({
          category: "fashion",
          $or: [{"variants.color": {$in: ["blue","aqua-blue"]}}, {"variants.size": "L"}]
        });
        print("Total matching: " + total);
        printjson(r.slice(0,3));
    """))

    # Q5: Product page views by popularity
    results.append(run_mongo("Q5: Product page views ordered by popularity", """
        let r = db.user_events.aggregate([
          {$match: {event_type: "page_view"}},
          {$group: {_id: "$data.product_id", view_count: {$sum: 1}, unique_viewers: {$addToSet: "$user_id"}}},
          {$project: {product_id: "$_id", view_count: 1, unique_viewers: {$size: "$unique_viewers"}, _id: 0}},
          {$sort: {view_count: -1}},
          {$limit: 10}
        ]).toArray();
        printjson(r);
    """))

    # Q6: Search terms by frequency and time of day
    results.append(run_mongo("Q6: Search terms by frequency & time of day", """
        let r = db.user_events.aggregate([
          {$match: {user_id: 1, event_type: "search"}},
          {$group: {_id: "$data.search_term", frequency: {$sum: 1}, last_searched: {$max: "$timestamp"}}},
          {$sort: {frequency: -1}},
          {$limit: 10}
        ]).toArray();
        printjson(r);
    """))

    # Q7: Cart info
    results.append(run_mysql("Q7: Cart info (device, items, total)", """
        SELECT c.cart_id, c.user_id, c.device_type,
               COUNT(ci.cart_item_id) AS item_count,
               ROUND(SUM(ci.quantity * p.base_price), 2) AS total_amount,
               c.is_active
        FROM carts c
        JOIN cart_items ci ON c.cart_id = ci.cart_id
        JOIN products p ON ci.product_id = p.product_id
        GROUP BY c.cart_id, c.user_id, c.device_type, c.is_active
        ORDER BY total_amount DESC
        LIMIT 10;
    """))

    # Q8: Sarah's orders
    results.append(run_mysql("Q8: All orders by Sarah", """
        SELECT o.order_id, o.order_date, o.status AS order_status,
               oi.product_name, oi.quantity, oi.unit_price, oi.subtotal,
               py.payment_method, o.shipping_option, o.total_amount
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN payments py ON o.order_id = py.order_id
        JOIN users u ON o.user_id = u.user_id
        WHERE u.username = 'sarah'
        ORDER BY o.order_date DESC
        LIMIT 15;
    """))

    # Q9: Returned items
    results.append(run_mysql("Q9: Returned items with refund status", """
        SELECT r.return_id, r.return_date, r.status AS return_status,
               p.product_name, ri.quantity, ri.refund_amount,
               ri.restocking_fee, ri.refund_status, r.reason
        FROM returns r
        JOIN return_items ri ON r.return_id = ri.return_id
        JOIN products p ON ri.product_id = p.product_id
        JOIN users u ON r.user_id = u.user_id
        WHERE u.username = 'sarah'
        ORDER BY r.return_date DESC
        LIMIT 10;
    """))

    # Q10: Avg days between purchases
    results.append(run_mysql("Q10: Avg days between purchases (Sarah)", """
        WITH sarah_orders AS (
            SELECT o.order_date,
                   LAG(o.order_date) OVER (ORDER BY o.order_date) AS prev_order_date
            FROM orders o
            JOIN users u ON o.user_id = u.user_id
            WHERE u.username = 'sarah' AND o.status != 'cancelled'
        )
        SELECT ROUND(AVG(DATEDIFF(order_date, prev_order_date)), 1) AS avg_days_between_purchases
        FROM sarah_orders
        WHERE prev_order_date IS NOT NULL;
    """))

    # Q11: Cart abandonment rate
    results.append(run_mysql("Q11: Cart abandonment % (past 30 days)", """
        SELECT ROUND(
            100.0 * SUM(CASE WHEN converted_to_order = FALSE THEN 1 ELSE 0 END)
                  / NULLIF(COUNT(*), 0), 2
        ) AS cart_abandonment_pct,
        COUNT(*) AS total_carts,
        SUM(CASE WHEN converted_to_order = FALSE THEN 1 ELSE 0 END) AS abandoned
        FROM carts
        WHERE created_at >= NOW() - INTERVAL 30 DAY;
    """))

    # Q12: Top 3 co-purchased with headphones (SQL fallback since no Neo4j)
    results.append(run_mysql("Q12: Top 3 products purchased with headphones (SQL)", """
        SELECT other_oi.product_name, COUNT(*) AS co_purchase_count
        FROM order_items hp_oi
        JOIN order_items other_oi ON hp_oi.order_id = other_oi.order_id
            AND hp_oi.order_item_id != other_oi.order_item_id
        WHERE hp_oi.product_name LIKE '%Headphone%'
           OR hp_oi.product_id IN (
               SELECT product_id FROM products
               JOIN categories c ON products.category_id = c.category_id
               WHERE c.category_name = 'electronics'
               LIMIT 100
           )
        GROUP BY other_oi.product_name
        ORDER BY co_purchase_count DESC
        LIMIT 3;
    """))

    # Q13: Days since last purchase per user
    results.append(run_mysql("Q13: Days since last purchase & total orders", """
        SELECT u.user_id, u.username,
               COUNT(o.order_id) AS total_orders,
               DATEDIFF(NOW(), MAX(o.order_date)) AS days_since_last_purchase
        FROM users u
        LEFT JOIN orders o ON u.user_id = o.user_id AND o.status != 'cancelled'
        GROUP BY u.user_id, u.username
        ORDER BY days_since_last_purchase IS NULL, days_since_last_purchase ASC
        LIMIT 15;
    """))

    # Summary
    print("\n\n" + "="*70)
    print("  PERFORMANCE SUMMARY")
    print("="*70)
    print(f"  {'Query':<55} {'Time (ms)':>10}")
    print("  " + "-"*66)
    for r in results:
        status = "PASS" if r["ms"] < 2000 else "SLOW"
        rows_info = f" ({r['rows']} rows)" if 'rows' in r else ""
        print(f"  {r['label']:<55} {r['ms']:>8.0f} ms  {status}")
    
    slow = [r for r in results if r["ms"] >= 2000]
    print(f"\n  Total: {len(results)} queries | Passed: {len(results)-len(slow)} | Slow: {len(slow)}")
    if not slow:
        print("  All queries completed within the 2-second threshold!")


if __name__ == "__main__":
    main()
