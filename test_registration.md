# 🔧 Полная диагностика регистрации

## Шаг 1: Очистка на сервере

```bash
# Остановить бота
pkill -f bot.py

# Удалить кеш файлы
rm -f data/bot_data.pkl
rm -f bot_data.pkl

# Удалить пользователя из БД
sudo -u postgres psql -d familydb -c "DELETE FROM users WHERE tg_id = 825042510;"

# Проверить что удален
sudo -u postgres psql -d familydb -c "SELECT * FROM users WHERE tg_id = 825042510;"
```

## Шаг 2: Запуск с логами

```bash
# Запустить бота с полным логированием
python3 bot.py 2>&1 | tee bot.log
```

## Шаг 3: Тестирование

1. Напишите боту `/start`
2. Посмотрите в логи - должно быть:

```
=== START COMMAND DEBUG ===
User ID: 825042510
DB Pool exists: True
user_data.registered: False
user_data.name: None
user_data.gender: None
user_data.age: None
is_registered: False
has_partial_data: False
=== END DEBUG ===
```

3. Если видите эти логи, то должно появиться сообщение регистрации:
   "🎉 Добро пожаловать на наши вечеринки! Как вас зовут?"

## Шаг 4: Если не работает

Проверьте:

1. **Подключение к БД:**
```bash
grep DB_ .env
```

2. **Права доступа к БД:**
```bash
sudo -u postgres psql -d familydb -c "\dt"
```

3. **Логи бота:**
```bash
tail -f bot.log | grep -E "(DEBUG|ERROR|WARNING)"
```

## Ожидаемое поведение:

- **Если пользователя НЕТ в БД** → Показать регистрацию
- **Если пользователь ЕСТЬ в БД с полными данными** → Показать меню  
- **Если пользователь ЕСТЬ в БД с неполными данными** → Продолжить регистрацию

---

## 🚨 Если проблема остается

Значит проблема в одном из мест:
1. Кеш `bot_data.pkl` не удаляется
2. БД подключение не работает
3. `load_user_data_from_db` работает неправильно

Тогда нужно смотреть логи!
