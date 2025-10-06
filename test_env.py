import os
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()

# Проверяем BOT_TOKEN
bot_token = os.getenv("BOT_TOKEN", "")

print(f"BOT_TOKEN найден: {'ДА' if bot_token else 'НЕТ'}")
print(f"Длина токена: {len(bot_token)}")
print(f"Первые 10 символов: {bot_token[:10] if bot_token else 'ПУСТО'}")

if not bot_token:
    print("\n❌ BOT_TOKEN не загружен!")
    print("Проверьте:")
    print("1. Файл .env в корне проекта")
    print("2. Строка BOT_TOKEN=... без пробелов")
    print("3. Нет опечаток в названии")
else:
    print("\n✅ BOT_TOKEN загружен успешно!")
