-- Создание таблицы студентов
CREATE TABLE IF NOT EXISTS students (
    id BIGINT PRIMARY KEY,  -- Telegram ID студента
    name TEXT NOT NULL,     -- Имя студента
    balance INTEGER DEFAULT 0,  -- Баланс студента
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- Время регистрации
);

-- Создание таблицы admins
CREATE TABLE IF NOT EXISTS admins (
    id SERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE NOT NULL
);

-- Создание таблицы merch
CREATE TABLE IF NOT EXISTS merch (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    cost INTEGER NOT NULL,
    used BOOLEAN DEFAULT FALSE
);

CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE codes (
    id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(id),
    code TEXT NOT NULL UNIQUE,
    points INTEGER NOT NULL,
    is_income BOOLEAN NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);