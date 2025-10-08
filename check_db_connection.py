#!/usr/bin/env python3
"""
Скрипт проверки подключения к базе данных
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "FamilyDB")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "1")

print("=" * 60)
print("🔍 ПРОВЕРКА ПОДКЛЮЧЕНИЯ К БАЗЕ ДАННЫХ")
print("=" * 60)
print(f"Host: {DB_HOST}")
print(f"Port: {DB_PORT}")
print(f"Database: {DB_NAME}")
print(f"User: {DB_USER}")
print(f"Password: {'*' * len(DB_PASSWORD)}")
print("=" * 60)
print()

async def check_connection():
    """Проверить подключение к БД"""
    try:
        print("⏳ Попытка подключения...")
        
        # Подключаемся к БД
        conn = await asyncpg.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        
        print("✅ Подключение успешно!\n")
        
        # Проверяем версию PostgreSQL
        version = await conn.fetchval("SELECT version();")
        print(f"📊 PostgreSQL версия:")
        print(f"   {version}\n")
        
        # Проверяем существующие таблицы
        tables = await conn.fetch("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """)
        
        print(f"📋 Таблицы в БД ({len(tables)}):")
        for table in tables:
            print(f"   • {table['tablename']}")
        print()
        
        # Проверяем количество записей
        print("📊 Количество записей:")
        
        try:
            users_count = await conn.fetchval("SELECT COUNT(*) FROM users;")
            print(f"   • Пользователей: {users_count}")
        except Exception as e:
            print(f"   • Пользователей: ❌ Ошибка ({e})")
        
        try:
            posters_count = await conn.fetchval("SELECT COUNT(*) FROM posters;")
            print(f"   • Афиш: {posters_count}")
        except Exception as e:
            print(f"   • Афиш: ❌ Ошибка ({e})")
        
        try:
            attendances_count = await conn.fetchval("SELECT COUNT(*) FROM attendances;")
            print(f"   • Посещений: {attendances_count}")
        except Exception as e:
            print(f"   • Посещений: ❌ Ошибка ({e})")
        
        print()
        
        # Проверяем структуру таблицы users
        print("🔍 Структура таблицы 'users':")
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'users'
            ORDER BY ordinal_position;
        """)
        
        if columns:
            for col in columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                print(f"   • {col['column_name']}: {col['data_type']} ({nullable})")
        else:
            print("   ⚠️ Таблица 'users' не найдена!")
        
        await conn.close()
        print("\n✅ Проверка завершена успешно!")
        
    except asyncpg.exceptions.InvalidPasswordError:
        print("❌ ОШИБКА: Неверный пароль!")
        print("\n💡 Решение:")
        print("   1. Проверьте пароль в файле .env")
        print("   2. Или попробуйте подключиться без пароля:")
        print("      sudo -u postgres psql -d FamilyDB")
        
    except asyncpg.exceptions.InvalidCatalogNameError:
        print(f"❌ ОШИБКА: База данных '{DB_NAME}' не существует!")
        print("\n💡 Решение:")
        print(f"   1. Создайте БД: sudo -u postgres createdb {DB_NAME}")
        print("   2. Или проверьте название в .env")
        
    except Exception as e:
        print(f"❌ ОШИБКА: {type(e).__name__}")
        print(f"   {e}")
        print("\n💡 Решение:")
        print("   1. Проверьте что PostgreSQL запущен: systemctl status postgresql")
        print("   2. Проверьте настройки в .env")
        print("   3. Проверьте pg_hba.conf для аутентификации")


if __name__ == "__main__":
    asyncio.run(check_connection())

