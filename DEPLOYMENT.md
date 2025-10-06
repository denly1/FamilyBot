# 🚀 Руководство по деплою TusaBot

## 📋 Что нужно задеплоить:

1. **PostgreSQL** - база данных (если еще не задеплоена)
2. **API Backend** - FastAPI сервер (`api.py`)
3. **Telegram Bot** - бот (`bot.py`)
4. **Web App** - React приложение (`project/`)

---

## 🗄️ 1. PostgreSQL

### Вариант A: Локальный сервер
Уже настроено, ничего делать не нужно.

### Вариант B: Облачный PostgreSQL

#### Railway.app (рекомендуется):
1. Зарегистрируйтесь на https://railway.app
2. Создайте новый проект
3. Добавьте PostgreSQL
4. Скопируйте DATABASE_URL
5. Обновите `.env`:
   ```env
   DATABASE_URL=postgresql://user:pass@host:port/dbname
   ```

#### Supabase (только PostgreSQL):
1. Создайте проект на https://supabase.com
2. Перейдите в Settings → Database
3. Скопируйте Connection String
4. Обновите `.env`

#### Neon.tech (бесплатно):
1. Зарегистрируйтесь на https://neon.tech
2. Создайте проект
3. Скопируйте Connection String
4. Обновите `.env`

---

## 🔧 2. API Backend (FastAPI)

### Вариант A: Railway.app

#### Шаг 1: Подготовка
Создайте `Procfile` в корне проекта:
```
web: uvicorn api:app --host 0.0.0.0 --port $PORT
```

Создайте `runtime.txt`:
```
python-3.11
```

#### Шаг 2: Деплой
```bash
# Установите Railway CLI
npm install -g @railway/cli

# Логин
railway login

# Инициализация
railway init

# Деплой
railway up
```

#### Шаг 3: Настройка переменных
В Railway Dashboard → Variables:
```
DB_HOST=your_db_host
DB_PORT=5432
DB_NAME=FamilyDB
DB_USER=postgres
DB_PASSWORD=your_password
```

#### Шаг 4: Получите URL
Railway автоматически даст вам URL типа:
```
https://your-app.railway.app
```

---

### Вариант B: Render.com

#### Шаг 1: Создайте Web Service
1. Зайдите на https://render.com
2. New → Web Service
3. Подключите GitHub репозиторий

#### Шаг 2: Настройки
```
Name: tusabot-api
Environment: Python 3
Build Command: pip install -r requirements.txt
Start Command: uvicorn api:app --host 0.0.0.0 --port $PORT
```

#### Шаг 3: Environment Variables
```
DB_HOST=your_db_host
DB_PORT=5432
DB_NAME=FamilyDB
DB_USER=postgres
DB_PASSWORD=your_password
```

---

### Вариант C: VPS (Ubuntu)

```bash
# Подключитесь к серверу
ssh user@your-server.com

# Установите зависимости
sudo apt update
sudo apt install python3-pip nginx

# Клонируйте репозиторий
git clone https://github.com/your-repo/tusabot.git
cd tusabot

# Установите пакеты
pip3 install -r requirements.txt

# Создайте systemd service
sudo nano /etc/systemd/system/tusabot-api.service
```

Содержимое файла:
```ini
[Unit]
Description=TusaBot API
After=network.target

[Service]
User=your-user
WorkingDirectory=/path/to/tusabot
Environment="PATH=/usr/local/bin"
ExecStart=/usr/local/bin/uvicorn api:app --host 0.0.0.0 --port 8000

[Install]
WantedBy=multi-user.target
```

Запуск:
```bash
sudo systemctl enable tusabot-api
sudo systemctl start tusabot-api
sudo systemctl status tusabot-api
```

Настройка Nginx:
```bash
sudo nano /etc/nginx/sites-available/tusabot-api
```

```nginx
server {
    listen 80;
    server_name api.your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/tusabot-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 🤖 3. Telegram Bot

### Вариант A: Railway.app

#### Шаг 1: Обновите Procfile
```
worker: python bot.py
```

#### Шаг 2: Деплой
```bash
railway up
```

#### Шаг 3: Переменные окружения
```
BOT_TOKEN=your_bot_token
ADMIN_USER_ID=your_telegram_id
CHANNEL_USERNAME=@largentmsk
CHANNEL_USERNAME_2=@idnrecords
DB_HOST=your_db_host
DB_PORT=5432
DB_NAME=FamilyDB
DB_USER=postgres
DB_PASSWORD=your_password
VK_TOKEN=your_vk_token
VK_GROUP_DOMAIN=largent.tusa
```

---

### Вариант B: VPS (рекомендуется для ботов)

```bash
# Создайте systemd service
sudo nano /etc/systemd/system/tusabot.service
```

```ini
[Unit]
Description=TusaBot Telegram Bot
After=network.target

[Service]
User=your-user
WorkingDirectory=/path/to/tusabot
Environment="PATH=/usr/local/bin"
ExecStart=/usr/bin/python3 bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable tusabot
sudo systemctl start tusabot
sudo systemctl status tusabot

# Просмотр логов
sudo journalctl -u tusabot -f
```

---

## 🌐 4. Web App (React)

### Вариант A: Vercel (рекомендуется)

#### Шаг 1: Подготовка
Создайте `project/vercel.json`:
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": "vite",
  "env": {
    "VITE_API_URL": "https://your-api.railway.app"
  }
}
```

#### Шаг 2: Деплой
```bash
cd project
npm install -g vercel
vercel login
vercel
```

#### Шаг 3: Настройка
В Vercel Dashboard → Settings → Environment Variables:
```
VITE_API_URL=https://your-api.railway.app
```

---

### Вариант B: Netlify

#### Шаг 1: Создайте `project/netlify.toml`:
```toml
[build]
  command = "npm run build"
  publish = "dist"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

#### Шаг 2: Деплой
```bash
cd project
npm install -g netlify-cli
netlify login
netlify deploy --prod
```

---

### Вариант C: GitHub Pages

```bash
cd project

# Установите gh-pages
npm install --save-dev gh-pages

# Добавьте в package.json
"homepage": "https://yourusername.github.io/tusabot",
"scripts": {
  "predeploy": "npm run build",
  "deploy": "gh-pages -d dist"
}

# Деплой
npm run deploy
```

---

## 🔗 5. Подключение мини-приложения к Telegram

### Шаг 1: Получите URL веб-приложения
После деплоя у вас будет URL типа:
```
https://tusabot.vercel.app
```

### Шаг 2: Обновите bot.py
Найдите функцию `show_web_app` и замените URL:
```python
async def show_web_app(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    web_app_url = "https://tusabot.vercel.app"  # ВАШ URL
    
    keyboard = [
        [InlineKeyboardButton("Открыть приложение", web_app=WebAppInfo(url=web_app_url))]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Нажмите кнопку ниже, чтобы открыть приложение:",
        reply_markup=reply_markup
    )
```

### Шаг 3: Перезапустите бота

### Шаг 4: Тестирование
```
/app - откроет веб-приложение
```

---

## ✅ Проверка деплоя:

### 1. API Backend
```bash
curl https://your-api.railway.app/health
# Должно вернуть: {"status":"healthy","database":"connected"}
```

### 2. Telegram Bot
Отправьте боту:
```
/start
/menu
/admin
```

### 3. Web App
Откройте в браузере:
```
https://tusabot.vercel.app
```

---

## 🔒 Безопасность:

### 1. CORS в API
Обновите `api.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tusabot.vercel.app",  # Ваш домен
        "https://web.telegram.org"      # Telegram Web App
    ],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)
```

### 2. Переменные окружения
Никогда не коммитьте `.env` в Git!

### 3. HTTPS
Всегда используйте HTTPS для API и веб-приложения.

---

## 📊 Мониторинг:

### Логи бота:
```bash
# Railway
railway logs

# VPS
sudo journalctl -u tusabot -f
```

### Логи API:
```bash
# Railway
railway logs

# VPS
sudo journalctl -u tusabot-api -f
```

---

## 🎉 Готово!

После деплоя у вас будет:
- ✅ API Backend на Railway/Render/VPS
- ✅ Telegram Bot на Railway/VPS
- ✅ Web App на Vercel/Netlify
- ✅ PostgreSQL на Railway/Neon
- ✅ Все работает вместе!

**Создайте первую афишу и проверьте что она появилась везде!** 🚀

---

## 📞 Поддержка:

Если что-то не работает:
1. Проверьте логи сервисов
2. Проверьте переменные окружения
3. Проверьте CORS настройки
4. Проверьте подключение к БД

---

*Последнее обновление: 5 октября 2025*