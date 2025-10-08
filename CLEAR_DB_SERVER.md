# 🗑️ Очистка БД на сервере

## 🚀 Быстрая команда (удалить ВСЁ):

```bash
ssh root@5.129.250.86 "PGPASSWORD=1 psql -h 127.0.0.1 -p 5432 -U postgres -d FamilyDB -c 'DELETE FROM attendances; DELETE FROM posters; DELETE FROM users;' && rm -rf /opt/tusabot/project/public/posters/* && sudo systemctl restart tusabot"
```

---

## 📋 Команды для удаления (на сервере):

### 1️⃣ Удалить ВСЕХ пользователей:
```bash
PGPASSWORD=1 psql -h 127.0.0.1 -p 5432 -U postgres -d FamilyDB -c "DELETE FROM users;"
```

### 2️⃣ Удалить ВСЕ афиши:
```bash
PGPASSWORD=1 psql -h 127.0.0.1 -p 5432 -U postgres -d FamilyDB -c "DELETE FROM posters;"
```

### 3️⃣ Удалить ВСЮ посещаемость:
```bash
PGPASSWORD=1 psql -h 127.0.0.1 -p 5432 -U postgres -d FamilyDB -c "DELETE FROM attendances;"
```

### 4️⃣ Удалить файлы фото афиш:
```bash
rm -rf /opt/tusabot/project/public/posters/*
```

### 5️⃣ Перезапустить бота:
```bash
sudo systemctl restart tusabot
```

---

## 🎯 Выборочное удаление пользователей:

### Удалить конкретного пользователя по ID:
```bash
PGPASSWORD=1 psql -h 127.0.0.1 -p 5432 -U postgres -d FamilyDB -c "DELETE FROM users WHERE tg_id = 825042510;"
```

### Удалить пользователя по username:
```bash
PGPASSWORD=1 psql -h 127.0.0.1 -p 5432 -U postgres -d FamilyDB -c "DELETE FROM users WHERE username = 'denlyz1';"
```

### Удалить пользователей младше 18 лет:
```bash
PGPASSWORD=1 psql -h 127.0.0.1 -p 5432 -U postgres -d FamilyDB -c "DELETE FROM users WHERE age < 18;"
```

---

## 📊 Проверка количества записей:

```bash
PGPASSWORD=1 psql -h 127.0.0.1 -p 5432 -U postgres -d FamilyDB -c "SELECT 'Пользователей' as table_name, COUNT(*) FROM users UNION ALL SELECT 'Афиш', COUNT(*) FROM posters UNION ALL SELECT 'Посещений', COUNT(*) FROM attendances;"
```

---

## ⚠️ ВНИМАНИЕ:
- Эти команды удаляют данные **БЕЗ ВОЗВРАТА**
- Рекомендуется сделать бэкап перед удалением
- После удаления пользователей/афиш перезапустите бота

---

## 💾 Бэкап перед удалением (опционально):

```bash
# Создать бэкап всей БД
pg_dump -h 127.0.0.1 -U postgres -d FamilyDB > backup_$(date +%Y%m%d_%H%M%S).sql

# Восстановить из бэкапа
psql -h 127.0.0.1 -U postgres -d FamilyDB < backup_20251008_120000.sql
```

---

## ✅ Проверка после очистки:

В боте:
- Откройте админ-панель: `/admin`
- Нажмите "👥 Пользователи"
- Должно показать: `Всего пользователей: 0`

В мини-приложении:
- Должно показать: "Скоро здесь появятся новые мероприятия"

