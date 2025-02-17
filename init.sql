DO $$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'postgres') THEN
        CREATE ROLE postgres WITH LOGIN PASSWORD 'postgres' SUPERUSER;
    END IF;
END $$;
CREATE DATABASE career_quest OWNER postgres;