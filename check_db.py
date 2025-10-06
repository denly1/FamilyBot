import asyncio
import asyncpg
from dotenv import load_dotenv
import os

async def check_database():
    load_dotenv()
    
    db_config = {
        'host': os.getenv("DB_HOST", "localhost"),
        'port': int(os.getenv("DB_PORT", "5432")),
        'database': os.getenv("DB_NAME", "FamilyDB"),
        'user': os.getenv("DB_USER", "postgres"),
        'password': os.getenv("DB_PASSWORD", "1")
    }
    
    try:
        print("🔍 Проверка подключения к базе данных...")
        print(f"📡 Параметры подключения: {db_config['user']}@**:***@{db_config['host']}:{db_config['port']}/{db_config['database']}")
        
        # Подключаемся к базе данных
        conn = await asyncpg.connect(**db_config)
        
        # Получаем информацию о базе данных
        db_name = await conn.fetchval('SELECT current_database()')
        db_user = await conn.fetchval('SELECT current_user')
        db_size = await conn.fetchval("SELECT pg_size_pretty(pg_database_size(current_database()))")
        
        print("\n✅ Подключение успешно установлено!")
        print(f"📊 База данных: {db_name}")
        print(f"👤 Пользователь: {db_user}")
        print(f"📏 Размер БД: {db_size}")
        
        # Получаем список таблиц и количество записей в каждой
        print("\n📋 Список таблиц и количество записей:")
        tables = await conn.fetch('''
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        ''')
        
        for table in tables:
            table_name = table['table_name']
            try:
                count = await conn.fetchval(f'SELECT COUNT(*) FROM "{table_name}"')
                print(f"- {table_name}: {count} записей")
            except Exception as e:
                print(f"- {table_name}: ошибка доступа - {str(e)[:50]}...")
        
        # Проверяем пользователей
        print("\n👥 Проверка таблицы users:")
        try:
            users = await conn.fetch('SELECT * FROM users LIMIT 5')
            if users:
                print(f"Найдено пользователей: {len(users)}")
                for i, user in enumerate(users, 1):
                    print(f"{i}. ID: {user.get('tg_id')}, Имя: {user.get('name')}, VK: {user.get('vk_id')}")
            else:
                print("В таблице users пока нет записей")
        except Exception as e:
            print(f"Ошибка при чтении таблицы users: {e}")
        
        # Проверяем афиши
        print("\n🎭 Проверка таблицы posters:")
        try:
            posters = await conn.fetch('SELECT id, title, created_at FROM posters ORDER BY created_at DESC LIMIT 3')
            if posters:
                print(f"Найдено афиш: {len(posters)}")
                for poster in posters:
                    print(f"- {poster['id']}: {poster['title']} ({poster['created_at'].strftime('%d.%m.%Y')})")
            else:
                print("В таблице posters пока нет записей")
        except Exception as e:
            print(f"Ошибка при чтении таблицы posters: {e}")
        
        await conn.close()
        
    except Exception as e:
        print(f"\n❌ Ошибка подключения к базе данных: {e}")
        print("\nВозможные причины:")
        print("1. Сервер PostgreSQL не запущен")
        print("2. Неправильные учетные данные в .env файле")
        print("3. Пользователь не имеет прав на подключение")
        print("4. Проблемы с сетевыми настройками (если не localhost)")
        print("\nПроверьте логи PostgreSQL для более подробной информации.")

if __name__ == "__main__":
    print("🔍 Запуск проверки базы данных...")
    asyncio.run(check_database())
