// ============================================================
// Fetching Data — Neo4j Cypher Queries
// ============================================================

// ---------------------------------------------------------------
// Q12: Top 3 products most frequently purchased together
//      with "headphones"
// ---------------------------------------------------------------

// Approach: find users who purchased a product in the "electronics"
// category named like headphones, then find other products those
// same users also purchased, and rank by co-occurrence count.

MATCH (headphone:Product)-[:BELONGS_TO]->(:Category {name: "electronics"})
WHERE headphone.name CONTAINS "Headphone"
MATCH (buyer:User)-[:PURCHASED]->(headphone)
MATCH (buyer)-[:PURCHASED]->(other:Product)
WHERE other <> headphone
RETURN other.product_id AS product_id,
       other.name       AS product_name,
       COUNT(buyer)     AS co_purchase_count
ORDER BY co_purchase_count DESC
LIMIT 3;

// ---------------------------------------------------------------
// Alternative Q12: using pre-computed FREQUENTLY_BOUGHT_WITH edges
// ---------------------------------------------------------------

MATCH (headphone:Product)-[r:FREQUENTLY_BOUGHT_WITH]->(other:Product)
WHERE headphone.name CONTAINS "Headphone"
RETURN other.product_id AS product_id,
       other.name       AS product_name,
       r.co_purchase_count
ORDER BY r.co_purchase_count DESC
LIMIT 3;

// ---------------------------------------------------------------
// Bonus: Graph queries that outperform relational joins
// ---------------------------------------------------------------

// "Users who viewed X also purchased Y" (recommendation)
MATCH (target:Product {product_id: 101})
MATCH (u:User)-[:VIEWED]->(target)
MATCH (u)-[:PURCHASED]->(rec:Product)
WHERE rec <> target
RETURN rec.product_id, rec.name, COUNT(u) AS strength
ORDER BY strength DESC
LIMIT 5;

// Multi-hop browsing path: what do users browse after headphones?
MATCH (u:User)-[:VIEWED]->(p1:Product {product_id: 101})
MATCH (u)-[:VIEWED]->(p2:Product)
WHERE p2 <> p1
WITH  p2, COUNT(u) AS viewers
RETURN p2.product_id, p2.name, viewers
ORDER BY viewers DESC
LIMIT 10;
