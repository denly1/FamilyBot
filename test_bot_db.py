import asyncio
import asyncpg
from dotenv import load_dotenv
import os

async def test_bot_database():
    load_dotenv()
    
    db_config = {
        'host': os.getenv("DB_HOST", "localhost"),
        'port': int(os.getenv("DB_PORT", "5432")),
        'database': os.getenv("DB_NAME", "FamilyDB"),
        'user': os.getenv("DB_USER", "postgres"),
        'password': os.getenv("DB_PASSWORD", "1")
    }
    
    try:
        print("🔍 Тестирование работы базы данных бота...")
        conn = await asyncpg.connect(**db_config)
        
        # Тестовые данные пользователя
        test_user = {
            'tg_id': 123456789,
            'name': 'Тестовый Пользователь',
            'username': 'testuser',
            'gender': 'male',
            'age': 25,
            'vk_id': 'id12345678'
        }
        
        # Вставляем тестового пользователя
        await conn.execute('''
            INSERT INTO users (tg_id, name, username, gender, age, vk_id)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (tg_id) 
            DO UPDATE SET 
                name = EXCLUDED.name,
                username = EXCLUDED.username,
                gender = EXCLUDED.gender,
                age = EXCLUDED.age,
                vk_id = EXCLUDED.vk_id,
                updated_at = NOW()
        ''', 
        test_user['tg_id'],
        test_user['name'],
        test_user['username'],
        test_user['gender'],
        test_user['age'],
        test_user['vk_id'])
        
        print(f"✅ Тестовый пользователь добавлен/обновлен: {test_user['name']} (@{test_user['username']})")
        
        # Получаем данные пользователя
        user = await conn.fetchrow(
            'SELECT * FROM users WHERE tg_id = $1', 
            test_user['tg_id']
        )
        
        print("\n📋 Данные пользователя из базы:")
        for key, value in dict(user).items():
            print(f"- {key}: {value}")
        
        # Тестируем обновление данных
        await conn.execute('''
            UPDATE users 
            SET age = 26, updated_at = NOW()
            WHERE tg_id = $1
        ''', test_user['tg_id'])
        
        print("\n🔄 Возраст пользователя обновлен до 26")
        
        # Проверяем триггер обновления updated_at
        user = await conn.fetchrow(
            'SELECT * FROM users WHERE tg_id = $1', 
            test_user['tg_id']
        )
        print(f"🕒 Время последнего обновления: {user['updated_at']}")
        
        # Тестируем вставку афиши
        poster = await conn.fetchrow('''
            INSERT INTO posters (file_id, caption, ticket_url, is_active)
            VALUES ($1, $2, $3, $4)
            RETURNING *
        ''', 
        'test_file_id_123',
        'Тестовое мероприятие',
        'https://example.com/tickets/123',
        True)
        
        print(f"\n🎭 Добавлена тестовая афиша: {poster['caption']} (ID: {poster['id']})")
        
        # Тестируем отметку о посещении
        attendance = await conn.fetchrow('''
            INSERT INTO attendances (user_id, poster_id, attended_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (user_id, poster_id) 
            DO UPDATE SET attended_at = NOW()
            RETURNING *
        ''', test_user['tg_id'], poster['id'])
        
        print(f"✅ Пользователь отмечен на мероприятии: {attendance['attended_at']}")
        
        # Получаем статистику
        users_count = await conn.fetchval('SELECT COUNT(*) FROM users')
        posters_count = await conn.fetchval('SELECT COUNT(*) FROM posters')
        attendances_count = await conn.fetchval('SELECT COUNT(*) FROM attendances')
        
        print("\n📊 Текущая статистика базы данных:")
        print(f"- Всего пользователей: {users_count}")
        print(f"- Всего афиш: {posters_count}")
        print(f"- Всего отметок о посещении: {attendances_count}")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании базы данных: {e}")

if __name__ == "__main__":
    print("🚀 Запуск теста работы базы данных бота...")
    asyncio.run(test_bot_database())
