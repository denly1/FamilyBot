-- Миграция 001: Начальная схема базы данных

CREATE TABLE IF NOT EXISTS users (
    tg_id BIGINT PRIMARY KEY,
    name TEXT,
    gender TEXT CHECK (gender IN ('male', 'female')),
    age INTEGER CHECK (age >= 16 AND age <= 100),
    vk_id TEXT,
    registered_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_users_vk_id ON users(vk_id);
CREATE INDEX IF NOT EXISTS idx_users_registered_at ON users(registered_at);

CREATE TABLE IF NOT EXISTS posters (
    id SERIAL PRIMARY KEY,
    file_id TEXT NOT NULL,
    caption TEXT,
    ticket_url TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    is_active BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS attendances (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(tg_id) ON DELETE CASCADE,
    poster_id INTEGER REFERENCES posters(id) ON DELETE CASCADE,
    attended_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, poster_id)
);

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at 
BEFORE UPDATE ON users 
FOR EACH ROW 
EXECUTE FUNCTION update_updated_at_column();

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO tusabot;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO tusabot;