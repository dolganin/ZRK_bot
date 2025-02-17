DO $$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'postgres') THEN
        CREATE ROLE postgres WITH LOGIN PASSWORD 'postgres' SUPERUSER;
    END IF;

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
END $$;
CREATE DATABASE career_quest OWNER postgres;

