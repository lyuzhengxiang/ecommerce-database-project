"""
E-Commerce Platform — Synthetic Data Generator
Generates realistic data for MySQL, MongoDB, and Neo4j.

Requirements:  pip install faker mysql-connector-python pymongo neo4j
"""

import random
import json
import csv
import os
from datetime import datetime, timedelta
from pathlib import Path

try:
    from faker import Faker
except ImportError:
    raise SystemExit("Install faker first:  pip install faker")

fake = Faker()
Faker.seed(42)
random.seed(42)

OUTPUT_DIR = Path(__file__).parent.parent / "generated_data"
OUTPUT_DIR.mkdir(exist_ok=True)

# ---------- configuration ----------
NUM_USERS = 1_000
NUM_CATEGORIES = 6
NUM_PRODUCTS = 5_000
NUM_ORDERS = 100_000
NUM_USER_EVENTS = 500_000
NUM_CARTS = 40_000
CART_ITEMS_PER_CART = (1, 6)
ORDER_ITEMS_PER_ORDER = (1, 5)

CATEGORIES = [
    {"category_id": 1, "category_name": "electronics", "parent_category_id": None, "description": "Electronic gadgets and accessories"},
    {"category_id": 2, "category_name": "fashion",     "parent_category_id": None, "description": "Clothing, shoes, and accessories"},
    {"category_id": 3, "category_name": "home_decor",  "parent_category_id": None, "description": "Home decoration items"},
    {"category_id": 4, "category_name": "books",       "parent_category_id": None, "description": "Books and publications"},
    {"category_id": 5, "category_name": "sports",      "parent_category_id": None, "description": "Sporting goods and equipment"},
    {"category_id": 6, "category_name": "toys",        "parent_category_id": None, "description": "Toys and games"},
]

DEVICE_TYPES = ["tablet", "laptop", "mobile", "desktop"]
SHIPPING_OPTIONS = ["standard", "mid_tier", "expedited", "overnight"]
PAYMENT_METHODS = ["credit_card", "debit_card", "bank_account", "paypal"]
ORDER_STATUSES = ["pending", "confirmed", "shipped", "delivered", "cancelled"]
RETURN_STATUSES = ["initiated", "label_printed", "shipped_back", "received", "refunded", "exchanged"]
EVENT_TYPES = ["page_view", "search", "click", "add_to_cart", "remove_from_cart"]
COLORS = ["black", "white", "blue", "red", "aqua-blue", "coral", "green", "grey", "pink", "terracotta"]
SIZES = ["XS", "S", "M", "L", "XL", "XXL"]

ELECTRONICS_ATTRS = {
    "battery_life": lambda: f"{random.randint(4,50)} hours",
    "connectivity": lambda: random.choice(["Bluetooth 5.0", "Bluetooth 5.2", "Wired", "USB-C", "Wi-Fi"]),
    "weight": lambda: f"{random.randint(50,800)}g",
    "noise_cancellation": lambda: random.choice([True, False]),
}
FASHION_ATTRS = {
    "material": lambda: random.choice(["cotton", "cotton blend", "polyester", "silk", "linen", "denim", "wool"]),
    "care_instructions": lambda: random.choice(["Machine wash cold", "Hand wash only", "Dry clean only"]),
    "style": lambda: random.choice(["casual", "formal", "summer dress", "sportswear", "streetwear"]),
    "pattern": lambda: random.choice(["solid", "striped", "floral", "checkered", "abstract"]),
}
HOME_DECOR_ATTRS = {
    "dimensions": lambda: {"height": f"{random.randint(10,60)}cm", "width": f"{random.randint(5,40)}cm"},
    "material": lambda: random.choice(["ceramic", "glass", "wood", "metal", "fabric"]),
    "weight": lambda: f"{round(random.uniform(0.2, 5.0), 1)}kg",
    "care_instructions": lambda: random.choice(["Hand wash only", "Wipe with damp cloth", "Do not submerge"]),
}
GENERIC_ATTRS = {
    "weight": lambda: f"{random.randint(100,2000)}g",
    "material": lambda: random.choice(["plastic", "metal", "wood", "composite"]),
}

SEARCH_TERMS = [
    "wireless headphones", "summer dress", "ceramic vase", "running shoes",
    "bluetooth speaker", "yoga mat", "coffee table", "laptop bag",
    "winter jacket", "led lights", "phone case", "water bottle",
    "backpack", "sunglasses", "desk lamp", "kitchen set",
    "gaming mouse", "smartwatch", "sneakers", "throw pillow"
]


def write_csv(filename, rows, fieldnames):
    path = OUTPUT_DIR / filename
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  wrote {len(rows):>9,} rows → {path.name}")


def write_json(filename, data):
    path = OUTPUT_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, default=str, indent=None)
    print(f"  wrote {len(data):>9,} docs → {path.name}")


# ======================== GENERATE ========================

def gen_users():
    users = []
    users.append({
        "user_id": 1, "username": "sarah", "email": "sarah@example.com",
        "password_hash": fake.sha256(), "first_name": "Sarah", "last_name": "Johnson",
        "phone": fake.phone_number(),
        "created_at": "2025-06-15 10:00:00", "updated_at": "2026-02-20 14:00:00"
    })
    for i in range(2, NUM_USERS + 1):
        created = fake.date_time_between(start_date="-2y", end_date="-30d")
        users.append({
            "user_id": i,
            "username": f"{fake.user_name()}_{i}",
            "email": f"user{i}@{fake.free_email_domain()}",
            "password_hash": fake.sha256(),
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "phone": fake.phone_number(),
            "created_at": str(created),
            "updated_at": str(created + timedelta(days=random.randint(0, 180))),
        })
    return users


def gen_addresses(users):
    addresses = []
    aid = 1
    for u in users:
        for addr_type in ["shipping", "billing"]:
            addresses.append({
                "address_id": aid,
                "user_id": u["user_id"],
                "address_type": addr_type,
                "street": fake.street_address(),
                "city": fake.city(),
                "state": fake.state_abbr(),
                "zip_code": fake.zipcode(),
                "country": "US",
                "is_default": addr_type == "shipping",
            })
            aid += 1
    return addresses


def gen_products():
    products = []
    for i in range(1, NUM_PRODUCTS + 1):
        cat_id = random.choice([c["category_id"] for c in CATEGORIES])
        products.append({
            "product_id": i,
            "category_id": cat_id,
            "product_name": f"{fake.word().capitalize()} {fake.word().capitalize()} {fake.bs().split()[0].capitalize()}",
            "description": fake.sentence(nb_words=12),
            "base_price": round(random.uniform(5.99, 499.99), 2),
            "stock_quantity": random.choices(
                population=[random.randint(0, 4), random.randint(5, 200)],
                weights=[0.1, 0.9]
            )[0],
            "created_at": str(fake.date_time_between(start_date="-1y", end_date="-7d")),
            "updated_at": str(fake.date_time_between(start_date="-7d", end_date="now")),
        })
    return products


def gen_product_catalog(products):
    """MongoDB product_catalog documents with flexible attributes."""
    cat_map = {c["category_id"]: c["category_name"] for c in CATEGORIES}
    catalog = []
    for p in products:
        cat_name = cat_map[p["category_id"]]
        if cat_name == "electronics":
            attrs = {k: v() for k, v in ELECTRONICS_ATTRS.items()}
            variants = [{"color": random.choice(COLORS), "sku": f"EL-{p['product_id']}-{j}"} for j in range(random.randint(1, 3))]
        elif cat_name == "fashion":
            attrs = {k: v() for k, v in FASHION_ATTRS.items()}
            variants = []
            for size in random.sample(SIZES, random.randint(2, 5)):
                for color in random.sample(COLORS, random.randint(1, 3)):
                    variants.append({"size": size, "color": color, "sku": f"FA-{p['product_id']}-{size}-{color[:3]}"})
        elif cat_name == "home_decor":
            attrs = {k: v() for k, v in HOME_DECOR_ATTRS.items()}
            variants = [{"color": random.choice(COLORS), "sku": f"HD-{p['product_id']}-{j}"} for j in range(random.randint(1, 3))]
        else:
            attrs = {k: v() for k, v in GENERIC_ATTRS.items()}
            variants = [{"sku": f"GN-{p['product_id']}-{j}"} for j in range(random.randint(1, 2))]

        catalog.append({
            "product_id": p["product_id"],
            "category": cat_name,
            "attributes": attrs,
            "variants": variants,
            "tags": [fake.word() for _ in range(random.randint(1, 4))],
        })
    return catalog


def gen_carts(users, products):
    carts, cart_items = [], []
    ci_id = 1
    for cart_id in range(1, NUM_CARTS + 1):
        user = random.choice(users)
        created = fake.date_time_between(start_date="-60d", end_date="now")
        converted = random.random() < 0.55
        carts.append({
            "cart_id": cart_id,
            "user_id": user["user_id"],
            "session_id": fake.uuid4(),
            "device_type": random.choice(DEVICE_TYPES),
            "created_at": str(created),
            "updated_at": str(created + timedelta(minutes=random.randint(1, 120))),
            "is_active": not converted,
            "converted_to_order": converted,
            "converted_at": str(created + timedelta(minutes=random.randint(5, 180))) if converted else "",
        })
        for _ in range(random.randint(*CART_ITEMS_PER_CART)):
            prod = random.choice(products)
            cart_items.append({
                "cart_item_id": ci_id,
                "cart_id": cart_id,
                "product_id": prod["product_id"],
                "quantity": random.randint(1, 3),
                "added_at": str(created + timedelta(minutes=random.randint(0, 30))),
            })
            ci_id += 1
    return carts, cart_items


def gen_orders(users, products, addresses):
    orders, order_items, payments = [], [], []
    oi_id, pay_id = 1, 1
    user_addr = {}
    for a in addresses:
        if a["address_type"] == "shipping":
            user_addr[a["user_id"]] = a["address_id"]

    for order_id in range(1, NUM_ORDERS + 1):
        user = random.choice(users)
        order_date = fake.date_time_between(start_date="-1y", end_date="now")
        status = random.choices(ORDER_STATUSES, weights=[5, 10, 15, 60, 10])[0]
        ship_opt = random.choice(SHIPPING_OPTIONS)
        ship_fee = {"standard": 5.99, "mid_tier": 9.99, "expedited": 14.99, "overnight": 24.99}[ship_opt]

        items_in_order = []
        for _ in range(random.randint(*ORDER_ITEMS_PER_ORDER)):
            prod = random.choice(products)
            qty = random.randint(1, 3)
            unit_price = prod["base_price"]
            items_in_order.append({
                "order_item_id": oi_id,
                "order_id": order_id,
                "product_id": prod["product_id"],
                "product_name": prod["product_name"],
                "unit_price": unit_price,
                "quantity": qty,
                "subtotal": round(unit_price * qty, 2),
            })
            oi_id += 1

        subtotal = sum(i["subtotal"] for i in items_in_order)
        tax = round(subtotal * 0.08, 2)
        total = round(subtotal + tax + ship_fee, 2)

        addr_id = user_addr.get(user["user_id"], 1)
        orders.append({
            "order_id": order_id,
            "user_id": user["user_id"],
            "order_date": str(order_date),
            "status": status,
            "total_amount": total,
            "tax_amount": tax,
            "shipping_fee": ship_fee,
            "shipping_option": ship_opt,
            "shipping_address_id": addr_id,
            "expected_shipping_date": str((order_date + timedelta(days=random.randint(1, 3))).date()),
            "expected_delivery_date": str((order_date + timedelta(days=random.randint(3, 10))).date()),
        })
        order_items.extend(items_in_order)

        pm = random.choice(PAYMENT_METHODS)
        payments.append({
            "payment_id": pay_id,
            "order_id": order_id,
            "payment_method": pm,
            "payment_status": "approved" if status != "cancelled" else "declined",
            "amount": total,
            "transaction_date": str(order_date),
            "card_last_four": str(random.randint(1000, 9999)) if "card" in pm else "",
            "billing_address_id": addr_id,
        })
        pay_id += 1

    return orders, order_items, payments


def gen_returns(orders, order_items_all):
    returns_list, return_items = [], []
    ri_id = 1
    delivered = [o for o in orders if o["status"] == "delivered"]
    sample_size = min(int(len(delivered) * 0.08), len(delivered))
    returned_orders = random.sample(delivered, sample_size)

    oi_by_order = {}
    for oi in order_items_all:
        oi_by_order.setdefault(oi["order_id"], []).append(oi)

    for ret_id, order in enumerate(returned_orders, 1):
        oi_for_order = oi_by_order.get(order["order_id"], [])
        if not oi_for_order:
            continue
        try:
            od = datetime.strptime(order["order_date"], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            od = datetime.strptime(order["order_date"][:19], "%Y-%m-%d %H:%M:%S")
        ret_date = od + timedelta(days=random.randint(1, 14))
        returns_list.append({
            "return_id": ret_id,
            "order_id": order["order_id"],
            "user_id": order["user_id"],
            "return_date": str(ret_date),
            "status": random.choice(RETURN_STATUSES),
            "reason": random.choice(["Wrong size", "Defective item", "Changed mind", "Item not as described", "Better price found"]),
        })
        items_to_return = random.sample(oi_for_order, random.randint(1, min(2, len(oi_for_order))))
        for oi in items_to_return:
            restocking = round(oi["subtotal"] * random.choice([0, 0, 0.1, 0.15]), 2)
            return_items.append({
                "return_item_id": ri_id,
                "return_id": ret_id,
                "order_item_id": oi["order_item_id"],
                "product_id": oi["product_id"],
                "quantity": oi["quantity"],
                "refund_amount": round(oi["subtotal"] - restocking, 2),
                "restocking_fee": restocking,
                "refund_status": random.choice(["pending", "processed", "completed"]),
            })
            ri_id += 1
    return returns_list, return_items


def gen_user_events(users, products):
    events = []
    for _ in range(NUM_USER_EVENTS):
        user = random.choice(users)
        event_type = random.choices(EVENT_TYPES, weights=[50, 15, 20, 10, 5])[0]
        ts = fake.date_time_between(start_date="-6m", end_date="now")
        prod = random.choice(products)

        data = {"product_id": prod["product_id"], "category": CATEGORIES[prod["category_id"] - 1]["category_name"]}

        if event_type == "page_view":
            data["time_spent_seconds"] = random.randint(3, 300)
            data["page_url"] = f"/products/{data['category']}/{prod['product_id']}"
        elif event_type == "search":
            data["search_term"] = random.choice(SEARCH_TERMS)
            data["results_count"] = random.randint(0, 100)
        elif event_type == "click":
            data["element"] = random.choice(["product_card", "image", "add_to_cart_btn", "detail_link"])

        events.append({
            "user_id": user["user_id"],
            "event_type": event_type,
            "timestamp": ts.isoformat(),
            "session_id": fake.uuid4(),
            "device_type": random.choice(DEVICE_TYPES),
            "data": data,
        })
    return events


def gen_neo4j_import(users, products, orders, order_items_all):
    """Generate Cypher statements for bulk Neo4j import."""
    lines = ["// Auto-generated Neo4j import\n"]
    cat_map = {c["category_id"]: c["category_name"] for c in CATEGORIES}

    for c in CATEGORIES:
        lines.append(f'MERGE (:Category {{name: "{c["category_name"]}"}});')
    lines.append("")

    for u in users[:200]:
        lines.append(f'MERGE (:User {{user_id: {u["user_id"]}, name: "{u["first_name"]}"}});')
    lines.append("")

    for p in products[:1000]:
        name_escaped = p["product_name"].replace('"', '\\"')
        lines.append(f'MERGE (:Product {{product_id: {p["product_id"]}, name: "{name_escaped}", price: {p["base_price"]}}});')
    lines.append("")

    for p in products[:1000]:
        cat_name = cat_map[p["category_id"]]
        lines.append(
            f'MATCH (p:Product {{product_id: {p["product_id"]}}}), (c:Category {{name: "{cat_name}"}}) '
            f'MERGE (p)-[:BELONGS_TO]->(c);'
        )
    lines.append("")

    order_user = {o["order_id"]: o["user_id"] for o in orders}
    purchase_pairs = {}
    for oi in order_items_all:
        uid = order_user.get(oi["order_id"])
        if uid is not None and uid <= 200 and oi["product_id"] <= 1000:
            pid = oi["product_id"]
            purchase_pairs[(uid, pid)] = purchase_pairs.get((uid, pid), 0) + 1

    for (uid, pid), cnt in list(purchase_pairs.items())[:5000]:
        lines.append(
            f'MATCH (u:User {{user_id: {uid}}}), (p:Product {{product_id: {pid}}}) '
            f'MERGE (u)-[:PURCHASED {{count: {cnt}}}]->(p);'
        )

    return "\n".join(lines)


# ======================== MAIN ========================

def main():
    print("Generating synthetic e-commerce data...\n")

    print("[1/8] Users")
    users = gen_users()
    write_csv("users.csv", users, users[0].keys())

    print("[2/8] Addresses")
    addresses = gen_addresses(users)
    write_csv("addresses.csv", addresses, addresses[0].keys())

    print("[3/8] Products (SQL)")
    products = gen_products()
    write_csv("products.csv", products, products[0].keys())
    write_csv("categories.csv", CATEGORIES, CATEGORIES[0].keys())

    print("[4/8] Product Catalog (MongoDB)")
    catalog = gen_product_catalog(products)
    write_json("product_catalog.json", catalog)

    print("[5/8] Carts")
    carts, cart_items = gen_carts(users, products)
    write_csv("carts.csv", carts, carts[0].keys())
    write_csv("cart_items.csv", cart_items, cart_items[0].keys())

    print("[6/8] Orders, Order Items, Payments")
    orders, order_items_all, payments = gen_orders(users, products, addresses)
    write_csv("orders.csv", orders, orders[0].keys())
    write_csv("order_items.csv", order_items_all, order_items_all[0].keys())
    write_csv("payments.csv", payments, payments[0].keys())

    print("[7/8] Returns")
    returns_list, return_items = gen_returns(orders, order_items_all)
    if returns_list:
        write_csv("returns.csv", returns_list, returns_list[0].keys())
    if return_items:
        write_csv("return_items.csv", return_items, return_items[0].keys())

    print("[8/8] User Events (MongoDB)")
    events = gen_user_events(users, products)
    write_json("user_events.json", events)

    print("\n[Neo4j] Generating Cypher import...")
    cypher = gen_neo4j_import(users, products, orders, order_items_all)
    cypher_path = OUTPUT_DIR / "neo4j_import.cypher"
    with open(cypher_path, "w") as f:
        f.write(cypher)
    print(f"  wrote → {cypher_path.name}")

    print("\n✓ Data generation complete!")
    print(f"  Output directory: {OUTPUT_DIR.resolve()}")
    print(f"  Users:        {len(users):>10,}")
    print(f"  Products:     {len(products):>10,}")
    print(f"  Orders:       {len(orders):>10,}")
    print(f"  Order Items:  {len(order_items_all):>10,}")
    print(f"  Carts:        {len(carts):>10,}")
    print(f"  Cart Items:   {len(cart_items):>10,}")
    print(f"  Returns:      {len(returns_list):>10,}")
    print(f"  User Events:  {len(events):>10,}")


if __name__ == "__main__":
    main()
