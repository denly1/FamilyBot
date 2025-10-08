#!/usr/bin/env python3
"""
Полная очистка для тестирования регистрации
"""

import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from db import create_pool

async def clear_all():
    print("=== ПОЛНАЯ ОЧИСТКА ===")
    
    # Загружаем .env
    load_dotenv()
    
    try:
        # Подключаемся к БД
        pool = await create_pool()
        print("✅ Подключились к БД")
        
        # Удаляем всех пользователей
        async with pool.acquire() as conn:
            result = await conn.execute("DELETE FROM users;")
            print(f"✅ Удалены пользователи из БД: {result}")
        
        # Удаляем кеш файлы
        cache_files = [
            "data/bot_data.pkl",
            "bot_data.pkl",
            Path(__file__).parent / "data" / "bot_data.pkl",
            Path(__file__).parent / "bot_data.pkl"
        ]
        
        for cache_file in cache_files:
            try:
                if isinstance(cache_file, str):
                    cache_file = Path(cache_file)
                if cache_file.exists():
                    cache_file.unlink()
                    print(f"✅ Удален кеш: {cache_file}")
            except Exception as e:
                print(f"⚠️ Не удалось удалить {cache_file}: {e}")
        
        await pool.close()
        print("✅ Полная очистка завершена")
        
        print("\n🚀 Теперь запустите бота:")
        print("python3 bot.py")
        
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(clear_all())
