// ============================================================
// E-Commerce Platform — Neo4j Graph Database Model
// ============================================================

// ------- Node Constraints & Indexes -------

CREATE CONSTRAINT user_id_unique    IF NOT EXISTS FOR (u:User)     REQUIRE u.user_id IS UNIQUE;
CREATE CONSTRAINT product_id_unique IF NOT EXISTS FOR (p:Product)  REQUIRE p.product_id IS UNIQUE;
CREATE CONSTRAINT cat_name_unique   IF NOT EXISTS FOR (c:Category) REQUIRE c.name IS UNIQUE;

// ------- Node Creation Examples -------

// Users
CREATE (:User {user_id: 1, name: "Sarah", email: "sarah@example.com"});

// Categories
CREATE (:Category {name: "electronics"});
CREATE (:Category {name: "fashion"});
CREATE (:Category {name: "home_decor"});

// Products
CREATE (:Product {product_id: 101, name: "Wireless Headphones", price: 79.99});
CREATE (:Product {product_id: 201, name: "Aqua-Blue Summer Dress", price: 49.99});
CREATE (:Product {product_id: 301, name: "Ceramic Vase", price: 34.99});

// ------- Relationships -------

// Product belongs to category
MATCH (p:Product {product_id: 101}), (c:Category {name: "electronics"})
CREATE (p)-[:BELONGS_TO]->(c);

MATCH (p:Product {product_id: 201}), (c:Category {name: "fashion"})
CREATE (p)-[:BELONGS_TO]->(c);

MATCH (p:Product {product_id: 301}), (c:Category {name: "home_decor"})
CREATE (p)-[:BELONGS_TO]->(c);

// User viewed product
MATCH (u:User {user_id: 1}), (p:Product {product_id: 101})
CREATE (u)-[:VIEWED {timestamp: datetime("2026-02-20T14:30:00"), device: "tablet"}]->(p);

// User purchased product
MATCH (u:User {user_id: 1}), (p:Product {product_id: 101})
CREATE (u)-[:PURCHASED {order_id: 1001, timestamp: datetime("2026-02-20T16:00:00"), quantity: 1}]->(p);

// Frequently bought together (computed relationship)
MATCH (p1:Product {product_id: 101}), (p2:Product {product_id: 201})
CREATE (p1)-[:FREQUENTLY_BOUGHT_WITH {co_purchase_count: 47}]->(p2);

// User added to cart
MATCH (u:User {user_id: 1}), (p:Product {product_id: 101})
CREATE (u)-[:ADDED_TO_CART {timestamp: datetime("2026-02-20T14:35:00")}]->(p);

// ------- Graph Model Summary -------
// Nodes:  User, Product, Category, Order
// Relationships:
//   (User)-[:VIEWED {timestamp, device}]->(Product)
//   (User)-[:PURCHASED {order_id, timestamp, quantity}]->(Product)
//   (User)-[:ADDED_TO_CART {timestamp}]->(Product)
//   (User)-[:SEARCHED {term, timestamp}]->(Product)
//   (Product)-[:BELONGS_TO]->(Category)
//   (Product)-[:FREQUENTLY_BOUGHT_WITH {co_purchase_count}]->(Product)
//   (User)-[:PLACED]->(Order)
//   (Order)-[:CONTAINS {quantity}]->(Product)
