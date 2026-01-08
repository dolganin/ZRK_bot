CREATE TABLE IF NOT EXISTS students (
    id BIGINT PRIMARY KEY,              -- Telegram ID студента
    name TEXT NOT NULL,                 -- Имя студента
    telegram_username TEXT,            -- Никнейм студента в Telegram (может быть NULL)
    balance INTEGER DEFAULT 0,          -- Баланс студента
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Время регистрации
    course TEXT,                        -- Курс студента (например, 1, 2, 3, 4, 5, магистратура, аспирантура)
    faculty TEXT                        -- Факультет студента (например, ИИР, ФЕН, ФФ и т.д.)
);


-- Таблица администраторов
CREATE TABLE IF NOT EXISTS admins (
    id SERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE NOT NULL  -- Telegram ID администратора
);

-- Таблица мероприятий
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,  -- Уникальное название мероприятия
    created_at TIMESTAMP DEFAULT NOW()  -- Время создания
);

-- Таблица кодов
CREATE TABLE IF NOT EXISTS codes (
    id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(id),  -- Внешний ключ на мероприятие
    code TEXT NOT NULL UNIQUE,  -- Уникальный код
    points INTEGER NOT NULL,    -- Количество баллов
    is_income BOOLEAN NOT NULL, -- Тип операции (пополнение или списание)
    created_at TIMESTAMP DEFAULT NOW()  -- Время создания
);

-- Таблица использованных кодов (привязка кодов к пользователям)
CREATE TABLE IF NOT EXISTS user_codes (
    user_id BIGINT REFERENCES students(id) ON DELETE CASCADE,  -- ID пользователя
    code_id INTEGER REFERENCES codes(id) ON DELETE CASCADE,   -- ID кода
    used_at TIMESTAMP DEFAULT NOW(),  -- Время использования
    PRIMARY KEY (user_id, code_id)  -- Уникальная пара "пользователь-код"
);

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    price_points INTEGER NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    total_points INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS order_items (
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    qty INTEGER NOT NULL,
    points_each INTEGER NOT NULL,
    PRIMARY KEY (order_id, product_id)
);

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

ALTER TABLE products
ADD COLUMN IF NOT EXISTS stock INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS ix_products_active ON products(is_active);

ALTER TABLE codes
ADD COLUMN IF NOT EXISTS starts_at TIMESTAMPTZ NULL,
ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ NULL,
ADD COLUMN IF NOT EXISTS max_uses INTEGER NULL;

CREATE INDEX IF NOT EXISTS ix_codes_code ON codes(code);
CREATE INDEX IF NOT EXISTS ix_codes_window ON codes(starts_at, expires_at);

