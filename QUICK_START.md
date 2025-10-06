# 🚀 Быстрый старт TusaBot

## ✅ Что изменилось:

1. **Удален Supabase** - теперь все данные в PostgreSQL
2. **Создан API Backend** - FastAPI для подключения веб-приложения
3. **Афиши в БД** - автоматическая синхронизация Бот → БД → Веб-приложение
4. **Возраст 16+** - обновлено ограничение возраста

---

## 📦 Установка зависимостей:

```bash
# Python пакеты
pip install -r requirements.txt

# Node.js пакеты (для веб-приложения)
cd project
npm install
cd ..
```

---

## 🗄️ Настройка базы данных:

### Вариант 1: Автоматическая (рекомендуется)
Просто запустите бота - он создаст все таблицы автоматически:
```bash
python bot.py
```

### Вариант 2: Вручную через SQL
Выполните ваш SQL скрипт в pgAdmin или psql для создания таблиц `users`, `posters`, `attendances`.

---

## ⚙️ Настройка переменных окружения:

Создайте файл `.env` в корне проекта:

```env
# Telegram Bot
BOT_TOKEN=ваш_токен_бота
ADMIN_USER_ID=ваш_telegram_id
CHANNEL_USERNAME=@largentmsk
CHANNEL_USERNAME_2=@idnrecords

# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=FamilyDB
DB_USER=postgres
DB_PASSWORD=1

# VK (опционально)
VK_TOKEN=
VK_GROUP_DOMAIN=largent.tusa

# Еженедельная рассылка
WEEKLY_DAY=4
WEEKLY_HOUR=12
WEEKLY_MINUTE=0
```

---

## 🎯 Запуск системы:

### 1️⃣ Запустить API Backend:
```bash
python api.py
```
✅ API доступен на `http://localhost:8000`

### 2️⃣ Запустить Telegram Bot (в другом терминале):
```bash
python bot.py
```
✅ Бот запущен и готов принимать команды

### 3️⃣ Запустить веб-приложение (в третьем терминале):
```bash
cd project
npm run dev
```
✅ Приложение доступно на `http://localhost:5173`

---

## 🎉 Как это работает:

### **Создание афиши:**

1. **В Telegram боте:**
   - Откройте `/admin` или `/menu`
   - Нажмите "🛠 Админ-панель"
   - Нажмите "🧩 Создать афишу"
   - Загрузите фото
   - Введите описание
   - Введите ссылку на билеты
   - Подтвердите

2. **Что происходит:**
   ```
   Бот → Сохраняет в PostgreSQL (таблица posters)
         ↓
   API Backend → Читает из БД
         ↓
   Веб-приложение → Получает через API
         ↓
   Пользователи видят афишу
   ```

3. **Результат:**
   - ✅ Афиша видна в боте (команда `/menu`)
   - ✅ Афиша видна в веб-приложении
   - ✅ Афиша доступна через API `/posters/latest`

---

## 🔍 Проверка работы:

### Проверить API:
```bash
# Открыть в браузере
http://localhost:8000

# Получить последнюю афишу
http://localhost:8000/posters/latest

# Получить все афиши
http://localhost:8000/posters

# Проверить здоровье
http://localhost:8000/health
```

### Проверить веб-приложение:
```bash
# Открыть в браузере
http://localhost:5173
```

### Проверить бота:
```
/start - начать работу
/menu - главное меню
/admin - админ-панель (только для админов)
```

---

## 📱 Подключение мини-приложения к Telegram:

### Шаг 1: Деплой веб-приложения
Разместите веб-приложение на хостинге (Vercel, Netlify, или свой сервер):
```bash
cd project
npm run build
# Загрузите содержимое папки dist/ на хостинг
```

### Шаг 2: Деплой API Backend
Разместите API на сервере (Railway, Render, или VPS):
```bash
# На сервере
python api.py
```

### Шаг 3: Настроить в боте
Обновите URL в команде `/app` в `bot.py`:
```python
web_app_url = "https://your-domain.com"  # Ваш URL
```

### Шаг 4: Настроить в веб-приложении
Создайте `project/.env.production`:
```env
VITE_API_URL=https://your-api-domain.com
```

---

## 🐛 Решение проблем:

### Проблема: API не запускается
```bash
# Проверьте что PostgreSQL запущен
# Проверьте настройки в .env
# Проверьте логи: python api.py
```

### Проблема: Бот не сохраняет афиши
```bash
# Проверьте подключение к БД
# Проверьте логи бота
# Убедитесь что таблица posters создана
```

### Проблема: Веб-приложение не показывает афиши
```bash
# Проверьте что API запущен
# Откройте консоль браузера (F12)
# Проверьте URL API в project/.env
```

---

## 📊 Структура БД:

```sql
users (
  tg_id BIGINT PRIMARY KEY,
  name TEXT,
  gender TEXT,
  age INTEGER (16-100),
  vk_id TEXT,
  username TEXT,
  registered_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)

posters (
  id SERIAL PRIMARY KEY,
  file_id TEXT,
  caption TEXT,
  ticket_url TEXT,
  created_at TIMESTAMPTZ,
  is_active BOOLEAN
)

attendances (
  id SERIAL PRIMARY KEY,
  user_id BIGINT → users(tg_id),
  poster_id INTEGER → posters(id),
  attended_at TIMESTAMPTZ,
  UNIQUE(user_id, poster_id)
)
```

---

## 🎊 Готово!

Теперь у вас полностью работающая система:
- ✅ Telegram Bot с админ-панелью
- ✅ PostgreSQL база данных
- ✅ REST API для веб-приложения
- ✅ React веб-приложение
- ✅ Автоматическая синхронизация данных

**Создайте первую афишу и проверьте что она появилась везде!** 🚀
