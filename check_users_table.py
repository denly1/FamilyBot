import asyncio
import asyncpg
from dotenv import load_dotenv
import os

async def check_users_table():
    load_dotenv()
    
    db_config = {
        'host': os.getenv("DB_HOST", "localhost"),
        'port': int(os.getenv("DB_PORT", "5432")),
        'database': os.getenv("DB_NAME", "FamilyDB"),
        'user': os.getenv("DB_USER", "postgres"),
        'password': os.getenv("DB_PASSWORD", "1")
    }
    
    try:
        print("🔍 Проверка структуры таблицы users...")
        conn = await asyncpg.connect(**db_config)
        
        # Получаем информацию о колонках таблицы users
        columns = await conn.fetch('''
            SELECT column_name, data_type, is_nullable, column_default 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            ORDER BY ordinal_position
        ''')
        
        print("\nСтруктура таблицы users:")
        for col in columns:
            print(f"- {col['column_name']} ({col['data_type']}) {'NOT NULL' if col['is_nullable'] == 'NO' else 'NULL'} {f'DEFAULT {col['column_default']}' if col['column_default'] else ''}")
        
        # Проверяем, существует ли колонка username
        has_username = any(col['column_name'] == 'username' for col in columns)
        print(f"\nКолонка 'username' существует: {'✅ Да' if has_username else '❌ Нет'}")
        
        if not has_username:
            print("\nДобавляем колонку 'username'...")
            await conn.execute('''
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS username TEXT
            ''')
            print("✅ Колонка 'username' успешно добавлена")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(check_users_table())
