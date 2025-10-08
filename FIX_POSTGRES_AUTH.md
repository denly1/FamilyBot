# 🔧 Исправление аутентификации PostgreSQL

## Проблема:
`FATAL: password authentication failed for user "postgres"`

---

## Решение 1: Использовать sudo (без пароля)

```bash
# На сервере выполните:
sudo -u postgres psql -d FamilyDB -c "DELETE FROM users;"
sudo -u postgres psql -d FamilyDB -c "DELETE FROM posters;"
sudo -u postgres psql -d FamilyDB -c "DELETE FROM attendances;"

# Проверка
sudo -u postgres psql -d FamilyDB -c "SELECT COUNT(*) FROM users;"
```

---

## Решение 2: Узнать правильный пароль

Проверьте ваш `.env` файл:
```bash
cat /opt/tusabot/.env | grep DB_PASSWORD
```

Затем используйте этот пароль:
```bash
PGPASSWORD=ваш_пароль psql -h 127.0.0.1 -p 5432 -U postgres -d FamilyDB -c "DELETE FROM users;"
```

---

## Решение 3: Использовать пользователя tusabot_user (если создан)

```bash
PGPASSWORD=ваш_пароль psql -h 127.0.0.1 -p 5432 -U tusabot_user -d FamilyDB -c "DELETE FROM users;"
```

---

## 🚀 БЫСТРАЯ КОМАНДА (через sudo, работает всегда):

```bash
# Удалить всё
sudo -u postgres psql -d FamilyDB << 'EOF'
DELETE FROM attendances;
DELETE FROM posters;
DELETE FROM users;
EOF

# Удалить файлы фото
rm -rf /opt/tusabot/project/public/posters/*

# Перезапустить бота
sudo systemctl restart tusabot
```

---

## ✅ Проверка после очистки:

```bash
sudo -u postgres psql -d FamilyDB -c "SELECT 'Пользователей' as item, COUNT(*) FROM users UNION ALL SELECT 'Афиш', COUNT(*) FROM posters;"
```

---

## 📝 Для следующего раза:

Добавьте в начало команды `sudo -u postgres` вместо `PGPASSWORD=1`:

```bash
# ❌ НЕ работает:
PGPASSWORD=1 psql -h 127.0.0.1 -p 5432 -U postgres -d FamilyDB

# ✅ РАБОТАЕТ:
sudo -u postgres psql -d FamilyDB
```

