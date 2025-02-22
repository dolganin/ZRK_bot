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
