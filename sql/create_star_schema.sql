-- DDL du schéma en étoile pour l'entrepôt de données Olist
-- Exécuter avec : sqlite3 data/database/olist_dw.db < sql/create_star_schema.sql

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ── Dimensions ──────────────────────────────────────────────────────────

DROP TABLE IF EXISTS fact_orders;
DROP TABLE IF EXISTS dim_customers;
DROP TABLE IF EXISTS dim_sellers;
DROP TABLE IF EXISTS dim_dates;
DROP TABLE IF EXISTS dim_products;
DROP TABLE IF EXISTS dim_geolocation;

CREATE TABLE dim_dates (
    date_key     INTEGER PRIMARY KEY,   -- AAAAMMJJ
    full_date    DATE    NOT NULL,
    year         INTEGER NOT NULL,
    quarter      INTEGER NOT NULL,
    month        INTEGER NOT NULL,
    day          INTEGER NOT NULL,
    day_of_week  INTEGER NOT NULL,      -- 0=Lundi
    day_name     TEXT    NOT NULL,
    is_weekend   INTEGER NOT NULL       -- 0 ou 1
);

CREATE TABLE dim_geolocation (
    geo_key          INTEGER PRIMARY KEY AUTOINCREMENT,
    zip_code_prefix  TEXT    NOT NULL UNIQUE,
    lat              REAL,
    lng              REAL,
    city             TEXT,
    state            TEXT
);

CREATE TABLE dim_customers (
    customer_key       INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id        TEXT    NOT NULL UNIQUE,
    customer_unique_id TEXT,
    geo_key            INTEGER,
    city               TEXT,
    state              TEXT,
    FOREIGN KEY (geo_key) REFERENCES dim_geolocation(geo_key)
);

CREATE TABLE dim_sellers (
    seller_key  INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_id   TEXT    NOT NULL UNIQUE,
    geo_key     INTEGER,
    city        TEXT,
    state       TEXT,
    FOREIGN KEY (geo_key) REFERENCES dim_geolocation(geo_key)
);

CREATE TABLE dim_products (
    product_key      INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id       TEXT    NOT NULL UNIQUE,
    category_name_pt TEXT,
    category_name_en TEXT,
    weight_g         REAL,
    length_cm        REAL,
    height_cm        REAL,
    width_cm         REAL,
    photos_qty       INTEGER
);

-- ── Table de faits ─────────────────────────────────────────────────────
-- Grain : une ligne par article de commande

CREATE TABLE fact_orders (
    fact_key             INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id             TEXT    NOT NULL,
    order_item_id        INTEGER NOT NULL,
    date_key             INTEGER,
    customer_key         INTEGER,
    seller_key           INTEGER,
    product_key          INTEGER,
    customer_geo_key     INTEGER,
    seller_geo_key       INTEGER,
    order_status         TEXT,
    price                REAL,
    freight_value        REAL,
    order_payment_total  REAL,
    payment_type         TEXT,
    review_score         INTEGER,
    delivery_days        REAL,
    estimated_days       REAL,
    delivery_delta_days  REAL,
    UNIQUE(order_id, order_item_id),
    CHECK(review_score BETWEEN 1 AND 5 OR review_score IS NULL),
    CHECK(price >= 0),
    CHECK(freight_value >= 0),
    FOREIGN KEY (date_key)         REFERENCES dim_dates(date_key),
    FOREIGN KEY (customer_key)     REFERENCES dim_customers(customer_key),
    FOREIGN KEY (seller_key)       REFERENCES dim_sellers(seller_key),
    FOREIGN KEY (product_key)      REFERENCES dim_products(product_key),
    FOREIGN KEY (customer_geo_key) REFERENCES dim_geolocation(geo_key),
    FOREIGN KEY (seller_geo_key)   REFERENCES dim_geolocation(geo_key)
);

-- ── Index ───────────────────────────────────────────────────────────────

CREATE INDEX idx_fact_order_id        ON fact_orders(order_id);
CREATE INDEX idx_fact_date_key        ON fact_orders(date_key);
CREATE INDEX idx_fact_customer_key    ON fact_orders(customer_key);
CREATE INDEX idx_fact_seller_key      ON fact_orders(seller_key);
CREATE INDEX idx_fact_product_key     ON fact_orders(product_key);
CREATE INDEX idx_fact_order_status    ON fact_orders(order_status);
CREATE INDEX idx_fact_customer_geo    ON fact_orders(customer_geo_key);
CREATE INDEX idx_fact_seller_geo      ON fact_orders(seller_geo_key);
