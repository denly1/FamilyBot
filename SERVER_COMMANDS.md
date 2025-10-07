# 🚀 TusaBot - Команды Сервера

## 📋 Информация о Проекте

**Сервер:** `5.129.250.86`  
**Домен:** `fambot.duckdns.org`  
**Пользователь:** `root`  
**Путь проекта:** `/opt/tusabot`

### База Данных PostgreSQL
- **Хост:** `127.0.0.1`
- **Порт:** `5432`
- **БД:** `familydb`
- **Пользователь:** `postgres`
- **Пароль:** `1`

---

## 🔐 Подключение к Серверу

```bash
ssh root@5.129.250.86
```

---

## 📊 Мониторинг Сервисов

### Статус всех сервисов
```bash
sudo systemctl status tusabot --no-pager
sudo systemctl status tusabot-api --no-pager
sudo systemctl status tusabot-web --no-pager
```

### Быстрая проверка
```bash
# Бот
sudo systemctl is-active tusabot

# API
sudo systemctl is-active tusabot-api

# Web App
sudo systemctl is-active tusabot-web

# Nginx
sudo systemctl is-active nginx
```

---

## 🔄 Управление Сервисами

### Перезапуск
```bash
# Перезапустить бота
sudo systemctl restart tusabot

# Перезапустить API
sudo systemctl restart tusabot-api

# Перезапустить веб-приложение
sudo systemctl restart tusabot-web

# Перезапустить Nginx
sudo systemctl restart nginx

# Перезапустить всё
sudo systemctl restart tusabot tusabot-api tusabot-web nginx
```

### Остановка
```bash
sudo systemctl stop tusabot
sudo systemctl stop tusabot-api
sudo systemctl stop tusabot-web
```

### Запуск
```bash
sudo systemctl start tusabot
sudo systemctl start tusabot-api
sudo systemctl start tusabot-web
```

---

## 📝 Логи

### Просмотр логов в реальном времени
```bash
# Бот
sudo journalctl -u tusabot -f

# API
sudo journalctl -u tusabot-api -f

# Web App
sudo journalctl -u tusabot-web -f

# Nginx
sudo tail -f /var/log/nginx/tusabot-error.log
sudo tail -f /var/log/nginx/tusabot-access.log
```

### Последние 50 строк
```bash
sudo journalctl -u tusabot -n 50 --no-pager
sudo journalctl -u tusabot-api -n 50 --no-pager
sudo journalctl -u tusabot-web -n 50 --no-pager
```

### Логи за сегодня
```bash
sudo journalctl -u tusabot --since today --no-pager
```

---

## 🗄️ Работа с Базой Данных

### Подключение к PostgreSQL
```bash
psql -h 127.0.0.1 -U postgres -d familydb
```

### Полезные SQL команды
```sql
-- Посмотреть все афиши
SELECT id, file_id, caption, ticket_url, is_active, created_at FROM posters ORDER BY created_at DESC;

-- Посмотреть активные афиши
SELECT * FROM posters WHERE is_active = true ORDER BY created_at DESC;

-- Посмотреть количество пользователей
SELECT COUNT(*) FROM users;

-- Посмотреть последних зарегистрированных пользователей
SELECT tg_id, name, registered_at FROM users ORDER BY registered_at DESC LIMIT 10;

-- Очистить все афиши (ОСТОРОЖНО!)
TRUNCATE TABLE posters CASCADE;

-- Деактивировать все афиши
UPDATE posters SET is_active = false;

-- Удалить конкретную афишу
DELETE FROM posters WHERE id = 123;

-- Выйти из psql
\q
```

### Бэкап базы данных
```bash
# Создать бэкап
pg_dump -h 127.0.0.1 -U postgres familydb > /opt/tusabot/backup_$(date +%Y%m%d_%H%M%S).sql

# Восстановить бэкап
psql -h 127.0.0.1 -U postgres familydb < /opt/tusabot/backup_20251007_120000.sql
```

---

## 🔧 Обновление Проекта

### Через GitHub Actions (АВТОМАТИЧЕСКИ)
Просто сделайте `git push` в репозиторий - всё обновится автоматически!

### Вручную (если нужно)
```bash
cd /opt/tusabot

# Остановить сервисы
sudo systemctl stop tusabot tusabot-api tusabot-web

# Получить обновления
git pull origin main

# Обновить зависимости Python
source venv/bin/activate
pip install -r requirements.txt

# Применить миграции БД (если есть)
cd /opt/tusabot
source .env
export PGPASSWORD="${DB_PASSWORD}"
for migration in migrations/*.sql; do
  echo "Applying $migration..."
  psql -h "${DB_HOST}" -U "${DB_USER}" -d "${DB_NAME}" -f "$migration"
done

# Пересобрать веб-приложение
cd /opt/tusabot/project
npm install
npm run build

# Запустить сервисы
sudo systemctl start tusabot tusabot-api tusabot-web
```

---

## 🌐 Nginx

### Проверка конфигурации
```bash
sudo nginx -t
```

### Перезагрузка конфигурации
```bash
sudo systemctl reload nginx
```

### Просмотр конфигурации
```bash
cat /etc/nginx/sites-available/tusabot
```

### Редактирование конфигурации
```bash
sudo nano /etc/nginx/sites-available/tusabot
# После изменений:
sudo nginx -t
sudo systemctl reload nginx
```

---

## 🔒 SSL Сертификаты

### Обновление сертификата (автоматически)
Certbot обновляет сертификаты автоматически через cron.

### Проверка срока действия
```bash
sudo certbot certificates
```

### Ручное обновление
```bash
sudo certbot renew
sudo systemctl reload nginx
```

---

## 🦆 DuckDNS

### Обновление IP адреса
```bash
/opt/tusabot/scripts/duck.sh
cat ~/duck.log  # Должно быть "OK"
```

### Проверка DNS
```bash
ping fambot.duckdns.org -c 3
```

DuckDNS обновляется автоматически каждые 5 минут через cron.

---

## 🧹 Очистка и Обслуживание

### Очистка логов
```bash
# Удалить старые логи (старше 7 дней)
sudo journalctl --vacuum-time=7d
```

### Очистка старых фото афиш
```bash
# Посмотреть размер папки с афишами
du -sh /opt/tusabot/project/public/posters

# Удалить все фото (ОСТОРОЖНО!)
rm /opt/tusabot/project/public/posters/*
```

### Проверка места на диске
```bash
df -h
```

---

## 🆘 Устранение Проблем

### Бот не отвечает
```bash
# Проверить статус
sudo systemctl status tusabot --no-pager

# Посмотреть логи
sudo journalctl -u tusabot -n 50 --no-pager

# Перезапустить
sudo systemctl restart tusabot
```

### API не работает
```bash
# Проверить статус
sudo systemctl status tusabot-api --no-pager

# Проверить подключение
curl http://localhost:8000/health

# Проверить логи
sudo journalctl -u tusabot-api -n 50 --no-pager

# Перезапустить
sudo systemctl restart tusabot-api
```

### Мини-приложение не загружается
```bash
# Проверить веб-сервис
sudo systemctl status tusabot-web --no-pager
curl http://localhost:5173

# Проверить Nginx
sudo systemctl status nginx --no-pager
sudo nginx -t
curl https://fambot.duckdns.org/health

# Перезапустить
sudo systemctl restart tusabot-web nginx
```

### Фото не отображаются
```bash
# Проверить что фото сохранены
ls -lh /opt/tusabot/project/public/posters/

# Проверить права доступа
sudo chmod 644 /opt/tusabot/project/public/posters/*
sudo chown root:root /opt/tusabot/project/public/posters/*

# Проверить конфигурацию Nginx
cat /etc/nginx/sites-available/tusabot | grep -A 5 "location.*posters"

# Тестовый запрос
curl -I https://fambot.duckdns.org/posters/poster_1759764586.jpg
```

### База данных недоступна
```bash
# Проверить статус PostgreSQL
sudo systemctl status postgresql

# Попробовать подключиться
psql -h 127.0.0.1 -U postgres -d familydb -c "SELECT 1;"

# Перезапустить PostgreSQL
sudo systemctl restart postgresql
```

---

## ⚡ Быстрые Команды

### Полный перезапуск всего
```bash
cd /opt/tusabot && \
sudo systemctl stop tusabot tusabot-api tusabot-web && \
git pull origin main && \
source venv/bin/activate && pip install -r requirements.txt && \
cd project && npm install && npm run build && cd .. && \
sudo systemctl start tusabot tusabot-api tusabot-web && \
sudo systemctl status tusabot tusabot-api tusabot-web --no-pager
```

### Проверка всего (health check)
```bash
echo "=== SERVICES ===" && \
sudo systemctl is-active tusabot tusabot-api tusabot-web nginx && \
echo -e "\n=== API HEALTH ===" && \
curl -s http://localhost:8000/health && \
echo -e "\n\n=== WEB APP ===" && \
curl -I -s http://localhost:5173 | head -1 && \
echo -e "\n=== HTTPS ===" && \
curl -I -s https://fambot.duckdns.org/health | head -1 && \
echo -e "\n=== DATABASE ===" && \
psql -h 127.0.0.1 -U postgres -d familydb -c "SELECT COUNT(*) as posters FROM posters WHERE is_active = true;" && \
echo "Done!"
```

### Посмотреть текущие активные афиши
```bash
psql -h 127.0.0.1 -U postgres -d familydb -c "SELECT id, LEFT(caption, 30) as caption, ticket_url, created_at FROM posters WHERE is_active = true ORDER BY created_at DESC;"
```

---

## 📚 Полезная Информация

### Переменные окружения
Находятся в файле `/opt/tusabot/.env`:
```bash
cat /opt/tusabot/.env
```

### Структура проекта
```
/opt/tusabot/
├── bot.py                 # Telegram бот
├── api.py                 # FastAPI backend
├── db.py                  # Работа с БД
├── .env                   # Конфигурация
├── requirements.txt       # Python зависимости
├── venv/                  # Python виртуальное окружение
├── project/               # React приложение
│   ├── dist/              # Собранное приложение
│   ├── public/
│   │   └── posters/       # Фото афиш
│   └── src/
├── migrations/            # SQL миграции
├── systemd/               # Systemd сервисы
├── nginx/                 # Nginx конфигурация
└── scripts/               # Вспомогательные скрипты
```

### Порты
- **5173** - Vite dev server (веб-приложение)
- **8000** - FastAPI (API)
- **5432** - PostgreSQL
- **80** - HTTP (redirect to HTTPS)
- **443** - HTTPS (Nginx)

### GitHub Actions
После push в репозиторий автоматически:
1. Подключается к серверу по SSH
2. Останавливает сервисы
3. Скачивает обновления (`git pull`)
4. Устанавливает зависимости
5. Применяет миграции БД
6. Собирает веб-приложение
7. Перезапускает сервисы

Посмотреть статус деплоя: [GitHub Actions](https://github.com/YOUR_REPO/actions)

---

## 🎯 Типичные Задачи

### Добавить новую афишу
1. Отправьте команду `/start` боту
2. Нажмите "Админ панель"
3. Выберите "🧩 Создать афишу"
4. Следуйте инструкциям

### Удалить афишу
1. В боте: "Админ панель" → "🗑 Удалить афишу"
2. Или через БД:
```bash
psql -h 127.0.0.1 -U postgres -d familydb
DELETE FROM posters WHERE id = 123;
\q
```

### Посмотреть статистику
```bash
curl -s https://fambot.duckdns.org/stats | python3 -m json.tool
```

---

## 📞 Контакты и Ссылки

- **Telegram Bot:** [@your_bot](https://t.me/your_bot)
- **Web App:** https://fambot.duckdns.org
- **API Docs:** https://fambot.duckdns.org/docs (если включено в FastAPI)
- **DuckDNS Panel:** https://www.duckdns.org

---

## ⚠️ Важные Заметки

1. **НИКОГДА не делайте `git push --force` на main**
2. **Всегда проверяйте бэкапы БД перед обновлениями**
3. **SSL сертификаты обновляются автоматически**
4. **DuckDNS IP обновляется каждые 5 минут**
5. **GitHub Actions деплоит при каждом push**
6. **При изменении `.env` нужно перезапустить все сервисы**
7. **Фото афиш хранятся в `/opt/tusabot/project/public/posters/`**
8. **При удалении афиши через бота, фото тоже удаляется**

---

*Последнее обновление: 7 октября 2025*

