-- ============================================================
-- E-Commerce Platform — Relational Database Schema (MySQL 8.0+)
-- ============================================================

-- ------- Users & Addresses -------

CREATE TABLE users (
    user_id       INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    email         VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name    VARCHAR(50),
    last_name     VARCHAR(50),
    phone         VARCHAR(20),
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE addresses (
    address_id   INT AUTO_INCREMENT PRIMARY KEY,
    user_id      INT NOT NULL,
    address_type VARCHAR(20) CHECK (address_type IN ('shipping', 'billing')),
    street       VARCHAR(255),
    city         VARCHAR(100),
    state        VARCHAR(100),
    zip_code     VARCHAR(20),
    country      VARCHAR(100) DEFAULT 'US',
    is_default   BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ------- Product Catalog (core relational data) -------

CREATE TABLE categories (
    category_id        INT AUTO_INCREMENT PRIMARY KEY,
    category_name      VARCHAR(100) NOT NULL UNIQUE,
    parent_category_id INT,
    description        TEXT,
    FOREIGN KEY (parent_category_id) REFERENCES categories(category_id)
) ENGINE=InnoDB;

CREATE TABLE products (
    product_id     INT AUTO_INCREMENT PRIMARY KEY,
    category_id    INT,
    product_name   VARCHAR(255) NOT NULL,
    description    TEXT,
    base_price     DECIMAL(10, 2) NOT NULL,
    stock_quantity INT NOT NULL DEFAULT 0,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
) ENGINE=InnoDB;

CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_stock    ON products(stock_quantity);

CREATE TABLE product_images (
    image_id   INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    image_url  VARCHAR(500) NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ------- Shopping Cart -------

CREATE TABLE carts (
    cart_id            INT AUTO_INCREMENT PRIMARY KEY,
    user_id            INT,
    session_id         VARCHAR(255),
    device_type        VARCHAR(50) CHECK (device_type IN ('tablet', 'laptop', 'mobile', 'desktop')),
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active          BOOLEAN DEFAULT TRUE,
    converted_to_order BOOLEAN DEFAULT FALSE,
    converted_at       TIMESTAMP NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
) ENGINE=InnoDB;

CREATE INDEX idx_carts_user   ON carts(user_id);
CREATE INDEX idx_carts_active ON carts(is_active, converted_to_order);

CREATE TABLE cart_items (
    cart_item_id INT AUTO_INCREMENT PRIMARY KEY,
    cart_id      INT NOT NULL,
    product_id   INT NOT NULL,
    quantity     INT NOT NULL DEFAULT 1 CHECK (quantity > 0),
    added_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cart_id)    REFERENCES carts(cart_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
) ENGINE=InnoDB;

-- ------- Orders -------

CREATE TABLE orders (
    order_id               INT AUTO_INCREMENT PRIMARY KEY,
    user_id                INT,
    order_date             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status                 VARCHAR(50) DEFAULT 'pending'
                               CHECK (status IN ('pending','confirmed','shipped','delivered','cancelled')),
    total_amount           DECIMAL(10, 2),
    tax_amount             DECIMAL(10, 2) DEFAULT 0,
    shipping_fee           DECIMAL(10, 2) DEFAULT 0,
    shipping_option        VARCHAR(50) CHECK (shipping_option IN ('standard','mid_tier','expedited','overnight')),
    shipping_address_id    INT,
    expected_shipping_date DATE,
    expected_delivery_date DATE,
    FOREIGN KEY (user_id)            REFERENCES users(user_id),
    FOREIGN KEY (shipping_address_id) REFERENCES addresses(address_id)
) ENGINE=InnoDB;

CREATE INDEX idx_orders_user   ON orders(user_id);
CREATE INDEX idx_orders_date   ON orders(order_date);
CREATE INDEX idx_orders_status ON orders(status);

CREATE TABLE order_items (
    order_item_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id      INT NOT NULL,
    product_id    INT,
    product_name  VARCHAR(255),   -- denormalized snapshot
    unit_price    DECIMAL(10, 2), -- price at time of purchase
    quantity      INT NOT NULL CHECK (quantity > 0),
    subtotal      DECIMAL(10, 2),
    FOREIGN KEY (order_id)   REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
) ENGINE=InnoDB;

CREATE INDEX idx_order_items_order   ON order_items(order_id);
CREATE INDEX idx_order_items_product ON order_items(product_id);

-- ------- Payments -------

CREATE TABLE payments (
    payment_id         INT AUTO_INCREMENT PRIMARY KEY,
    order_id           INT,
    payment_method     VARCHAR(50) CHECK (payment_method IN ('credit_card','debit_card','bank_account','paypal')),
    payment_status     VARCHAR(50) DEFAULT 'pending'
                           CHECK (payment_status IN ('pending','approved','declined','refunded')),
    amount             DECIMAL(10, 2) NOT NULL,
    transaction_date   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    card_last_four     VARCHAR(4),
    billing_address_id INT,
    FOREIGN KEY (order_id)           REFERENCES orders(order_id),
    FOREIGN KEY (billing_address_id) REFERENCES addresses(address_id)
) ENGINE=InnoDB;

CREATE INDEX idx_payments_order ON payments(order_id);

-- ------- Returns & Refunds -------

CREATE TABLE returns (
    return_id   INT AUTO_INCREMENT PRIMARY KEY,
    order_id    INT,
    user_id     INT,
    return_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status      VARCHAR(50) DEFAULT 'initiated'
                    CHECK (status IN ('initiated','label_printed','shipped_back','received','refunded','exchanged')),
    reason      TEXT,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (user_id)  REFERENCES users(user_id)
) ENGINE=InnoDB;

CREATE INDEX idx_returns_user  ON returns(user_id);
CREATE INDEX idx_returns_order ON returns(order_id);

CREATE TABLE return_items (
    return_item_id INT AUTO_INCREMENT PRIMARY KEY,
    return_id      INT NOT NULL,
    order_item_id  INT,
    product_id     INT,
    quantity       INT NOT NULL CHECK (quantity > 0),
    refund_amount  DECIMAL(10, 2),
    restocking_fee DECIMAL(10, 2) DEFAULT 0,
    refund_status  VARCHAR(50) DEFAULT 'pending'
                       CHECK (refund_status IN ('pending','processed','completed')),
    FOREIGN KEY (return_id)    REFERENCES returns(return_id) ON DELETE CASCADE,
    FOREIGN KEY (order_item_id) REFERENCES order_items(order_item_id),
    FOREIGN KEY (product_id)   REFERENCES products(product_id)
) ENGINE=InnoDB;
