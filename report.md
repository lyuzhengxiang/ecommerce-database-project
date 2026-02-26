# E-Commerce Database Architecture Project Report

---

## Table of Contents

1. [Database Design](#1-database-design)
   1. [Functionality–Database Type Mapping](#11-functionality-database-type-mapping)
   2. [Entity-Relationship Diagram (ERD)](#12-entity-relationship-diagram)
   3. [Handling Diverse Product Attributes](#13-handling-diverse-product-attributes)
   4. [Session Management Across Devices](#14-session-management-across-devices)
   5. [Denormalization Strategy](#15-denormalization-strategy)
   6. [Data Flow Diagram](#16-data-flow-diagram)
   7. [Challenges and Mitigations](#17-challenges-and-mitigations)
   8. [In-Memory Storage (Redis)](#18-in-memory-storage-redis)
   9. [User Behavior Data Architecture](#19-user-behavior-data-architecture)
   10. [Graph Database Model](#110-graph-database-model)
2. [Fetching Data — Queries](#2-fetching-data)
3. [Data Generation & Performance Evaluation](#3-data-generation--performance-evaluation)
4. [Revision Log](#4-revision-log)
5. [Team Contributions](#5-team-contributions)

---

## 1. Database Design

### 1.1 Functionality–Database Type Mapping

Based on the e-commerce narrative, we map each functionality to the most appropriate database type:

| # | Functionality | Database | Type | Rationale |
|---|---------------|----------|------|-----------|
| 1 | **User accounts & profiles** | MySQL | Relational | Structured data with strict consistency requirements (login credentials, personal info). ACID transactions ensure data integrity for registration and updates. |
| 2 | **Product catalog (core)** | MySQL | Relational | Products have a core set of shared fields (name, price, stock) that benefit from relational integrity and JOINs with categories and orders. |
| 3 | **Product attributes (category-specific)** | MongoDB | Document | Headphones, dresses, and vases each have entirely different attribute sets. A document store allows schema-free, nested attributes without altering table structures. |
| 4 | **Shopping cart (active session)** | Redis | In-Memory | Carts are accessed at high frequency with low-latency requirements. Redis key-value storage enables sub-millisecond reads and automatic expiration for abandoned carts. |
| 5 | **Session management (cross-device)** | Redis + MongoDB | Hybrid | Redis holds the active session for instant lookup on login; MongoDB persists session history and device trail for durability beyond TTL. |
| 6 | **Orders & payments** | MySQL | Relational | Financial transactions demand ACID compliance. Orders involve multi-table writes (order → order_items → payment) that must succeed or fail atomically. |
| 7 | **Returns & refunds** | MySQL | Relational | Returns reference orders and products through foreign keys. Refund amounts and restocking fees require consistent computation. |
| 8 | **Real-time inventory** | Redis + MySQL | Hybrid | Redis maintains a live counter (DECR/INCR) for the real-time stock display. MySQL is the source of truth, periodically synchronized. |
| 9 | **User behavior tracking** | MongoDB | Document | Behavioral events (views, searches, clicks, time-on-page) are semi-structured, high-volume, write-heavy. MongoDB handles append-heavy workloads efficiently and supports flexible event schemas. |
| 10 | **Product recommendations / "bought together"** | Neo4j | Graph | Finding products frequently purchased together requires multi-hop traversals. Graph databases execute these traversals in O(relationships) rather than O(n²) JOINs. |

---

### 1.2 Entity-Relationship Diagram

The relational portion of our design uses MySQL (InnoDB engine). Full DDL is in `sql/schema.sql`.

#### Tables and Key Fields

```
users
├── user_id (PK)
├── username (UNIQUE)
├── email (UNIQUE)
├── password_hash
├── first_name, last_name, phone
└── created_at, updated_at

addresses
├── address_id (PK)
├── user_id (FK → users)
├── address_type (shipping | billing)
├── street, city, state, zip_code, country
└── is_default

categories
├── category_id (PK)
├── category_name (UNIQUE)
├── parent_category_id (FK → categories, self-ref)
└── description

products
├── product_id (PK)
├── category_id (FK → categories)
├── product_name
├── description
├── base_price
├── stock_quantity
└── created_at, updated_at

product_images
├── image_id (PK)
├── product_id (FK → products)
├── image_url
└── is_primary

carts
├── cart_id (PK)
├── user_id (FK → users)
├── session_id
├── device_type
├── is_active, converted_to_order
└── created_at, updated_at

cart_items
├── cart_item_id (PK)
├── cart_id (FK → carts)
├── product_id (FK → products)
├── quantity
└── added_at

orders
├── order_id (PK)
├── user_id (FK → users)
├── order_date
├── status
├── total_amount, tax_amount, shipping_fee   ← denormalized
├── shipping_option
├── shipping_address_id (FK → addresses)
└── expected_shipping_date, expected_delivery_date

order_items
├── order_item_id (PK)
├── order_id (FK → orders)
├── product_id (FK → products)
├── product_name   ← denormalized snapshot
├── unit_price     ← denormalized snapshot
├── quantity
└── subtotal

payments
├── payment_id (PK)
├── order_id (FK → orders)
├── payment_method
├── payment_status
├── amount
├── transaction_date
├── card_last_four
└── billing_address_id (FK → addresses)

returns
├── return_id (PK)
├── order_id (FK → orders)
├── user_id (FK → users)
├── return_date, status, reason

return_items
├── return_item_id (PK)
├── return_id (FK → returns)
├── order_item_id (FK → order_items)
├── product_id (FK → products)
├── quantity
├── refund_amount, restocking_fee
└── refund_status
```

#### Relationships

| Parent | Child | Relationship | Cardinality |
|--------|-------|-------------|-------------|
| users | addresses | has | 1:N |
| users | carts | creates | 1:N |
| users | orders | places | 1:N |
| users | returns | initiates | 1:N |
| categories | products | contains | 1:N |
| categories | categories | parent-child (self-ref) | 1:N |
| products | cart_items | added to | 1:N |
| products | order_items | included in | 1:N |
| products | product_images | has | 1:N |
| carts | cart_items | contains | 1:N |
| orders | order_items | contains | 1:N |
| orders | payments | paid by | 1:1 |
| orders | returns | may have | 1:N |
| returns | return_items | contains | 1:N |
| addresses | orders | ships to | 1:N |

---

### 1.3 Handling Diverse Product Attributes

The narrative features three distinct product categories with entirely different attributes:

- **Electronics (headphones):** battery life, connectivity type, weight, noise cancellation
- **Fashion (dress):** size, material, color, care instructions, style
- **Home Décor (vase):** dimensions (H×W×D), ceramic type, weight, care instructions

**Our Approach: Hybrid — SQL Core + MongoDB Document Attributes**

The **core product data** (name, price, stock, category) lives in MySQL for relational integrity and transactional operations. The **category-specific attributes** live in MongoDB's `product_catalog` collection, where each document links to the SQL `product_id` but stores a free-form `attributes` object.

This avoids the downsides of:
- **Wide table approach:** Adding columns for every possible attribute would create sparse rows with hundreds of NULLs.
- **EAV (Entity-Attribute-Value):** While flexible, EAV requires expensive pivoting on every read and loses type safety.

MongoDB lets us store deeply nested and varying attributes natively. Adding a new product category (e.g., "groceries" with attributes like expiration_date, organic_certification) requires zero schema migration.

---

### 1.4 Session Management Across Devices

Sarah starts shopping on her tablet, abandons the session, then returns hours later on her laptop with her cart intact. Our design handles this through a **Redis + MongoDB hybrid**:

**Redis (active session layer):**
```
Key:    session:user:{user_id}
Value:  {
          "session_id": "sess_abc123",
          "device": "laptop",
          "cart": { "items": [...], "total": 129.98 },
          "recently_viewed": [101, 201, 301],
          "last_active": "2026-02-20T16:00:00Z"
        }
TTL:    24 hours (sliding)
```

**Flow:**
1. Sarah logs in on tablet → Redis creates `session:user:1` with cart data.
2. She adds headphones → Redis cart updated in-place (sub-millisecond).
3. She leaves (no logout) → session persists in Redis with 24h TTL.
4. She logs in on laptop → backend reads `session:user:1` from Redis, restores full cart state. Device field updated to "laptop."
5. On periodic intervals (every 5 minutes) or on significant actions (add to cart, checkout), the session snapshot is persisted to MongoDB `sessions` collection for durability.

**Why not just a MySQL sessions table?** Sessions are ephemeral, high-frequency read/write data. A MySQL table would add unnecessary disk I/O and locking overhead for data that changes every few seconds.

---

### 1.5 Denormalization Strategy

**Denormalized Component: `order_items` Table**

We denormalize by storing `product_name` and `unit_price` directly in the MySQL `order_items` table as snapshots at the time of purchase, rather than always JOINing to the `products` table.

**Rationale:**
- Product names and prices can change after an order is placed (price updates, renamed products, discontinued items).
- Order history must reflect the actual purchase conditions.
- Order detail queries (Q8) are extremely common and read-heavy.

**Trade-off Analysis:**

| Dimension | Impact |
|-----------|--------|
| **Read performance** | Significantly improved. The most common query (order history) avoids a JOIN to products, reducing I/O and query time. |
| **Write performance** | Slightly increased cost at order creation time — we must copy product_name and unit_price into each order_item row. This is acceptable since orders are created far less frequently than they are read. |
| **Consistency** | The snapshot is intentionally inconsistent with current product data. This is the desired behavior: if a product's price changes from $79.99 to $89.99, Sarah's past order must still show $79.99. |
| **Storage** | Marginal increase. Storing a VARCHAR(255) product_name and DECIMAL unit_price per order_item adds ~260 bytes/row. For 100K orders × 3 items avg = ~75 MB — negligible. |

We also denormalize `total_amount`, `tax_amount`, and `shipping_fee` in the `orders` table rather than computing them on every read.

---

### 1.6 Data Flow Diagram

```
┌──────────────┐          ┌──────────────┐
│   Client     │◄────────►│   API Layer  │
│ (Tablet/     │          │  (Backend)   │
│  Laptop)     │          └──────┬───────┘
└──────────────┘                 │
                    ┌────────────┼────────────┐
                    │            │            │
               ┌────▼────┐ ┌────▼────┐ ┌────▼────┐
               │  Redis   │ │  MySQL  │ │ MongoDB │
               │ (Cache)  │ │ (OLTP)  │ │ (Docs)  │
               └────┬─────┘ └────┬────┘ └────┬────┘
                    │            │            │
                    │     ┌──────▼──────┐     │
                    └────►│  Sync Jobs  │◄────┘
                          │ (scheduled) │
                          └──────┬──────┘
                                 │
                          ┌──────▼──────┐
                          │   Neo4j     │
                          │  (Graph)    │
                          └─────────────┘
```

**Data Flows:**

| Flow | Direction | Freshness | Mechanism |
|------|-----------|-----------|-----------|
| User login / session restore | Redis → API | Real-time | Direct read on every request |
| Add to cart | API → Redis → MySQL | Redis: instant; MySQL: eventual (5 min batch) | Write-through to Redis; async persist to MySQL |
| Place order | API → MySQL | Real-time (transactional) | Synchronous multi-table INSERT in a single transaction |
| Inventory update | MySQL → Redis | Near real-time (< 1 sec) | After order commit, publish event; Redis DECR |
| Product attributes | API → MongoDB | Real-time | Direct read from product_catalog collection |
| User behavior event | API → MongoDB | Real-time append | Fire-and-forget insert (eventual consistency acceptable) |
| Co-purchase graph update | MySQL → Neo4j | Batch (hourly) | Scheduled job reads new orders, updates FREQUENTLY_BOUGHT_WITH edges |

**Failure Fallbacks:**
- **Redis down:** Fall back to MongoDB sessions collection or MySQL carts table. Slower but functional.
- **MongoDB down:** Product attributes served from a local cache or degraded view (core data from MySQL only). Behavior events queued in-memory and flushed on recovery.
- **Neo4j down:** Recommendation queries fall back to a SQL-based co-purchase query (slower but correct). The rest of the platform is unaffected.

---

### 1.7 Challenges and Mitigations

| Challenge | Impact | Mitigation |
|-----------|--------|------------|
| **Data consistency across stores** | Product data exists in MySQL, MongoDB, and Redis simultaneously. Updates to one may not immediately reflect in others. | Use an event-driven architecture: MySQL writes trigger events that update MongoDB and Redis. Implement idempotent consumers and retry logic. Accept eventual consistency for non-critical data (attributes, views). |
| **Cache invalidation (Redis)** | Stale inventory counts could allow overselling. | Use Redis WATCH + MULTI for atomic decrements. Set short TTLs (5 min) on inventory keys. On cache miss, read from MySQL and repopulate. |
| **Schema drift in MongoDB** | Without enforced schemas, documents can become inconsistent over time. | Apply JSON Schema validation on collections (see `mongodb/schema.js`). Use application-level validators on write paths. |
| **Neo4j sync lag** | The co-purchase graph updates hourly, so recent purchases aren't reflected in recommendations immediately. | Acceptable for recommendations. For time-sensitive use cases, supplement with a real-time "users also bought" query against MySQL. |
| **Single point of failure** | If MySQL goes down, orders and payments halt. | Deploy MySQL with replication (primary + read replica). Use connection pooling (ProxySQL). Configure automated failover. |
| **High-volume event ingestion** | 500K+ behavioral events can strain MongoDB write throughput. | Use MongoDB's bulk write API. Partition events by month (time-based collections or TTL indexes). Consider a message queue (Kafka/RabbitMQ) as a buffer. |

---

### 1.8 In-Memory Storage (Redis)

#### What Data Benefits from Redis

| Data | Redis Key Pattern | TTL | Rationale |
|------|------------------|-----|-----------|
| Active session / cart | `session:user:{id}` | 24h (sliding) | Sub-millisecond restore on device switch |
| Real-time inventory | `inventory:{product_id}` | 5 min | Stock counter shown on product page must be instant |
| Recently viewed products | `recent_views:{user_id}` | 7 days | "Recently viewed" section loads instantly using a Redis sorted set (ZSET) |
| Product page view counts | `page_views:{product_id}` | None (persistent) | Incremented on every page view via INCR; avoids MongoDB write per view |
| Hot product cache | `product:{product_id}` | 10 min | Frequently accessed products cached as JSON to avoid repeated PG queries |

#### Consistency & Synchronization Strategy

1. **Write-through (cart):** Every cart mutation writes to Redis first (fast response to user), then asynchronously persists to MySQL `carts` / `cart_items` tables.

2. **Write-behind (page views):** Redis INCR accumulates view counts. A scheduled job (every 5 minutes) flushes aggregated counts to MongoDB `user_events` for permanent storage.

3. **Cache-aside (product data):** Application checks Redis first. On cache miss, reads from MySQL/MongoDB, writes result to Redis with TTL. On product update in MySQL, the cache key is explicitly invalidated.

4. **Inventory sync:** On order placement, MySQL decrements `stock_quantity` within the transaction. A post-commit hook sends a message to decrement `inventory:{product_id}` in Redis. If Redis is unavailable, the next cache miss will read the correct value from MySQL.

---

### 1.9 User Behavior Data Architecture

User interactions captured include:
- **Page views:** Which products a user looked at and for how long
- **Searches:** Search terms, result counts, clicked results
- **Clicks:** Which UI elements were clicked (product cards, images, buttons)
- **Cart actions:** Items added/removed from cart

**Storage: MongoDB `user_events` Collection**

```json
{
  "user_id": 1,
  "event_type": "page_view",
  "timestamp": "2026-02-20T14:30:00Z",
  "session_id": "sess_abc123",
  "device_type": "tablet",
  "data": {
    "product_id": 101,
    "category": "electronics",
    "time_spent_seconds": 45,
    "page_url": "/products/headphones/101"
  }
}
```

**Why MongoDB?**
1. **Schema flexibility:** Each event type has different `data` fields. Page views include time_spent; searches include search_term. Document storage handles this naturally.
2. **High write throughput:** Behavioral events are fire-and-forget inserts. MongoDB's append-optimized storage engine handles hundreds of thousands of writes per second.
3. **Rich aggregation:** MongoDB's aggregation pipeline supports the analytics queries we need (Q5: page views by popularity, Q6: search term frequency by time-of-day).
4. **TTL support:** Events older than one year auto-expire via TTL index, keeping storage manageable.

**Why not MySQL for events?** MySQL's rigid schema requires `ALTER TABLE` for every new event field. With semi-structured behavioral data that evolves frequently, MongoDB handles schema variability natively.

**Indexes for Performance:**
- `{ user_id: 1, timestamp: -1 }` — efficient per-user event retrieval
- `{ event_type: 1 }` — fast filtering by event type
- `{ "data.product_id": 1 }` — product-level analytics
- `{ timestamp: 1, expireAfterSeconds }` — automatic data lifecycle management

**Scale Considerations:**
At 500K events, a single MongoDB replica set handles the load easily. At production scale (millions/day), we would:
- Shard the collection on `{ user_id: 1, timestamp: 1 }` for horizontal scaling
- Use a Kafka buffer between the API and MongoDB to absorb traffic spikes
- Create materialized views for hot aggregations (daily page view totals)

---

### 1.10 Graph Database Model

#### Why a Graph Database?

Certain queries in our e-commerce platform involve multi-hop relationship traversals that relational databases handle poorly:

| Query | Relational Approach | Graph Approach |
|-------|-------------------|----------------|
| "Products frequently bought with headphones" | Multi-table JOIN (orders → order_items → order_items → products), O(n²) self-join | Direct traversal: `(user)-[:PURCHASED]->(headphone)`, then `(user)-[:PURCHASED]->(other)`, O(relationships) |
| "Users who viewed X also bought Y" | Complex subquery with multiple JOINs across events and orders tables | Two-hop path: `(user)-[:VIEWED]->(X)`, `(user)-[:PURCHASED]->(Y)` |
| "Browsing path analysis" | Nearly impossible with SQL — requires recursive CTEs across temporal event data | Natural path traversal along timestamped VIEWED edges |

#### Graph Model

```
Nodes:
  (:User)     — {user_id, name, email}
  (:Product)  — {product_id, name, price}
  (:Category) — {name}

Relationships:
  (User)-[:VIEWED {timestamp, device}]->(Product)
  (User)-[:PURCHASED {order_id, timestamp, quantity}]->(Product)
  (User)-[:ADDED_TO_CART {timestamp}]->(Product)
  (Product)-[:BELONGS_TO]->(Category)
  (Product)-[:FREQUENTLY_BOUGHT_WITH {co_purchase_count}]->(Product)
```

The FREQUENTLY_BOUGHT_WITH relationship is pre-computed by a batch job that analyzes order co-occurrences hourly. This avoids expensive real-time graph traversals for the recommendation query while keeping results reasonably fresh.

---

## 2. Fetching Data

Below we present all 13 queries. Each specifies which database is used. Full query code is in `sql/queries.sql`, `mongodb/queries.js`, and `neo4j/queries.cypher`.

### Q1: Fashion Products with Attributes

**Databases:** MySQL + MongoDB

*Step 1 — SQL (core product data):*
```sql
SELECT p.product_id, p.product_name, p.base_price, p.stock_quantity
FROM   products p
JOIN   categories c ON p.category_id = c.category_id
WHERE  c.category_name = 'fashion';
```

*Step 2 — MongoDB (category-specific attributes):*
```javascript
db.product_catalog.find(
  { category: "fashion" },
  { product_id: 1, "attributes.size": 1, "attributes.color": 1,
    "attributes.material": 1, variants: 1 }
);
```

The application merges the two result sets on `product_id` to present complete product information.

---

### Q2: Last 5 Products Viewed by Sarah (Past 6 Months)

**Database:** MongoDB

```javascript
db.user_events.aggregate([
  { $match: {
      user_id: 1, event_type: "page_view",
      timestamp: { $gte: new Date(Date.now() - 180*24*3600*1000) }
  }},
  { $sort: { timestamp: -1 } },
  { $group: {
      _id: "$data.product_id",
      last_viewed: { $first: "$timestamp" },
      category: { $first: "$data.category" }
  }},
  { $sort: { last_viewed: -1 } },
  { $limit: 5 }
]);
```

Leverages the `{ user_id: 1, timestamp: -1 }` compound index for efficient retrieval.

---

### Q3: Low-Stock Items (< 5 units)

**Database:** MySQL

```sql
SELECT p.product_id, p.product_name, c.category_name, p.stock_quantity
FROM   products p
JOIN   categories c ON p.category_id = c.category_id
WHERE  p.stock_quantity < 5
ORDER  BY p.stock_quantity ASC;
```

Uses `idx_products_stock` index for a fast range scan.

---

### Q4: Fashion Products — Blue Color OR Large Size

**Databases:** MySQL + MongoDB

*SQL identifies fashion products; MongoDB filters by variant attributes:*

```javascript
db.product_catalog.find({
  category: "fashion",
  $or: [
    { "variants.color": { $in: ["blue", "aqua-blue"] } },
    { "variants.size": "L" }
  ]
});
```

---

### Q5: Product Page Views by Popularity

**Database:** MongoDB

```javascript
db.user_events.aggregate([
  { $match: { event_type: "page_view" } },
  { $group: {
      _id: "$data.product_id",
      view_count: { $sum: 1 },
      unique_viewers: { $addToSet: "$user_id" }
  }},
  { $project: {
      product_id: "$_id", view_count: 1,
      unique_viewer_count: { $size: "$unique_viewers" }
  }},
  { $sort: { view_count: -1 } }
]);
```

---

### Q6: Search Terms by Frequency and Time of Day

**Database:** MongoDB

```javascript
db.user_events.aggregate([
  { $match: { user_id: 1, event_type: "search" } },
  { $addFields: {
      time_of_day: { $switch: {
        branches: [
          { case: { $and: [{$gte: [{$hour: "$timestamp"}, 6]},
                           {$lt:  [{$hour: "$timestamp"}, 12]}] }, then: "morning" },
          { case: { $and: [{$gte: [{$hour: "$timestamp"}, 12]},
                           {$lt:  [{$hour: "$timestamp"}, 18]}] }, then: "afternoon" },
          { case: { $and: [{$gte: [{$hour: "$timestamp"}, 18]},
                           {$lt:  [{$hour: "$timestamp"}, 22]}] }, then: "evening" }
        ],
        default: "night"
      }}
  }},
  { $group: {
      _id: { term: "$data.search_term", time: "$time_of_day" },
      frequency: { $sum: 1 },
      last_searched: { $max: "$timestamp" }
  }},
  { $sort: { frequency: -1 } }
]);
```

---

### Q7: Cart Information

**Database:** MySQL

```sql
SELECT c.cart_id, c.user_id, c.device_type,
       COUNT(ci.cart_item_id) AS item_count,
       SUM(ci.quantity * p.base_price) AS total_amount,
       c.is_active
FROM   carts c
JOIN   cart_items ci ON c.cart_id = ci.cart_id
JOIN   products p    ON ci.product_id = p.product_id
GROUP  BY c.cart_id, c.user_id, c.device_type, c.is_active;
```

---

### Q8: All Orders by Sarah

**Database:** MySQL

```sql
SELECT o.order_id, o.order_date, o.status, oi.product_name, oi.quantity,
       oi.unit_price, oi.subtotal, py.payment_method, py.payment_status,
       o.shipping_option, o.total_amount, o.expected_delivery_date
FROM   orders o
JOIN   order_items oi ON o.order_id = oi.order_id
JOIN   payments py    ON o.order_id = py.order_id
JOIN   users u        ON o.user_id  = u.user_id
WHERE  u.username = 'sarah'
ORDER  BY o.order_date DESC;
```

The denormalized `product_name` and `unit_price` in `order_items` avoid an additional JOIN to products.

---

### Q9: Returned Items with Refund Status

**Database:** MySQL

```sql
SELECT r.return_id, r.return_date, r.status AS return_status,
       p.product_name, ri.quantity, ri.refund_amount,
       ri.restocking_fee, ri.refund_status, r.reason
FROM   returns r
JOIN   return_items ri ON r.return_id   = ri.return_id
JOIN   products p      ON ri.product_id = p.product_id
JOIN   users u         ON r.user_id     = u.user_id
WHERE  u.username = 'sarah';
```

---

### Q10: Average Days Between Purchases (Sarah)

**Database:** MySQL

```sql
WITH sarah_orders AS (
    SELECT o.order_date,
           LAG(o.order_date) OVER (ORDER BY o.order_date) AS prev_order_date
    FROM   orders o
    JOIN   users u ON o.user_id = u.user_id
    WHERE  u.username = 'sarah' AND o.status != 'cancelled'
)
SELECT ROUND(AVG(DATEDIFF(order_date, prev_order_date)), 1)
       AS avg_days_between_purchases
FROM   sarah_orders
WHERE  prev_order_date IS NOT NULL;
```

Uses a CTE with the `LAG` window function (MySQL 8.0+) to compute time gaps, and `DATEDIFF()` for day-level difference.

---

### Q11: Cart Abandonment Rate (Past 30 Days)

**Database:** MySQL

```sql
SELECT ROUND(
    100.0 * SUM(CASE WHEN converted_to_order = FALSE THEN 1 ELSE 0 END)
          / NULLIF(COUNT(*), 0), 2
) AS cart_abandonment_pct
FROM carts
WHERE created_at >= NOW() - INTERVAL 30 DAY;
```

---

### Q12: Top 3 Products Purchased with Headphones

**Database:** Neo4j

```cypher
MATCH (hp:Product)-[:BELONGS_TO]->(:Category {name: "electronics"})
WHERE hp.name CONTAINS "Headphone"
MATCH (buyer:User)-[:PURCHASED]->(hp)
MATCH (buyer)-[:PURCHASED]->(other:Product)
WHERE other <> hp
RETURN other.product_id AS product_id,
       other.name       AS product_name,
       COUNT(buyer)     AS co_purchase_count
ORDER BY co_purchase_count DESC
LIMIT 3;
```

This traversal is natural in a graph: starting from headphone nodes, follow PURCHASED edges backwards to buyers, then forward to other products. In SQL, this would require a self-join on order_items — O(n²) vs O(edges).

---

### Q13: Days Since Last Purchase & Total Orders per User

**Database:** MySQL

```sql
SELECT u.user_id, u.username,
       COUNT(o.order_id) AS total_orders,
       DATEDIFF(NOW(), MAX(o.order_date)) AS days_since_last_purchase
FROM   users u
LEFT   JOIN orders o ON u.user_id = o.user_id AND o.status != 'cancelled'
GROUP  BY u.user_id, u.username
ORDER  BY days_since_last_purchase IS NULL, days_since_last_purchase ASC;
```

---

## 3. Data Generation & Performance Evaluation

### Data Generation

We created a Python script (`scripts/generate_data.py`) using the Faker library that generates:

| Dataset | Count | Format | Target DB |
|---------|-------|--------|-----------|
| Users | 1,000 | CSV | MySQL |
| Addresses | 2,000 | CSV | MySQL |
| Categories | 6 | CSV | MySQL |
| Products | 5,000 | CSV | MySQL |
| Product Catalog | 5,000 | JSON | MongoDB |
| Carts | 40,000 | CSV | MySQL |
| Cart Items | ~130,000 | CSV | MySQL |
| Orders | 100,000 | CSV | MySQL |
| Order Items | ~250,000 | CSV | MySQL |
| Payments | 100,000 | CSV | MySQL |
| Returns | ~4,800 | CSV | MySQL |
| Return Items | ~6,000 | CSV | MySQL |
| User Events | 500,000 | JSON | MongoDB |
| Neo4j Import | ~7,000 nodes | Cypher | Neo4j |

Referential consistency is maintained: every `user_id`, `product_id`, `order_id` in child tables exists in the parent table.

### Performance Results

All 13 queries were benchmarked against the generated dataset. The performance evaluation script is in `scripts/performance_eval.py`.

| Query | Database | Rows Scanned | Execution Time | Status |
|-------|----------|-------------|----------------|--------|
| Q1 | MySQL + Mongo | ~830 products | < 50 ms | PASS |
| Q2 | MongoDB | 500K events → 5 results | < 200 ms | PASS |
| Q3 | MySQL | 5,000 products → ~500 | < 30 ms | PASS |
| Q4 | MongoDB | ~830 products | < 80 ms | PASS |
| Q5 | MongoDB | 500K events aggregation | < 800 ms | PASS |
| Q6 | MongoDB | User events subset | < 100 ms | PASS |
| Q7 | MySQL | 40K carts + items | < 500 ms | PASS |
| Q8 | MySQL | ~100 Sarah's orders | < 50 ms | PASS |
| Q9 | MySQL | ~10 returns | < 20 ms | PASS |
| Q10 | MySQL | ~100 Sarah's orders | < 30 ms | PASS |
| Q11 | MySQL | ~20K carts (30-day) | < 100 ms | PASS |
| Q12 | Neo4j | Graph traversal | < 300 ms | PASS |
| Q13 | MySQL | 1K users × orders | < 200 ms | PASS |

All queries complete well within the 2-second threshold.

### Key Indexes That Enable Performance

**MySQL:**
- `idx_products_category` on `products(category_id)` — Q1, Q4
- `idx_products_stock` on `products(stock_quantity)` — Q3
- `idx_orders_user` on `orders(user_id)` — Q8, Q10, Q13
- `idx_orders_date` on `orders(order_date)` — Q11, Q13
- `idx_carts_active` on `carts(is_active, converted_to_order)` — Q11

**MongoDB:**
- `{ user_id: 1, timestamp: -1 }` on `user_events` — Q2, Q6
- `{ event_type: 1 }` on `user_events` — Q5
- `{ category: 1 }` on `product_catalog` — Q1, Q4
- `{ "variants.color": 1 }` on `product_catalog` — Q4

**Neo4j:**
- Unique constraint on `Product.product_id` — Q12
- Unique constraint on `Category.name` — Q12

---

## 4. Revision Log

| Rev # | Date | Design Component | Change Made | Rationale |
|-------|------|-----------------|-------------|-----------|
| 1 | 2026-02-02 | Overall Architecture | Decided on a hybrid database approach (MySQL + MongoDB + Redis + Neo4j) instead of a single-database solution. | The e-commerce narrative involves structured transactions (orders), flexible schemas (product attributes), high-frequency ephemeral data (sessions), and relationship traversals (recommendations). No single database excels at all four. |
| 2 | 2026-02-07 | Product Attributes Storage | Moved category-specific attributes from a relational EAV (Entity-Attribute-Value) model to MongoDB document storage. | The EAV model required expensive pivot queries for every product detail page. MongoDB's flexible documents store nested attributes natively, eliminating the need for dynamic column pivoting. |
| 3 | 2026-02-12 | Session & Cart Management | Migrated session/cart storage from a MySQL `sessions` table to Redis with MongoDB backup. | Cross-device session restoration requires sub-millisecond reads. MySQL added 5–15ms of latency per session lookup under load. Redis delivers < 1ms. MongoDB serves as a durable fallback. |
| 4 | 2026-02-18 | Order Items Denormalization | Added `product_name` and `unit_price` snapshot columns to `order_items`, denormalizing from the normalized design. | Order history queries (Q8) were the most frequent read operation but required a JOIN to `products`. Denormalization eliminated this JOIN and ensures historical accuracy (prices change over time). Read/write trade-off is favorable since orders are created once but read many times. |
| 5 | 2026-02-21 | User Behavior Tracking | Changed from appending behavioral events to a MySQL `events` table to using MongoDB's `user_events` collection with TTL index. | Behavioral events are semi-structured (different fields per event type), high-volume (500K+), and write-heavy. MySQL's rigid schema required ALTER TABLE for each new event field. MongoDB handles schema variability natively and TTL indexes automate data lifecycle. |
| 6 | 2026-02-24 | Query Performance — Index Strategy | Added compound indexes on `user_events { user_id, timestamp }`, `products { category_id }`, and `carts { is_active, converted_to_order }`. | Initial performance testing showed Q2 (recently viewed) taking > 3 seconds without the compound index. Q11 (cart abandonment) was doing a full table scan. After adding targeted indexes, all queries fell below the 2-second threshold. |
| 7 | 2026-02-26 | Real-Time Inventory | Introduced Redis as a caching layer for inventory counts (`inventory:{product_id}`) with write-through sync to MySQL. | The product page showed stock availability in real-time, but querying MySQL for every page view created unnecessary load. Redis INCR/DECR provides atomic, sub-millisecond stock updates with periodic MySQL reconciliation. |

---

## 5. Team Contributions

| Team Member | Responsibilities |
|-------------|-----------------|
| **Member A** | Database design (tasks 1–5), SQL schema, relational queries (Q1, Q3, Q7–Q11, Q13), performance evaluation |
| **Member B** | Database design (tasks 6–10), MongoDB & Neo4j schemas, non-relational queries (Q2, Q4–Q6, Q12), data generation script |

---

*End of Report*
