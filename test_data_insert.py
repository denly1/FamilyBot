import asyncio
import asyncpg
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

async def test_data_insertion():
    load_dotenv()
    
    db_config = {
        'host': os.getenv("DB_HOST", "localhost"),
        'port': int(os.getenv("DB_PORT", "5432")),
        'database': os.getenv("DB_NAME", "FamilyDB"),
        'user': os.getenv("DB_USER", "postgres"),
        'password': os.getenv("DB_PASSWORD", "1")
    }
    
    try:
        print("🧪 Тестирование вставки данных...")
        conn = await asyncpg.connect(**db_config)
        
        # Тест добавления пользователя
        test_user = {
            'tg_id': 123456789,
            'name': 'Тестовый Пользователь',
            'username': 'testuser'
        }
        
        await conn.execute('''
            INSERT INTO users (tg_id, name, username, created_at, updated_at)
            VALUES ($1, $2, $3, NOW(), NOW())
            ON CONFLICT (tg_id) DO UPDATE
            SET name = EXCLUDED.name,
                username = EXCLUDED.username,
                updated_at = NOW()
        ''', test_user['tg_id'], test_user['name'], test_user['username'])
        
        print(f"✅ Добавлен/обновлен пользователь: {test_user['name']} (@{test_user['username']})")
        
        # Тест добавления афиши
        test_poster = {
            'file_id': 'test_file_id_123',
            'caption': 'Тестовая афиша',
            'ticket_url': 'https://example.com/tickets/123',
            'is_active': True
        }
        
        poster_id = await conn.fetchval('''
            INSERT INTO posters (file_id, caption, ticket_url, is_active, created_at)
            VALUES ($1, $2, $3, $4, NOW())
            RETURNING id
        ''', test_poster['file_id'], test_poster['caption'], 
            test_poster['ticket_url'], test_poster['is_active'])
        
        print(f"✅ Добавлена афиша #{poster_id}: {test_poster['caption']}")
        
        # Тест добавления записи о посещении
        await conn.execute('''
            INSERT INTO attendances (user_id, poster_id, status, created_at, updated_at)
            VALUES ($1, $2, 'registered', NOW(), NOW())
            ON CONFLICT (user_id, poster_id) DO UPDATE
            SET status = EXCLUDED.status,
                updated_at = NOW()
        ''', test_user['tg_id'], poster_id)
        
        print(f"✅ Запись о посещении добавлена для пользователя {test_user['tg_id']} и афиши {poster_id}")
        
        # Проверяем, что данные сохранились
        user_count = await conn.fetchval('SELECT COUNT(*) FROM users')
        posters_count = await conn.fetchval('SELECT COUNT(*) FROM posters')
        attendances_count = await conn.fetchval('SELECT COUNT(*) FROM attendances')
        
        print("\n📊 Текущая статистика:")
        print(f"- Всего пользователей: {user_count}")
        print(f"- Всего афиш: {posters_count}")
        print(f"- Всего записей о посещениях: {attendances_count}")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка при работе с базой данных: {e}")

if __name__ == "__main__":
    asyncio.run(test_data_insertion())
