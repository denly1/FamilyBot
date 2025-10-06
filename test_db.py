import asyncio
import asyncpg
from dotenv import load_dotenv
import os

async def test_db_connection():
    load_dotenv()
    
    db_config = {
        'host': os.getenv("DB_HOST", "127.0.0.1"),
        'port': int(os.getenv("DB_PORT", "5432")),
        'database': os.getenv("DB_NAME", "FamilyDB"),
        'user': os.getenv("DB_USER", "postgres"),
        'password': os.getenv("DB_PASSWORD", "1")
    }
    
    try:
        print("Попытка подключения к базе данных...")
        print(f"Параметры подключения: {db_config['host']}:{db_config['port']}/{db_config['database']}")
        
        # Подключаемся к базе данных
        conn = await asyncpg.connect(**db_config)
        
        # Получаем название текущей базы данных
        db_name = await conn.fetchval('SELECT current_database()')
        print(f"✅ Успешное подключение к базе данных: {db_name}")
        
        # Получаем версию PostgreSQL
        version = await conn.fetchval('SELECT version()')
        print(f"ℹ️ Версия PostgreSQL: {version.split(',')[0]}")
        
        # Получаем список таблиц
        tables = await conn.fetch('''
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        ''')
        
        print("\nСписок таблиц в базе данных:")
        for i, table in enumerate(tables, 1):
            print(f"{i}. {table['table_name']}")
        
        # Проверяем таблицу users
        try:
            users_count = await conn.fetchval('SELECT COUNT(*) FROM users')
            print(f"\nВсего пользователей в базе: {users_count}")
        except Exception as e:
            print(f"\n⚠️ Ошибка при доступе к таблице users: {e}")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка подключения к базе данных: {e}")
        print("\nПроверьте следующее:")
        print("1. Запущен ли PostgreSQL сервер")
        print("2. Правильность параметров подключения в .env файле")
        print("3. Доступность базы данных с указанными учетными данными")
        print("4. Разрешен ли доступ к базе с вашего IP (проверьте pg_hba.conf)")

if __name__ == "__main__":
    asyncio.run(test_db_connection())
