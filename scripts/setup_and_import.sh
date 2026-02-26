#!/bin/bash
# ============================================================
# E-Commerce Platform — One-Click Setup & Data Import
# ============================================================
# Prerequisites: Docker Desktop running, Python 3.8+
#
# This script will:
#   1. Generate synthetic data (if not already present)
#   2. Start MySQL 8.0 and MongoDB 7 Docker containers
#   3. Create the MySQL schema
#   4. Import all data into MySQL and MongoDB
#   5. Create MongoDB indexes
# ============================================================

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DATA_DIR="$PROJECT_DIR/generated_data"

echo "============================================================"
echo "  E-Commerce Database — Setup & Import"
echo "============================================================"

# ---------- Step 1: Generate data ----------
if [ ! -f "$DATA_DIR/users.csv" ]; then
    echo ""
    echo "[Step 1/5] Generating synthetic data..."
    cd "$PROJECT_DIR"
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
    fi
    source .venv/bin/activate
    pip install faker --quiet
    python3 scripts/generate_data.py
    deactivate
else
    echo ""
    echo "[Step 1/5] Data already exists in generated_data/, skipping generation."
fi

# ---------- Step 2: Start Docker containers ----------
echo ""
echo "[Step 2/5] Starting Docker containers..."

if docker inspect ecommerce_mysql >/dev/null 2>&1; then
    if [ "$(docker inspect -f '{{.State.Running}}' ecommerce_mysql)" = "true" ]; then
        echo "  MySQL container already running."
    else
        docker start ecommerce_mysql
        echo "  MySQL container started."
    fi
else
    docker run -d --name ecommerce_mysql \
        -e MYSQL_ROOT_PASSWORD=root123 \
        -e MYSQL_DATABASE=ecommerce \
        -p 3307:3306 \
        mysql:8.0
    echo "  MySQL container created."
fi

if docker inspect ecommerce_mongo >/dev/null 2>&1; then
    if [ "$(docker inspect -f '{{.State.Running}}' ecommerce_mongo)" = "true" ]; then
        echo "  MongoDB container already running."
    else
        docker start ecommerce_mongo
        echo "  MongoDB container started."
    fi
else
    docker run -d --name ecommerce_mongo -p 27017:27017 mongo:7
    echo "  MongoDB container created."
fi

echo "  Waiting for MySQL to be ready..."
for i in $(seq 1 30); do
    if docker exec ecommerce_mysql mysql -uroot -proot123 -e "SELECT 1" >/dev/null 2>&1; then
        echo "  MySQL is ready."
        break
    fi
    sleep 2
done

# ---------- Step 3: Create MySQL schema ----------
echo ""
echo "[Step 3/5] Creating MySQL schema..."
docker cp "$PROJECT_DIR/sql/schema.sql" ecommerce_mysql:/tmp/schema.sql
docker exec ecommerce_mysql mysql -uroot -proot123 ecommerce -e "source /tmp/schema.sql" 2>/dev/null
echo "  Schema created."

# ---------- Step 4: Import data into MySQL ----------
echo ""
echo "[Step 4/5] Importing data into MySQL..."
docker cp "$DATA_DIR/" ecommerce_mysql:/tmp/data/
docker cp "$PROJECT_DIR/scripts/import_mysql.sql" ecommerce_mysql:/tmp/import.sql
docker exec ecommerce_mysql mysql -uroot -proot123 --local-infile=1 ecommerce -e "source /tmp/import.sql" 2>/dev/null
echo "  MySQL import complete."

# ---------- Step 5: Import data into MongoDB ----------
echo ""
echo "[Step 5/5] Importing data into MongoDB..."
docker cp "$DATA_DIR/product_catalog.json" ecommerce_mongo:/tmp/product_catalog.json
docker cp "$DATA_DIR/user_events.json" ecommerce_mongo:/tmp/user_events.json

docker exec ecommerce_mongo mongoimport \
    --db ecommerce --collection product_catalog \
    --file /tmp/product_catalog.json --jsonArray --drop 2>/dev/null

docker exec ecommerce_mongo mongoimport \
    --db ecommerce --collection user_events \
    --file /tmp/user_events.json --jsonArray --drop 2>/dev/null

docker exec ecommerce_mongo mongosh ecommerce --quiet --eval '
    db.product_catalog.createIndex({ product_id: 1 }, { unique: true });
    db.product_catalog.createIndex({ category: 1 });
    db.product_catalog.createIndex({ "variants.color": 1 });
    db.product_catalog.createIndex({ "variants.size": 1 });
    db.user_events.createIndex({ user_id: 1, timestamp: -1 });
    db.user_events.createIndex({ event_type: 1 });
    db.user_events.createIndex({ "data.product_id": 1 });
' 2>/dev/null
echo "  MongoDB import and indexing complete."

# ---------- Done ----------
echo ""
echo "============================================================"
echo "  Setup complete! You can now run the queries:"
echo ""
echo "    python3 scripts/run_all_queries.py"
echo ""
echo "  To stop containers later:"
echo "    docker stop ecommerce_mysql ecommerce_mongo"
echo "  To remove containers:"
echo "    docker rm ecommerce_mysql ecommerce_mongo"
echo "============================================================"
