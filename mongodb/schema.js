// ============================================================
// E-Commerce Platform — MongoDB Collections & Schema Design
// ============================================================

// ------- 1. Product Catalog (flexible attributes per category) -------
db.createCollection("product_catalog", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["product_id", "category", "attributes"],
      properties: {
        product_id:  { bsonType: "int", description: "FK to SQL products table" },
        category:    { bsonType: "string" },
        attributes:  { bsonType: "object" },
        variants:    { bsonType: "array" },
        tags:        { bsonType: "array" }
      }
    }
  }
});

db.product_catalog.createIndex({ product_id: 1 }, { unique: true });
db.product_catalog.createIndex({ category: 1 });
db.product_catalog.createIndex({ "attributes.color": 1 });
db.product_catalog.createIndex({ "attributes.size": 1 });
db.product_catalog.createIndex({ "variants.color": 1 });

// Example: Electronics (headphones)
// {
//   product_id: 101,
//   category: "electronics",
//   attributes: {
//     battery_life: "30 hours",
//     connectivity: "Bluetooth 5.0",
//     weight: "250g",
//     noise_cancellation: true,
//     driver_size: "40mm"
//   },
//   variants: [
//     { color: "black", sku: "HP-BLK-001" },
//     { color: "white", sku: "HP-WHT-001" }
//   ],
//   tags: ["wireless", "over-ear", "noise-cancelling"]
// }

// Example: Fashion (dress)
// {
//   product_id: 201,
//   category: "fashion",
//   attributes: {
//     material: "cotton blend",
//     care_instructions: "Machine wash cold",
//     style: "summer dress",
//     pattern: "solid"
//   },
//   variants: [
//     { size: "S", color: "aqua-blue", sku: "DR-AQB-S" },
//     { size: "M", color: "aqua-blue", sku: "DR-AQB-M" },
//     { size: "L", color: "aqua-blue", sku: "DR-AQB-L" },
//     { size: "S", color: "coral",     sku: "DR-CRL-S" }
//   ],
//   tags: ["summer", "casual", "dress"]
// }

// Example: Home Décor (vase)
// {
//   product_id: 301,
//   category: "home_decor",
//   attributes: {
//     dimensions: { height: "30cm", width: "15cm", depth: "15cm" },
//     material: "ceramic",
//     ceramic_type: "porcelain",
//     weight: "1.2kg",
//     care_instructions: "Hand wash only"
//   },
//   variants: [
//     { color: "white",     sku: "VS-WHT-001" },
//     { color: "terracotta", sku: "VS-TRC-001" }
//   ],
//   tags: ["ceramic", "vase", "living-room"]
// }


// ------- 2. User Events (behavior tracking) -------
db.createCollection("user_events");

db.user_events.createIndex({ user_id: 1, timestamp: -1 });
db.user_events.createIndex({ event_type: 1 });
db.user_events.createIndex({ "data.product_id": 1 });
db.user_events.createIndex({ timestamp: 1 }, { expireAfterSeconds: 365 * 24 * 3600 });

// Example documents:
// {
//   user_id: 1,
//   event_type: "page_view",        // page_view | search | click | add_to_cart | remove_from_cart
//   timestamp: ISODate("2026-02-20T14:30:00Z"),
//   session_id: "sess_abc123",
//   device_type: "tablet",
//   data: {
//     product_id: 101,
//     category: "electronics",
//     time_spent_seconds: 45,
//     page_url: "/products/headphones/101"
//   }
// }
//
// {
//   user_id: 1,
//   event_type: "search",
//   timestamp: ISODate("2026-02-20T14:25:00Z"),
//   session_id: "sess_abc123",
//   device_type: "tablet",
//   data: {
//     search_term: "wireless headphones",
//     results_count: 24,
//     clicked_product_ids: [101, 102, 105]
//   }
// }


// ------- 3. Sessions (cross-device persistence) -------
db.createCollection("sessions");

db.sessions.createIndex({ user_id: 1 }, { unique: true });
db.sessions.createIndex({ last_active: 1 }, { expireAfterSeconds: 30 * 24 * 3600 });

// Example:
// {
//   user_id: 1,
//   session_id: "sess_abc123",
//   device_history: ["tablet", "laptop"],
//   cart_snapshot: {
//     items: [
//       { product_id: 101, product_name: "Wireless Headphones", quantity: 1, price: 79.99 },
//       { product_id: 201, product_name: "Aqua-Blue Summer Dress", quantity: 1, price: 49.99 }
//     ],
//     total: 129.98
//   },
//   recently_viewed: [101, 201, 301],
//   last_active: ISODate("2026-02-20T16:00:00Z"),
//   created_at: ISODate("2026-02-20T14:00:00Z")
// }
