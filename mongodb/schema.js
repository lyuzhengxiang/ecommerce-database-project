// as mentioned in the report, we use MongoDB in the following three scenarios

// product attributes
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

// behavior tracking
db.createCollection("user_events");
db.user_events.createIndex({ user_id: 1, timestamp: -1 });
db.user_events.createIndex({ event_type: 1 });
db.user_events.createIndex({ "data.product_id": 1 });
db.user_events.createIndex({ timestamp: 1 }, { expireAfterSeconds: 365 * 24 * 3600 });

// session management 
db.createCollection("sessions");
db.sessions.createIndex({ user_id: 1 }, { unique: true });
db.sessions.createIndex({ last_active: 1 }, { expireAfterSeconds: 30 * 24 * 3600 });
