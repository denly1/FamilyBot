#!/usr/bin/env python3
"""
Простой тест подключения к БД и проверка пользователя
"""

import asyncio
import os
from dotenv import load_dotenv
from db import create_pool, get_user

async def test_db():
    print("=== ТЕСТ БД ===")
    
    # Загружаем .env
    load_dotenv()
    
    # Показываем настройки БД
    print(f"DB_HOST: {os.getenv('DB_HOST', 'localhost')}")
    print(f"DB_PORT: {os.getenv('DB_PORT', '5432')}")
    print(f"DB_NAME: {os.getenv('DB_NAME', 'FamilyDB')}")
    print(f"DB_USER: {os.getenv('DB_USER', 'postgres')}")
    print(f"DB_PASSWORD: {'*' * len(os.getenv('DB_PASSWORD', ''))}")
    
    try:
        # Создаем пул подключений
        print("\n1. Создаем пул подключений...")
        pool = await create_pool()
        print("✅ Пул создан успешно")
        
        # Проверяем подключение
        print("\n2. Проверяем подключение...")
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            print(f"✅ Подключение работает: {result}")
        
        # Проверяем таблицы
        print("\n3. Проверяем таблицы...")
        async with pool.acquire() as conn:
            tables = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            print(f"✅ Найдено таблиц: {len(tables)}")
            for table in tables:
                print(f"   - {table['tablename']}")
        
        # Проверяем пользователя 825042510
        print(f"\n4. Ищем пользователя 825042510...")
        user = await get_user(pool, 825042510)
        if user:
            print(f"❌ Пользователь НАЙДЕН в БД: {user}")
            print("   Это может быть причиной проблемы!")
        else:
            print("✅ Пользователь НЕ найден в БД")
        
        # Показываем всех пользователей
        print(f"\n5. Все пользователи в БД:")
        async with pool.acquire() as conn:
            users = await conn.fetch("SELECT tg_id, name, gender, age FROM users LIMIT 10")
            if users:
                for u in users:
                    print(f"   - ID: {u['tg_id']}, Name: {u['name']}, Gender: {u['gender']}, Age: {u['age']}")
            else:
                print("   Пользователей нет")
        
        await pool.close()
        print("\n✅ Тест завершен успешно")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_db())
