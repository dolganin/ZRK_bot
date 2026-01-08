CREATE TABLE IF NOT EXISTS students (
    id BIGINT PRIMARY KEY,
    name TEXT NOT NULL,
    telegram_username TEXT,
    balance INTEGER DEFAULT 0,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    course TEXT,
    faculty TEXT
);

CREATE TABLE IF NOT EXISTS admins (
    id SERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS codes (
    id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(id),
    code TEXT NOT NULL UNIQUE,
    points INTEGER NOT NULL,
    is_income BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    starts_at TIMESTAMPTZ NULL,
    expires_at TIMESTAMPTZ NULL,
    max_uses INTEGER NULL,
    CONSTRAINT ck_codes_income_only CHECK (is_income = TRUE)
);

CREATE INDEX IF NOT EXISTS ix_codes_code ON codes(code);
CREATE INDEX IF NOT EXISTS ix_codes_window ON codes(starts_at, expires_at);

CREATE TABLE IF NOT EXISTS user_codes (
    user_id BIGINT REFERENCES students(id) ON DELETE CASCADE,
    code_id INTEGER REFERENCES codes(id) ON DELETE CASCADE,
    used_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_id, code_id)
);

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    price_points INTEGER NOT NULL,
    stock INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS ix_products_active ON products(is_active);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    total_points INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    fulfilled_at TIMESTAMPTZ NULL,
    fulfilled_by BIGINT NULL REFERENCES admins(user_id)
);

CREATE INDEX IF NOT EXISTS ix_orders_user_status ON orders(user_id, status);

CREATE TABLE IF NOT EXISTS order_items (
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    qty INTEGER NOT NULL,
    issued_qty INTEGER NOT NULL DEFAULT 0,
    points_each INTEGER NOT NULL,
    PRIMARY KEY (order_id, product_id),
    CONSTRAINT ck_order_items_qty_nonneg CHECK (qty >= 0),
    CONSTRAINT ck_order_items_issued_nonneg CHECK (issued_qty >= 0),
    CONSTRAINT ck_order_items_issued_le_qty CHECK (issued_qty <= qty)
);

CREATE INDEX IF NOT EXISTS ix_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS ix_order_items_product ON order_items(product_id);

CREATE TABLE IF NOT EXISTS claim_tokens (
    token TEXT PRIMARY KEY,
    order_id INTEGER NOT NULL UNIQUE REFERENCES orders(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    expires_at TIMESTAMP NULL,
    issued_by BIGINT NULL REFERENCES admins(user_id),
    issued_at TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS product_images (
  id BIGSERIAL PRIMARY KEY,
  product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  telegram_file_id TEXT,
  telegram_file_unique_id TEXT,
  storage_path TEXT,
  mime TEXT,
  size_bytes BIGINT,
  width INT,
  height INT,
  is_main BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_product_images_main
ON product_images(product_id)
WHERE is_main = TRUE;

CREATE INDEX IF NOT EXISTS ix_product_images_product
ON product_images(product_id);

CREATE TABLE IF NOT EXISTS maps (
  id BIGSERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  telegram_file_id TEXT,
  telegram_file_unique_id TEXT,
  storage_path TEXT,
  mime TEXT,
  size_bytes BIGINT,
  width INT,
  height INT,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_maps_active ON maps(is_active);
