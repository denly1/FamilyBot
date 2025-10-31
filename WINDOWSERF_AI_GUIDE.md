# 🤖 ПОЛНАЯ ДОКУМЕНТАЦИЯ ДЛЯ WINDOWSERF AI - TusaBot Project

## 📋 ОБЩАЯ ИНФОРМАЦИЯ О ПРОЕКТЕ

**TusaBot** - это комплексная система для управления вечеринками и мероприятиями, состоящая из:
1. **Telegram бот** (`bot.py`) - основной интерфейс для пользователей и админов
2. **FastAPI бэкенд** (`api.py`) - REST API для веб-приложения
3. **React мини-приложение** (`project/`) - веб-интерфейс для просмотра афиш
4. **PostgreSQL база данных** - хранение всех данных
5. **Nginx** - веб-сервер и reverse proxy

---

## 🏗️ АРХИТЕКТУРА СИСТЕМЫ

```
┌─────────────────┐
│  Telegram Bot   │ (bot.py) - Основной бот для регистрации, рассылок, админки
└────────┬────────┘
         │
         ├─────────────────┐
         │                 │
┌────────▼────────┐  ┌─────▼──────┐
│   PostgreSQL    │  │  FastAPI   │ (api.py) - REST API для веб-приложения
│    Database     │  │   Backend  │
└─────────────────┘  └─────┬───────┘
                          │
                   ┌──────▼──────┐
                   │   React     │ (project/) - Мини-приложение
                   │   Mini-App  │
                   └──────┬──────┘
                          │
                   ┌──────▼──────┐
                   │    Nginx     │ - Reverse proxy и статика
                   └─────────────┘
```

---

## 📁 СТРУКТУРА ПРОЕКТА

```
TusaBot — копия (2)/
├── bot.py                    # Основной Telegram бот
├── api.py                    # FastAPI бэкенд
├── db.py                     # Функции работы с БД
├── db_config.py             # Конфигурация БД (deprecated)
├── requirements.txt         # Python зависимости
├── .env                     # Переменные окружения (НЕ коммитить!)
├── clear_all.py             # Скрипт очистки кеша
├── check_db_connection.py   # Проверка подключения к БД
├── test_db_simple.py        # Простые тесты БД
│
├── project/                 # React веб-приложение
│   ├── src/
│   │   ├── App.tsx          # Главный компонент
│   │   ├── components/
│   │   │   ├── EventPoster.tsx
│   │   │   └── Stories.tsx
│   │   └── lib/
│   │       └── api.ts       # API клиент
│   ├── public/              # Статические файлы
│   │   └── posters/         # Сохраненные фото афиш
│   ├── dist/                # Собранное приложение (production)
│   ├── package.json         # Node.js зависимости
│   └── vite.config.ts       # Vite конфигурация
│
├── nginx/                   # Nginx конфигурация
│   └── tusabot.conf
│
├── systemd/                 # Systemd сервисы
│   ├── tusabot.service      # Бот сервис
│   ├── tusabot-api.service  # API сервис
│   └── tusabot-web.service # Веб-сервер сервис
│
└── scripts/                 # Скрипты деплоя
    └── deploy.sh
```

---

## 🔧 ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ (.env)

**ВСЕГДА НЕ КОММИТИТЬ .env В GIT!**

```bash
# Telegram Bot
BOT_TOKEN=your_bot_token_here
ADMIN_USER_ID=123456789
ADMIN_USER_ID_2=987654321
ADMIN_USER_ID_3=111222333

# Telegram каналы и чат
CHANNEL_USERNAME=@mediafamm          # Основной канал
CHANNEL_USERNAME_2=@thefamilymsk    # Второй канал
CHAT_USERNAME=@familyychaat         # Чат/группа

# База данных PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=familydb                    # Имя БД
DB_USER=tusabot                     # ИЛИ postgres (зависит от настройки)
DB_PASSWORD=your_password_here

# Веб-приложение
WEB_APP_URL=https://fammsktusovki.publicvm.com

# Недельная рассылка (опционально)
WEEKLY_DAY=4                        # 0=Пн, 4=Пт
WEEKLY_HOUR=12                      # Час по MSK (UTC+3)
WEEKLY_MINUTE=0

# Прокси (опционально)
PROXY_URL=
```

---

## 🗄️ СТРУКТУРА БАЗЫ ДАННЫХ

### Таблица `users`
```sql
CREATE TABLE users (
    tg_id BIGINT PRIMARY KEY,              -- Telegram ID пользователя
    name TEXT,                              -- Имя пользователя
    gender TEXT CHECK (gender IN ('male', 'female')),  -- Пол
    age INTEGER CHECK (age >= 16 AND age <= 100),      -- Возраст
    vk_id TEXT,                             -- VK ID (deprecated)
    username TEXT,                           -- Telegram username
    registered_at TIMESTAMPTZ DEFAULT now(), -- Дата регистрации
    created_at TIMESTAMPTZ DEFAULT now(),    -- Дата создания записи
    updated_at TIMESTAMPTZ DEFAULT now()     -- Дата обновления
);
```

### Таблица `posters`
```sql
CREATE TABLE posters (
    id SERIAL PRIMARY KEY,                   -- ID афиши
    file_id TEXT NOT NULL,                   -- Telegram file_id ИЛИ путь /posters/photo.jpg
    caption TEXT,                            -- Описание/текст афиши
    ticket_url TEXT,                         -- Ссылка на покупку билетов
    created_at TIMESTAMPTZ DEFAULT now(),     -- Дата создания
    is_active BOOLEAN DEFAULT true           -- Активна ли афиша
);
```

### Таблица `attendances`
```sql
CREATE TABLE attendances (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(tg_id) ON DELETE CASCADE,
    poster_id INTEGER REFERENCES posters(id) ON DELETE CASCADE,
    attended_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, poster_id)               -- Один пользователь = одно посещение
);
```

---

## 📝 ВСЕ СДЕЛАННЫЕ ИЗМЕНЕНИЯ И ФИКСЫ

### ✅ 1. Регистрация пользователей
- **Проблема:** Пользователи видели "нет доступных афиш" вместо регистрации
- **Решение:** 
  - Убрали автоматическое создание пользователя в `/start`
  - Добавили проверку регистрации в `show_main_menu()`
  - Добавили загрузку данных из БД при каждом запуске
  - Временно отключили `PicklePersistence` для отладки

### ✅ 2. Проверка подписок (2 канала + 1 чат)
- **Проблема:** Проверялся только 1 канал
- **Решение:**
  - Функция `is_user_subscribed()` теперь проверяет:
    - `CHANNEL_USERNAME` = @mediafamm (MEDIA FAM)
    - `CHANNEL_USERNAME_2` = @thefamilymsk (THE FAMILY)
    - `CHAT_USERNAME` = @familyychaat (Family Guests)
  - Обновлен вывод в админке с детальной информацией о всех подписках

### ✅ 3. Поиск по username/ID
- **Добавлено:** Кнопка "🔍 Проверка по нику" в админ-панели
- **Функционал:**
  - Поиск по Telegram username (@username)
  - Поиск по Telegram ID (число)
  - Режим непрерывной проверки (можно проверять нескольких пользователей подряд)
  - Показ статуса подписок для всех 3 сущностей

### ✅ 4. Рассылка с кнопками
- **Добавлено:** Поддержка кнопок в текстовых и фото рассылках
- **Формат:**
  ```
  Ваш текст | Текст кнопки | https://ссылка
  ```
- **Пример:**
  ```
  70 % БИЛЕТОВ ПРОДАНО !
  SOLD OUT близко.
  ПРОМОКОД « FAMILY »
  СКИДКА 200 ₽ 👆 | Купить билеты | https://moscow.qtickets.events/190511-arbat-hall-18-oktyabrya
  ```
- **Реализация:** Функции `handle_text()` и `handle_photo()` парсят формат ` | ` и создают `InlineKeyboardButton`

### ✅ 5. Мини-приложение (веб)
- **Проблема:** Кнопка "Купить билет" не была кликабельной
- **Решение:**
  - Добавлены CSS свойства: `z-[9999]`, `pointerEvents: 'auto'`, `touchAction: 'manipulation'`
  - Исправлены swipe handlers (перенесены с основного контейнера на img)
  - Добавлен `onClick` с `e.stopPropagation()` и `window.open()`

### ✅ 6. Stories компонент
- **Исправлено:** Размер текста, выравнивание, отступы в "О НАС" и "МЕДИА STAFF"
- **Изменения:** Уменьшены шрифты, добавлены правильные отступы, центрированы изображения

### ✅ 7. Сохранение фото локально
- **Добавлено:** При создании афиши фото сохраняется в `project/public/posters/`
- **Путь:** `/posters/poster_<timestamp>.jpg`
- **Использование:** Для веб-приложения (мини-приложение), Telegram использует `file_id`

### ✅ 8. Обновление канала
- **Изменено:** `CHANNEL_USERNAME` с `@whatpartyy` на `@mediafamm`

---

## 🖥️ КОМАНДЫ ДЛЯ СЕРВЕРА

### 📍 Расположение проекта
```bash
cd /opt/tusabot
```

### 🔄 Git операции
```bash
# Обновить код с GitHub
cd /opt/tusabot
git stash                              # Сохранить локальные изменения
rm -f project/.env.production          # Удалить конфликтующие файлы
git pull origin main                   # Получить обновления
# Если есть конфликты:
git reset --hard origin/main           # Сбросить все локальные изменения
```

### 🐍 Python окружение
```bash
# Активировать виртуальное окружение
cd /opt/tusabot
source venv/bin/activate

# Если venv нет - создать:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Деактивировать
deactivate
```

### 🗄️ База данных PostgreSQL

#### Подключение к БД
```bash
# Вариант 1: Через postgres пользователя
sudo -u postgres psql -d familydb

# Вариант 2: Через tusabot пользователя (если настроен)
PGPASSWORD=your_password psql -h 127.0.0.1 -U tusabot -d familydb
```

#### Полезные SQL запросы
```sql
-- Показать всех пользователей
SELECT tg_id, name, gender, age, registered_at FROM users ORDER BY registered_at DESC;

-- Показать количество пользователей
SELECT COUNT(*) as total, 
       COUNT(name) as with_name, 
       COUNT(gender) as with_gender, 
       COUNT(age) as with_age 
FROM users;

-- Показать активные афиши
SELECT id, caption, created_at, is_active FROM posters WHERE is_active = true ORDER BY created_at DESC;

-- Показать все афиши
SELECT id, caption, created_at, is_active FROM posters ORDER BY created_at DESC;

-- Удалить всех пользователей
DELETE FROM users;

-- Удалить конкретного пользователя
DELETE FROM users WHERE tg_id = 123456789;

-- Удалить все афиши
DELETE FROM posters;

-- Удалить конкретную афишу
DELETE FROM posters WHERE id = 1;

-- Удалить все посещения
DELETE FROM attendances;

-- Статистика пользователей
SELECT 
    COUNT(*) as total_users,
    COUNT(CASE WHEN gender = 'male' THEN 1 END) as male_users,
    COUNT(CASE WHEN gender = 'female' THEN 1 END) as female_users,
    COUNT(CASE WHEN registered_at >= CURRENT_DATE THEN 1 END) as today_registrations
FROM users;
```

### 🚀 Systemd сервисы

#### Управление ботом
```bash
# Статус
sudo systemctl status tusabot

# Запустить
sudo systemctl start tusabot

# Остановить
sudo systemctl stop tusabot

# Перезапустить
sudo systemctl restart tusabot

# Логи в реальном времени
sudo journalctl -u tusabot -f

# Последние 100 строк логов
sudo journalctl -u tusabot -n 100
```

#### Управление API
```bash
sudo systemctl status tusabot-api
sudo systemctl start tusabot-api
sudo systemctl stop tusabot-api
sudo systemctl restart tusabot-api
sudo journalctl -u tusabot-api -f
```

#### Управление веб-сервером
```bash
sudo systemctl status tusabot-web
sudo systemctl start tusabot-web
sudo systemctl stop tusabot-web
sudo systemctl restart tusabot-web
sudo journalctl -u tusabot-web -f
```

### 🧹 Очистка кеша
```bash
cd /opt/tusabot
source venv/bin/activate

# Удалить кеш бота (PicklePersistence)
rm -f data/bot_data.pkl
rm -f bot_data.pkl

# Очистить старые афиши из папки (вручную)
# ВНИМАНИЕ: Это удалит файлы, а не записи из БД!
rm -f project/public/posters/poster_*.jpg
```

### 🔍 Тестирование

#### Проверка подключения к БД
```bash
cd /opt/tusabot
source venv/bin/activate
python check_db_connection.py
```

#### Запуск бота вручную (для отладки)
```bash
cd /opt/tusabot
source venv/bin/activate
python bot.py 2>&1 | tee bot_debug.log
```

#### Запуск API вручную
```bash
cd /opt/tusabot
source venv/bin/activate
python api.py
# ИЛИ
uvicorn api:app --host 0.0.0.0 --port 8000
```

### 🌐 Nginx

#### Проверка конфигурации
```bash
sudo nginx -t
```

#### Перезагрузка Nginx
```bash
sudo systemctl reload nginx
sudo systemctl restart nginx
```

#### Проверка статуса
```bash
sudo systemctl status nginx
```

#### Просмотр логов
```bash
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

### 📦 Сборка веб-приложения
```bash
cd /opt/tusabot/project
npm install                    # Установить зависимости
npm run build                  # Собрать production версию
# Результат в project/dist/
```

---

## 💻 КОМАНДЫ ДЛЯ ЛОКАЛЬНОЙ РАЗРАБОТКИ

### 🔄 Push на GitHub
```bash
# В локальной папке проекта
git add .
git commit -m "Описание изменений"
git push origin main
```

### 🧪 Локальный запуск бота
```bash
# Активировать venv
source venv/bin/activate  # Linux/Mac
# ИЛИ
venv\Scripts\activate     # Windows

# Запустить
python bot.py
```

### 🧪 Локальный запуск API
```bash
source venv/bin/activate
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

### 🧪 Локальный запуск веб-приложения
```bash
cd project
npm install
npm run dev
# Откроется на http://localhost:5173
```

---

## 🔌 API ENDPOINTS

### FastAPI Backend (`api.py`)

**Базовый URL:** `https://fammsktusovki.publicvm.com/api` (через Nginx)

#### GET `/`
```json
{
  "message": "TusaBot API",
  "version": "1.0.0",
  "endpoints": {...}
}
```

#### GET `/health`
```json
{
  "status": "healthy",
  "database": "connected"
}
```

#### GET `/posters`
Возвращает все активные афиши (сортировка по `created_at DESC`)
```json
[
  {
    "id": 1,
    "file_id": "/posters/poster_123.jpg",
    "photo_url": "/posters/poster_123.jpg",
    "caption": "Вечеринка 25 октября",
    "title": "Вечеринка 25 октября",
    "subtitle": "",
    "ticket_url": "https://example.com",
    "created_at": "2024-10-08T12:00:00",
    "is_active": true
  }
]
```

#### GET `/posters/latest`
Возвращает последнюю активную афишу

#### GET `/posters/{poster_id}`
Возвращает конкретную афишу по ID

#### GET `/photo/{file_id}`
Проксирует фото из Telegram Bot API (если `file_id` это Telegram file_id)

#### GET `/stats`
Общая статистика системы

---

## 🤖 TELEGRAM BOT КОМАНДЫ

### Команды для пользователей
- `/start` - Начать регистрацию или показать приветствие
- `/menu` - Главное меню с афишами
- `/id` - Показать свой Telegram ID

### Команды для админов
- `/admin` - Открыть админ-панель

### Инлайн кнопки админ-панели
- 🧩 Создать афишу
- 📋 Список афиш
- 📤 Разослать афишу
- 🗑 Удалить афишу
- 🔗 Задать ссылку
- 📝 Текстовая рассылка
- 🔍 Проверка по нику
- 👥 Пользователи
- 🔄 Обновить

---

## 🚀 ПРОЦЕСС ДЕПЛОЯ

### Автоматический деплой (GitHub Actions)
Файл: `.github/workflows/deploy.yml`

При каждом push в `main`:
1. Подключается к серверу по SSH
2. Выполняет `git pull origin main`
3. Активирует venv и устанавливает зависимости
4. Собирает веб-приложение (`npm run build`)
5. Перезапускает сервисы (bot, api, web)

### Ручной деплой
```bash
# 1. Push на GitHub
git add .
git commit -m "Описание"
git push origin main

# 2. На сервере
cd /opt/tusabot
git pull origin main

# 3. Обновить зависимости (если нужно)
source venv/bin/activate
pip install -r requirements.txt

# 4. Собрать веб-приложение
cd project
npm install
npm run build

# 5. Перезапустить сервисы
sudo systemctl restart tusabot
sudo systemctl restart tusabot-api
sudo systemctl restart tusabot-web
```

---

## 🔧 TROUBLESHOOTING

### Проблема: Бот не запускается
```bash
# Проверить логи
sudo journalctl -u tusabot -n 50

# Проверить виртуальное окружение
source venv/bin/activate
python bot.py  # Запустить вручную и увидеть ошибки

# Проверить .env файл
cat .env | grep BOT_TOKEN  # Должен быть токен

# Проверить подключение к БД
python check_db_connection.py
```

### Проблема: ModuleNotFoundError (httpx, asyncpg и т.д.)
```bash
cd /opt/tusabot
source venv/bin/activate
pip install -r requirements.txt
```

### Проблема: База данных недоступна
```bash
# Проверить статус PostgreSQL
sudo systemctl status postgresql

# Проверить подключение
sudo -u postgres psql -d familydb -c "SELECT 1;"

# Проверить .env
cat .env | grep DB_
```

### Проблема: Регистрация не показывается
```bash
# 1. Удалить кеш бота
rm -f data/bot_data.pkl

# 2. Проверить пользователя в БД
sudo -u postgres psql -d familydb -c "SELECT * FROM users WHERE tg_id = YOUR_ID;"

# 3. Если пользователя нет - должно показывать регистрацию
# 4. Перезапустить бота
sudo systemctl restart tusabot
```

### Проблема: Веб-приложение не открывается
```bash
# Проверить Nginx
sudo nginx -t
sudo systemctl status nginx

# Проверить что файлы собраны
ls -la project/dist/

# Проверить логи Nginx
sudo tail -f /var/log/nginx/error.log
```

### Проблема: API не отвечает
```bash
# Проверить статус API сервиса
sudo systemctl status tusabot-api

# Проверить что API работает
curl http://localhost:8000/health

# Проверить логи
sudo journalctl -u tusabot-api -n 50
```

---

## 📚 ВАЖНЫЕ ДЕТАЛИ РЕАЛИЗАЦИИ

### 1. Формат рассылки с кнопками
**Разделитель:** ` | ` (пробел-вертикальная черта-пробел)

**Правильно:**
```
Текст сообщения | Текст кнопки | https://ссылка
```

**Неправильно:**
```
Текст|Кнопка|https://ссылка  # Нет пробелов
Текст | Кнопка | ссылка      # Нет https://
```

### 2. Проверка подписок
Функция `is_user_subscribed()` возвращает кортеж `(канал1, канал2, чат)`:
- Все три должны быть `True` для полного доступа

### 3. Сохранение фото
- При создании афиши фото сохраняется в `project/public/posters/poster_<timestamp>.jpg`
- В БД сохраняется путь `/posters/poster_<timestamp>.jpg`
- Telegram использует `file_id` для быстрой отправки

### 4. Мини-приложение
- Использует React + TypeScript + TailwindCSS
- Собирается через Vite
- Доступно через Telegram Web App API
- Кнопка в главном меню бота ведет на веб-приложение

### 5. Безопасность
- `.env` файл НЕ должен быть в Git
- Все пароли в `.env`
- Nginx настроен для HTTPS
- CORS настроен (можно ограничить в продакшене)

---

## 📞 КОНТАКТЫ И ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ

### Каналы и чат
- 📢 Основной канал: `@mediafamm` (MEDIA FAM)
- 🎉 Второй канал: `@thefamilymsk` (THE FAMILY)
- 💬 Чат: `@familyychaat` (Family Guests)

### Домены
- 🌐 Веб-приложение: `https://fammsktusovki.publicvm.com`
- 🔌 API: `https://fammsktusovki.publicvm.com/api`

### Структура сервисов
- `tusabot.service` - Telegram бот (`bot.py`)
- `tusabot-api.service` - FastAPI (`api.py`, порт 8000)
- `tusabot-web.service` - Nginx для веб-приложения

---

## ✅ ЧЕКЛИСТ ПРИ РАБОТЕ С ПРОЕКТОМ

1. ✅ Всегда используй виртуальное окружение (`source venv/bin/activate`)
2. ✅ Проверь `.env` файл перед запуском
3. ✅ Убедись что PostgreSQL запущен
4. ✅ Проверь логи перед сообщением об ошибке (`journalctl -u tusabot`)
5. ✅ Удаляй кеш бота (`rm -f data/bot_data.pkl`) при проблемах с регистрацией
6. ✅ Используй правильный формат для рассылки с кнопками (` | `)
7. ✅ После изменений в коде - перезапускай сервисы
8. ✅ Перед push проверь что `.env` не попадет в коммит

---

**ВСЕГО ДОБРА И УСПЕШНОЙ РАБОТЫ! 🚀**

