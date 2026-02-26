"""
E-Commerce Platform — Query Performance Evaluation
Runs all 13 queries against the databases and reports execution times.

Requirements:  pip install mysql-connector-python pymongo neo4j tabulate
"""

import time
import os
from datetime import datetime, timedelta

try:
    import mysql.connector
except ImportError:
    mysql = None

try:
    from pymongo import MongoClient
except ImportError:
    MongoClient = None

try:
    from neo4j import GraphDatabase
except ImportError:
    GraphDatabase = None

try:
    from tabulate import tabulate
except ImportError:
    tabulate = None

MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", 3306)),
    "database": os.getenv("MYSQL_DB", "ecommerce"),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASS", ""),
}

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = "ecommerce"

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS", "password")

THRESHOLD_MS = 2000


def timed(fn):
    """Run fn, return (result, elapsed_ms)."""
    start = time.perf_counter()
    result = fn()
    elapsed = (time.perf_counter() - start) * 1000
    return result, elapsed


# ========== MySQL Queries ==========

def mysql_queries(conn):
    results = {}

    def run_sql(label, sql):
        def _run():
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql)
            rows = cursor.fetchall()
            cursor.close()
            return rows
        rows, ms = timed(_run)
        results[label] = {"rows": len(rows), "ms": round(ms, 2)}

    run_sql("Q1-SQL: Fashion products", """
        SELECT p.product_id, p.product_name, p.base_price, p.stock_quantity
        FROM products p JOIN categories c ON p.category_id = c.category_id
        WHERE c.category_name = 'fashion'
    """)

    run_sql("Q3: Low stock items (<5)", """
        SELECT p.product_id, p.product_name, c.category_name, p.stock_quantity
        FROM products p JOIN categories c ON p.category_id = c.category_id
        WHERE p.stock_quantity < 5 ORDER BY p.stock_quantity ASC
    """)

    run_sql("Q7: Cart info", """
        SELECT c.cart_id, c.device_type, COUNT(ci.cart_item_id) AS item_count,
               SUM(ci.quantity * p.base_price) AS total_amount
        FROM carts c JOIN cart_items ci ON c.cart_id = ci.cart_id
        JOIN products p ON ci.product_id = p.product_id
        GROUP BY c.cart_id, c.device_type
    """)

    run_sql("Q8: Sarah's orders", """
        SELECT o.order_id, o.order_date, o.status, oi.product_name, oi.quantity,
               oi.unit_price, py.payment_method, o.shipping_option
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN payments py ON o.order_id = py.order_id
        JOIN users u ON o.user_id = u.user_id
        WHERE u.username = 'sarah'
        ORDER BY o.order_date DESC
    """)

    run_sql("Q9: Sarah's returns", """
        SELECT r.return_id, ri.product_id, p.product_name, ri.refund_amount,
               ri.restocking_fee, ri.refund_status
        FROM returns r
        JOIN return_items ri ON r.return_id = ri.return_id
        JOIN products p ON ri.product_id = p.product_id
        JOIN users u ON r.user_id = u.user_id
        WHERE u.username = 'sarah'
    """)

    run_sql("Q10: Avg days between purchases", """
        WITH sarah_orders AS (
            SELECT o.order_date,
                   LAG(o.order_date) OVER (ORDER BY o.order_date) AS prev
            FROM orders o JOIN users u ON o.user_id = u.user_id
            WHERE u.username = 'sarah' AND o.status != 'cancelled'
        )
        SELECT ROUND(AVG(DATEDIFF(order_date, prev)), 1) AS avg_days
        FROM sarah_orders WHERE prev IS NOT NULL
    """)

    run_sql("Q11: Cart abandonment %", """
        SELECT ROUND(
            100.0 * SUM(CASE WHEN converted_to_order = FALSE THEN 1 ELSE 0 END)
                  / NULLIF(COUNT(*), 0), 2
        ) AS pct
        FROM carts WHERE created_at >= NOW() - INTERVAL 30 DAY
    """)

    run_sql("Q13: Days since last purchase", """
        SELECT u.user_id, u.username, COUNT(o.order_id) AS total_orders,
               DATEDIFF(NOW(), MAX(o.order_date)) AS days_since
        FROM users u LEFT JOIN orders o ON u.user_id = o.user_id AND o.status != 'cancelled'
        GROUP BY u.user_id, u.username
        ORDER BY days_since IS NULL, days_since ASC
        LIMIT 20
    """)

    return results


# ========== MongoDB Queries ==========

def mongo_queries(db):
    results = {}

    def run_mongo(label, fn):
        data, ms = timed(fn)
        count = len(list(data)) if hasattr(data, '__iter__') else 0
        results[label] = {"rows": count, "ms": round(ms, 2)}

    run_mongo("Q1-Mongo: Fashion attrs", lambda: list(
        db.product_catalog.find({"category": "fashion"}, {"attributes": 1, "variants": 1, "product_id": 1})
    ))

    six_months_ago = datetime.utcnow() - timedelta(days=180)
    run_mongo("Q2: Last 5 viewed by Sarah", lambda: list(
        db.user_events.aggregate([
            {"$match": {"user_id": 1, "event_type": "page_view", "timestamp": {"$gte": six_months_ago.isoformat()}}},
            {"$sort": {"timestamp": -1}},
            {"$group": {"_id": "$data.product_id", "last_viewed": {"$first": "$timestamp"}}},
            {"$sort": {"last_viewed": -1}},
            {"$limit": 5}
        ])
    ))

    run_mongo("Q4-Mongo: Blue/Large fashion", lambda: list(
        db.product_catalog.find({
            "category": "fashion",
            "$or": [{"variants.color": "blue"}, {"variants.color": "aqua-blue"}, {"variants.size": "L"}]
        })
    ))

    run_mongo("Q5: Page views by popularity", lambda: list(
        db.user_events.aggregate([
            {"$match": {"event_type": "page_view"}},
            {"$group": {"_id": "$data.product_id", "views": {"$sum": 1}}},
            {"$sort": {"views": -1}},
            {"$limit": 20}
        ])
    ))

    run_mongo("Q6: Search terms frequency", lambda: list(
        db.user_events.aggregate([
            {"$match": {"user_id": 1, "event_type": "search"}},
            {"$group": {"_id": "$data.search_term", "freq": {"$sum": 1}}},
            {"$sort": {"freq": -1}}
        ])
    ))

    return results


# ========== Neo4j Queries ==========

def neo4j_queries(driver):
    results = {}

    def run_cypher(label, query):
        def _run():
            with driver.session() as session:
                return list(session.run(query))
        data, ms = timed(_run)
        results[label] = {"rows": len(data), "ms": round(ms, 2)}

    run_cypher("Q12: Top 3 co-purchased with headphones", """
        MATCH (hp:Product)-[:BELONGS_TO]->(:Category {name: "electronics"})
        WHERE hp.name CONTAINS "Headphone"
        MATCH (buyer:User)-[:PURCHASED]->(hp)
        MATCH (buyer)-[:PURCHASED]->(other:Product)
        WHERE other <> hp
        RETURN other.product_id AS pid, other.name AS name, COUNT(buyer) AS cnt
        ORDER BY cnt DESC LIMIT 3
    """)

    return results


# ========== Report ==========

def print_report(all_results):
    print("\n" + "=" * 70)
    print("  QUERY PERFORMANCE REPORT")
    print("=" * 70)

    rows = []
    for label, info in all_results.items():
        status = "PASS" if info["ms"] <= THRESHOLD_MS else "SLOW"
        rows.append([label, info["rows"], f'{info["ms"]:.1f}', status])

    if tabulate:
        print(tabulate(rows, headers=["Query", "Rows", "Time (ms)", "Status"], tablefmt="grid"))
    else:
        print(f"{'Query':<45} {'Rows':>6} {'ms':>10} {'Status':>6}")
        print("-" * 70)
        for r in rows:
            print(f"{r[0]:<45} {r[1]:>6} {r[2]:>10} {r[3]:>6}")

    slow = [r for r in rows if r[3] == "SLOW"]
    print(f"\nTotal queries: {len(rows)}  |  Passed: {len(rows)-len(slow)}  |  Slow: {len(slow)}")
    if slow:
        print("\nOptimization suggestions for slow queries:")
        for s in slow:
            print(f"  - {s[0]}: Consider adding indexes or reducing scan scope")


def main():
    all_results = {}

    try:
        import mysql.connector as mc
        conn = mc.connect(**MYSQL_CONFIG)
        print("Connected to MySQL")
        all_results.update(mysql_queries(conn))
        conn.close()
    except Exception as e:
        print(f"MySQL skipped: {e}")

    if MongoClient:
        try:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
            client.server_info()
            db = client[MONGO_DB]
            print("Connected to MongoDB")
            all_results.update(mongo_queries(db))
            client.close()
        except Exception as e:
            print(f"MongoDB skipped: {e}")

    if GraphDatabase:
        try:
            driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
            driver.verify_connectivity()
            print("Connected to Neo4j")
            all_results.update(neo4j_queries(driver))
            driver.close()
        except Exception as e:
            print(f"Neo4j skipped: {e}")

    if all_results:
        print_report(all_results)
    else:
        print("\nNo databases available. Performance evaluation requires running databases.")
        print("To test, start MySQL, MongoDB, and/or Neo4j, then re-run this script.")
        print("\nExpected performance (based on schema design & indexing):")
        print("  All 13 queries should complete within 2 seconds on <=100K records.")
        print("  Key indexes are defined in sql/schema.sql and mongodb/schema.js.")


if __name__ == "__main__":
    main()
