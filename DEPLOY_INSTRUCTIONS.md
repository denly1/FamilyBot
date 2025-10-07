# 📝 Инструкция по Деплою

## Что нужно сделать СЕЙЧАС:

### 1️⃣ Создать файл `.env.production`

Создайте файл `project/.env.production` со следующим содержимым:

```
VITE_API_URL=https://fambot.duckdns.org
```

**Как создать:**
- Откройте папку `project` в вашем проекте
- Создайте новый файл `.env.production` (с точкой в начале!)
- Вставьте строку: `VITE_API_URL=https://fambot.duckdns.org`
- Сохраните файл

---

### 2️⃣ Закоммитить и запушить изменения

Откройте терминал в папке проекта и выполните:

```bash
git add .
git commit -m "Fix photo display and swipe functionality in mini-app"
git push origin main
```

**Что изменилось:**
- ✅ Исправлена логика отображения фото в мини-приложении
- ✅ API теперь правильно определяет локальные файлы
- ✅ Добавлена поддержка путей как `/posters/file.jpg`, так и `posters/file.jpg`
- ✅ Упрощена логика URL для фото
- ✅ Добавлен `SERVER_COMMANDS.md` с полной документацией по серверу

---

### 3️⃣ Дождаться автоматического деплоя

После push:
1. GitHub Actions автоматически подключится к серверу
2. Скачает обновления
3. Пересоберет веб-приложение
4. Перезапустит все сервисы

**Статус деплоя можно посмотреть здесь:**  
https://github.com/ВАШ_РЕПОЗИТОРИЙ/actions

---

## 🔍 Проверка после деплоя

### На сервере:

```bash
# Подключитесь к серверу
ssh root@5.129.250.86

# Проверьте что все сервисы работают
sudo systemctl status tusabot tusabot-api tusabot-web --no-pager

# Проверьте что фото на месте
ls -lh /opt/tusabot/project/public/posters/

# Проверьте API
curl -s http://localhost:8000/posters | python3 -m json.tool

# Выйдите
exit
```

### В браузере:

1. Откройте https://fambot.duckdns.org
2. Должны отобразиться афиши с фото
3. Попробуйте свайпнуть влево/вправо для навигации
4. Кнопка "Купить билет" должна вести на правильную ссылку

---

## 🐛 Если что-то не работает

### Фото не отображаются:

```bash
# На сервере проверьте Nginx конфигурацию
sudo nano /etc/nginx/sites-available/tusabot

# Убедитесь что есть такой блок:
# location ~ ^/posters/poster_.+\.(jpg|jpeg|png|gif)$ {
#     root /opt/tusabot/project/public;
#     expires 1d;
#     access_log off;
#     add_header Cache-Control "public, immutable";
# }

# Если внесли изменения:
sudo nginx -t
sudo systemctl reload nginx
```

### Свайп не работает:

Убедитесь что в `project/src/App.tsx` логика свайпа правильная (она уже исправлена в последнем коммите).

### База данных пустая:

```bash
# Подключитесь к БД
psql -h 127.0.0.1 -U postgres -d familydb

# Посмотрите афиши
SELECT * FROM posters WHERE is_active = true;

# Если нет - создайте новую через бота
# /start -> Админ панель -> Создать афишу
```

---

## 📚 Справка

Все команды для управления сервером теперь в файле `SERVER_COMMANDS.md`!

---

**Вопросы?** Напишите в чат!

