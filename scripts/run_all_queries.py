#!/usr/bin/env python3
"""
E-Commerce Platform — Full Reproduction Script
================================================
Runs all 13 queries against MySQL and MongoDB, measures performance,
and prints a summary report.

Prerequisites:
  - Docker running with containers 'ecommerce_mysql' and 'ecommerce_mongo'
  - Data already imported (see scripts/setup_and_import.sh)

Usage:
  python3 scripts/run_all_queries.py
"""

import time
import subprocess
import sys

MYSQL_CMD = [
    "docker", "exec", "ecommerce_mysql",
    "mysql", "-uroot", "-proot123", "ecommerce", "--batch", "-e"
]
MONGO_CMD = [
    "docker", "exec", "ecommerce_mongo",
    "mongosh", "ecommerce", "--quiet", "--eval"
]

THRESHOLD_MS = 2000


# ========== Query Definitions ==========

SQL_QUERIES = {
    "Q1-SQL": {
        "label": "Q1: Fashion products — core data (MySQL)",
        "sql": """
            SELECT p.product_id, p.product_name, p.base_price, p.stock_quantity
            FROM products p JOIN categories c ON p.category_id = c.category_id
            WHERE c.category_name = 'fashion'
            LIMIT 10;
        """
    },
    "Q3": {
        "label": "Q3: Low stock items (< 5 units)",
        "sql": """
            SELECT p.product_id, p.product_name, c.category_name, p.stock_quantity
            FROM products p JOIN categories c ON p.category_id = c.category_id
            WHERE p.stock_quantity < 5
            ORDER BY p.stock_quantity ASC
            LIMIT 15;
        """
    },
    "Q7": {
        "label": "Q7: Cart info — device type, item count, total",
        "sql": """
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
        """
    },
    "Q8": {
        "label": "Q8: All orders placed by Sarah",
        "sql": """
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
        """
    },
    "Q9": {
        "label": "Q9: Returned items with refund status",
        "sql": """
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
        """
    },
    "Q10": {
        "label": "Q10: Avg days between purchases (Sarah)",
        "sql": """
            WITH sarah_orders AS (
                SELECT o.order_date,
                       LAG(o.order_date) OVER (ORDER BY o.order_date) AS prev_order_date
                FROM orders o
                JOIN users u ON o.user_id = u.user_id
                WHERE u.username = 'sarah' AND o.status != 'cancelled'
            )
            SELECT ROUND(AVG(DATEDIFF(order_date, prev_order_date)), 1)
                       AS avg_days_between_purchases
            FROM sarah_orders
            WHERE prev_order_date IS NOT NULL;
        """
    },
    "Q11": {
        "label": "Q11: Cart abandonment % (past 30 days)",
        "sql": """
            SELECT ROUND(
                100.0 * SUM(CASE WHEN converted_to_order = FALSE THEN 1 ELSE 0 END)
                      / NULLIF(COUNT(*), 0), 2
            ) AS cart_abandonment_pct,
            COUNT(*) AS total_carts,
            SUM(CASE WHEN converted_to_order = FALSE THEN 1 ELSE 0 END) AS abandoned
            FROM carts
            WHERE created_at >= NOW() - INTERVAL 30 DAY;
        """
    },
    "Q12": {
        "label": "Q12: Top 3 co-purchased with electronics (SQL)",
        "sql": """
            SELECT other_p.product_name, c2.category_name, COUNT(*) AS co_purchase_count
            FROM order_items oi1
            JOIN products p1 ON oi1.product_id = p1.product_id
            JOIN categories c1 ON p1.category_id = c1.category_id
            JOIN order_items oi2 ON oi1.order_id = oi2.order_id
                AND oi1.order_item_id != oi2.order_item_id
            JOIN products other_p ON oi2.product_id = other_p.product_id
            JOIN categories c2 ON other_p.category_id = c2.category_id
            WHERE c1.category_name = 'electronics'
              AND c2.category_name != 'electronics'
            GROUP BY other_p.product_id, other_p.product_name, c2.category_name
            ORDER BY co_purchase_count DESC
            LIMIT 3;
        """
    },
    "Q13": {
        "label": "Q13: Days since last purchase & total orders per user",
        "sql": """
            SELECT u.user_id, u.username,
                   COUNT(o.order_id) AS total_orders,
                   DATEDIFF(NOW(), MAX(o.order_date)) AS days_since_last_purchase
            FROM users u
            LEFT JOIN orders o ON u.user_id = o.user_id AND o.status != 'cancelled'
            GROUP BY u.user_id, u.username
            ORDER BY days_since_last_purchase IS NULL, days_since_last_purchase ASC
            LIMIT 15;
        """
    },
}

MONGO_QUERIES = {
    "Q1-Mongo": {
        "label": "Q1: Fashion product attributes (MongoDB)",
        "js": """
            let total = db.product_catalog.countDocuments({category:"fashion"});
            let r = db.product_catalog.find(
              {category: "fashion"},
              {product_id:1, "attributes.material":1, "attributes.style":1, variants:1, _id:0}
            ).limit(3).toArray();
            print("Total fashion products: " + total);
            printjson(r);
        """
    },
    "Q2": {
        "label": "Q2: Last 5 products viewed by Sarah (past 6 months)",
        "js": """
            let sixMonthsAgo = new Date();
            sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6);
            let r = db.user_events.aggregate([
              {$match: {user_id: 1, event_type: "page_view",
                        timestamp: {$gte: sixMonthsAgo.toISOString()}}},
              {$sort: {timestamp: -1}},
              {$group: {_id: "$data.product_id",
                        last_viewed: {$first: "$timestamp"},
                        category: {$first: "$data.category"}}},
              {$sort: {last_viewed: -1}},
              {$limit: 5},
              {$project: {product_id: "$_id", last_viewed: 1, category: 1, _id: 0}}
            ]).toArray();
            printjson(r);
        """
    },
    "Q4": {
        "label": "Q4: Fashion products — blue OR large size (MongoDB)",
        "js": """
            let total = db.product_catalog.countDocuments({
              category: "fashion",
              $or: [{"variants.color": {$in: ["blue","aqua-blue"]}},
                    {"variants.size": "L"}]
            });
            let r = db.product_catalog.find({
              category: "fashion",
              $or: [{"variants.color": {$in: ["blue","aqua-blue"]}},
                    {"variants.size": "L"}]
            }, {product_id:1, variants:1, _id:0}).limit(3).toArray();
            print("Total matching: " + total);
            printjson(r);
        """
    },
    "Q5": {
        "label": "Q5: Product page views ordered by popularity",
        "js": """
            let r = db.user_events.aggregate([
              {$match: {event_type: "page_view"}},
              {$group: {_id: "$data.product_id",
                        view_count: {$sum: 1},
                        unique_viewers: {$addToSet: "$user_id"}}},
              {$project: {product_id: "$_id", view_count: 1,
                          unique_viewers: {$size: "$unique_viewers"}, _id: 0}},
              {$sort: {view_count: -1}},
              {$limit: 10}
            ]).toArray();
            printjson(r);
        """
    },
    "Q6": {
        "label": "Q6: Search terms by frequency & time of day",
        "js": """
            let r = db.user_events.aggregate([
              {$match: {user_id: 1, event_type: "search"}},
              {$addFields: {
                hour: {$toInt: {$substr: ["$timestamp", 11, 2]}},
                time_of_day: {$switch: {
                  branches: [
                    {case: {$and: [{$gte: [{$toInt:{$substr:["$timestamp",11,2]}}, 6]},
                                   {$lt:  [{$toInt:{$substr:["$timestamp",11,2]}}, 12]}]},
                     then: "morning"},
                    {case: {$and: [{$gte: [{$toInt:{$substr:["$timestamp",11,2]}}, 12]},
                                   {$lt:  [{$toInt:{$substr:["$timestamp",11,2]}}, 18]}]},
                     then: "afternoon"},
                    {case: {$and: [{$gte: [{$toInt:{$substr:["$timestamp",11,2]}}, 18]},
                                   {$lt:  [{$toInt:{$substr:["$timestamp",11,2]}}, 22]}]},
                     then: "evening"}
                  ],
                  default: "night"
                }}
              }},
              {$group: {_id: {term: "$data.search_term", time: "$time_of_day"},
                        frequency: {$sum: 1},
                        last_searched: {$max: "$timestamp"}}},
              {$sort: {frequency: -1}},
              {$limit: 10},
              {$project: {search_term: "$_id.term", time_of_day: "$_id.time",
                          frequency: 1, last_searched: 1, _id: 0}}
            ]).toArray();
            printjson(r);
        """
    },
}


# ========== Runners ==========

def run_mysql_query(label, sql):
    start = time.perf_counter()
    result = subprocess.run(MYSQL_CMD + [sql], capture_output=True, text=True)
    elapsed_ms = (time.perf_counter() - start) * 1000
    output = result.stdout.strip()
    lines = output.split('\n') if output else []
    row_count = max(len(lines) - 1, 0)

    print(f"\n{'='*72}")
    print(f"  {label}")
    print(f"  Database: MySQL  |  Rows: {row_count}  |  Time: {elapsed_ms:.0f} ms")
    print(f"{'='*72}")
    for line in lines[:10]:
        print(f"  {line}")
    if len(lines) > 10:
        print(f"  ... ({row_count} total rows)")

    return {"label": label, "db": "MySQL", "rows": row_count, "ms": round(elapsed_ms, 1)}


def run_mongo_query(label, js):
    start = time.perf_counter()
    result = subprocess.run(MONGO_CMD + [js], capture_output=True, text=True)
    elapsed_ms = (time.perf_counter() - start) * 1000
    output = result.stdout.strip()

    print(f"\n{'='*72}")
    print(f"  {label}")
    print(f"  Database: MongoDB  |  Time: {elapsed_ms:.0f} ms")
    print(f"{'='*72}")
    lines = output.split('\n') if output else []
    for line in lines[:12]:
        print(f"  {line}")
    if len(lines) > 12:
        print(f"  ... (output truncated)")

    return {"label": label, "db": "MongoDB", "ms": round(elapsed_ms, 1)}


# ========== Main ==========

def check_containers():
    """Verify Docker containers are running."""
    for name in ["ecommerce_mysql", "ecommerce_mongo"]:
        r = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", name],
            capture_output=True, text=True
        )
        if r.stdout.strip() != "true":
            print(f"ERROR: Container '{name}' is not running.")
            print(f"  Start it with:  scripts/setup_and_import.sh")
            sys.exit(1)
    print("Docker containers verified: ecommerce_mysql, ecommerce_mongo")


def main():
    check_containers()

    print("\n" + "#" * 72)
    print("  E-COMMERCE DATABASE — RUNNING ALL 13 QUERIES")
    print("#" * 72)

    results = []

    query_order = [
        ("sql",   "Q1-SQL"),
        ("mongo", "Q1-Mongo"),
        ("mongo", "Q2"),
        ("sql",   "Q3"),
        ("mongo", "Q4"),
        ("mongo", "Q5"),
        ("mongo", "Q6"),
        ("sql",   "Q7"),
        ("sql",   "Q8"),
        ("sql",   "Q9"),
        ("sql",   "Q10"),
        ("sql",   "Q11"),
        ("sql",   "Q12"),
        ("sql",   "Q13"),
    ]

    for db_type, key in query_order:
        if db_type == "sql":
            q = SQL_QUERIES[key]
            results.append(run_mysql_query(q["label"], q["sql"]))
        else:
            q = MONGO_QUERIES[key]
            results.append(run_mongo_query(q["label"], q["js"]))

    # Performance summary
    print("\n\n" + "=" * 72)
    print("  PERFORMANCE SUMMARY")
    print("=" * 72)
    print(f"  {'#':<4} {'Query':<48} {'DB':<9} {'ms':>7}  {'Status'}")
    print("  " + "-" * 70)

    for i, r in enumerate(results, 1):
        status = "PASS" if r["ms"] < THRESHOLD_MS else "SLOW"
        short_label = r["label"].split(":")[0]
        desc = r["label"].split(":", 1)[1].strip() if ":" in r["label"] else r["label"]
        desc = desc[:44] + "..." if len(desc) > 47 else desc
        print(f"  {short_label:<4} {desc:<48} {r['db']:<9} {r['ms']:>6.0f}  {status}")

    slow = [r for r in results if r["ms"] >= THRESHOLD_MS]
    total = len(results)
    print(f"\n  {'='*70}")
    print(f"  Total: {total} queries  |  Passed: {total - len(slow)}  |  Slow: {len(slow)}")
    print(f"  Threshold: {THRESHOLD_MS} ms per query")
    if not slow:
        print(f"  Result: ALL QUERIES PASSED within the {THRESHOLD_MS}ms threshold.")
    else:
        print(f"\n  Slow queries that need optimization:")
        for s in slow:
            print(f"    - {s['label']}: {s['ms']}ms")
    print()


if __name__ == "__main__":
    main()
