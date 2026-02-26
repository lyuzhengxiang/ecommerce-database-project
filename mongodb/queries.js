// ============================================================
// Fetching Data — MongoDB Queries
// ============================================================

// ---------------------------------------------------------------
// Q1 (supplement): Fashion products with flexible attributes
//   After fetching product_ids from SQL, retrieve their attributes:
// ---------------------------------------------------------------
db.product_catalog.find(
  { category: "fashion" },
  {
    product_id: 1,
    "attributes.size": 1,
    "attributes.color": 1,
    "attributes.material": 1,
    variants: 1,
    _id: 0
  }
);

// ---------------------------------------------------------------
// Q2: Last 5 products viewed by Sarah (past 6 months)
// ---------------------------------------------------------------
var sixMonthsAgo = new Date();
sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6);

db.user_events.aggregate([
  {
    $match: {
      user_id: 1,                     // Sarah's user_id
      event_type: "page_view",
      timestamp: { $gte: sixMonthsAgo }
    }
  },
  { $sort: { timestamp: -1 } },
  {
    $group: {
      _id: "$data.product_id",
      last_viewed: { $first: "$timestamp" },
      category: { $first: "$data.category" }
    }
  },
  { $sort: { last_viewed: -1 } },
  { $limit: 5 },
  {
    $project: {
      product_id: "$_id",
      last_viewed: 1,
      category: 1,
      _id: 0
    }
  }
]);

// ---------------------------------------------------------------
// Q4 (supplement): Fashion products in blue OR large size
//   Filter MongoDB product_catalog for matching variants
// ---------------------------------------------------------------
db.product_catalog.find(
  {
    category: "fashion",
    $or: [
      { "variants.color": "blue" },
      { "variants.color": "aqua-blue" },
      { "variants.size": "L" }
    ]
  },
  {
    product_id: 1,
    variants: 1,
    attributes: 1,
    _id: 0
  }
);

// ---------------------------------------------------------------
// Q5: Product page views ordered by popularity
// ---------------------------------------------------------------
db.user_events.aggregate([
  { $match: { event_type: "page_view" } },
  {
    $group: {
      _id: "$data.product_id",
      view_count: { $sum: 1 },
      unique_viewers: { $addToSet: "$user_id" }
    }
  },
  {
    $project: {
      product_id: "$_id",
      view_count: 1,
      unique_viewer_count: { $size: "$unique_viewers" },
      _id: 0
    }
  },
  { $sort: { view_count: -1 } }
]);

// ---------------------------------------------------------------
// Q6: Recent search terms — frequency & time-of-day category
// ---------------------------------------------------------------
db.user_events.aggregate([
  {
    $match: {
      user_id: 1,
      event_type: "search"
    }
  },
  {
    $addFields: {
      hour: { $hour: "$timestamp" },
      time_of_day: {
        $switch: {
          branches: [
            { case: { $and: [{ $gte: ["$hour", 6] },  { $lt: ["$hour", 12] }] }, then: "morning" },
            { case: { $and: [{ $gte: ["$hour", 12] }, { $lt: ["$hour", 18] }] }, then: "afternoon" },
            { case: { $and: [{ $gte: ["$hour", 18] }, { $lt: ["$hour", 22] }] }, then: "evening" }
          ],
          default: "night"
        }
      }
    }
  },
  {
    $group: {
      _id: {
        search_term: "$data.search_term",
        time_of_day: "$time_of_day"
      },
      frequency: { $sum: 1 },
      last_searched: { $max: "$timestamp" }
    }
  },
  { $sort: { frequency: -1 } },
  {
    $project: {
      search_term: "$_id.search_term",
      time_of_day: "$_id.time_of_day",
      frequency: 1,
      last_searched: 1,
      _id: 0
    }
  }
]);
