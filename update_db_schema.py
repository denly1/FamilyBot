import asyncio
import asyncpg
from dotenv import load_dotenv
import os

async def update_database_schema():
    load_dotenv()
    
    db_config = {
        'host': os.getenv("DB_HOST", "localhost"),
        'port': int(os.getenv("DB_PORT", "5432")),
        'database': os.getenv("DB_NAME", "FamilyDB"),
        'user': os.getenv("DB_USER", "postgres"),
        'password': os.getenv("DB_PASSWORD", "1")
    }
    
    try:
        print("🔄 Обновление структуры базы данных...")
        conn = await asyncpg.connect(**db_config)
        
        # Добавляем недостающие колонки в таблицу users
        await conn.execute('''
            -- Добавляем колонку username, если её нет
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS username TEXT;
            
            -- Добавляем ограничение для поля gender, если его нет
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'users_gender_check'
                ) THEN
                    ALTER TABLE users 
                    ADD CONSTRAINT users_gender_check 
                    CHECK (gender IN ('male', 'female'));
                END IF;
            END $$;
            
            -- Добавляем ограничение для поля age, если его нет
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'users_age_check'
                ) THEN
                    ALTER TABLE users 
                    ADD CONSTRAINT users_age_check 
                    CHECK (age >= 14 AND age <= 100);
                END IF;
            END $$;
            
            -- Обновляем значения по умолчанию для временных меток
            ALTER TABLE users 
            ALTER COLUMN created_at SET DEFAULT now(),
            ALTER COLUMN updated_at SET DEFAULT now(),
            ALTER COLUMN registered_at SET DEFAULT now();
        ''')
        
        # Проверяем и обновляем таблицу posters
        await conn.execute('''
            -- Создаем таблицу posters, если её нет
            CREATE TABLE IF NOT EXISTS posters (
                id SERIAL PRIMARY KEY,
                file_id TEXT NOT NULL,
                caption TEXT,
                ticket_url TEXT,
                created_at TIMESTAMPTZ DEFAULT now(),
                is_active BOOLEAN DEFAULT true
            );
        ''')
        
        # Проверяем и обновляем таблицу attendances
        await conn.execute('''
            -- Создаем таблицу attendances, если её нет
            CREATE TABLE IF NOT EXISTS attendances (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(tg_id) ON DELETE CASCADE,
                poster_id INTEGER REFERENCES posters(id) ON DELETE CASCADE,
                attended_at TIMESTAMPTZ DEFAULT now(),
                UNIQUE(user_id, poster_id)
            );
        ''')
        
        # Создаем или обновляем функцию для обновления updated_at
        await conn.execute('''
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = now();
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            
            -- Создаем или обновляем триггер для users
            DROP TRIGGER IF EXISTS update_users_updated_at ON users;
            CREATE TRIGGER update_users_updated_at
            BEFORE UPDATE ON users
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        ''')
        
        print("✅ Структура базы данных успешно обновлена!")
        
        # Выводим информацию о таблицах
        tables = await conn.fetch('''
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        ''')
        
        print("\nДоступные таблицы в базе данных:")
        for table in tables:
            count = await conn.fetchval(f'SELECT COUNT(*) FROM {table["table_name"]}')
            print(f"- {table['table_name']}: {count} записей")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка при обновлении структуры базы данных: {e}")

if __name__ == "__main__":
    print("🔄 Запуск обновления структуры базы данных...")
    asyncio.run(update_database_schema())
