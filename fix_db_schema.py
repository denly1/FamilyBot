import asyncio
import asyncpg
from dotenv import load_dotenv
import os

async def fix_database_schema():
    load_dotenv()
    
    db_config = {
        'host': os.getenv("DB_HOST", "localhost"),
        'port': int(os.getenv("DB_PORT", "5432")),
        'database': os.getenv("DB_NAME", "FamilyDB"),
        'user': os.getenv("DB_USER", "postgres"),
        'password': os.getenv("DB_PASSWORD", "1")
    }
    
    try:
        print("🔧 Проверка и обновление структуры базы данных...")
        conn = await asyncpg.connect(**db_config)
        
        # Создаем таблицы, если они не существуют
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            tg_id BIGINT PRIMARY KEY,
            name TEXT,
            gender TEXT CHECK (gender IN ('male', 'female')),
            age INTEGER CHECK (age >= 14 AND age <= 100),
            vk_id TEXT,
            username TEXT,
            registered_at TIMESTAMPTZ DEFAULT now(),
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        );
        
        CREATE TABLE IF NOT EXISTS posters (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            event_date TIMESTAMPTZ,
            location TEXT,
            image_url TEXT,
            ticket_url TEXT,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        );
        
        CREATE TABLE IF NOT EXISTS attendances (
            id SERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(tg_id) ON DELETE CASCADE,
            poster_id INTEGER REFERENCES posters(id) ON DELETE CASCADE,
            status TEXT DEFAULT 'registered',
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now(),
            UNIQUE(user_id, poster_id)
        );
        
        -- Создаем функцию для автоматического обновления updated_at
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        
        -- Создаем триггеры для автоматического обновления updated_at
        DROP TRIGGER IF EXISTS update_users_updated_at ON users;
        CREATE TRIGGER update_users_updated_at
        BEFORE UPDATE ON users
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        
        DROP TRIGGER IF EXISTS update_posters_updated_at ON posters;
        CREATE TRIGGER update_posters_updated_at
        BEFORE UPDATE ON posters
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        
        DROP TRIGGER IF EXISTS update_attendances_updated_at ON attendances;
        CREATE TRIGGER update_attendances_updated_at
        BEFORE UPDATE ON attendances
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        ''')
        
        print("✅ Структура базы данных успешно обновлена!")
        
        # Проверяем наличие необходимых столбцов в таблице posters
        columns = await conn.fetch('''
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'posters'
        ''')
        
        print("\nСтруктура таблицы posters:")
        for col in columns:
            print(f"- {col['column_name']} ({col['data_type']})")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка при обновлении структуры базы данных: {e}")

if __name__ == "__main__":
    asyncio.run(fix_database_schema())
