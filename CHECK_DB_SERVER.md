# 🔍 Проверка базы данных на сервере

## 🚀 Быстрая проверка (одна команда):

```bash
ssh root@5.129.250.86 'cd /opt/tusabot && source venv/bin/activate && python3 << "PYTHON"
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "FamilyDB")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "1")

async def check():
    try:
        conn = await asyncpg.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASSWORD)
        print("✅ БД подключена!")
        users = await conn.fetchval("SELECT COUNT(*) FROM users")
        posters = await conn.fetchval("SELECT COUNT(*) FROM posters")
        print(f"📊 Пользователей: {users}")
        print(f"📊 Афиш: {posters}")
        await conn.close()
    except Exception as e:
        print(f"❌ Ошибка: {e}")

asyncio.run(check())
PYTHON
'
```

---

## 📋 Пошаговая проверка на сервере:

### 1. Подключитесь к серверу:
```bash
ssh root@5.129.250.86
```

### 2. Проверьте статус PostgreSQL:
```bash
systemctl status postgresql
```

Должно быть: **active (running)**

---

### 3. Проверьте содержимое .env:
```bash
cd /opt/tusabot
cat .env | grep DB_
```

Должно показать:
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=FamilyDB
DB_USER=postgres
DB_PASSWORD=1
```

---

### 4. Попробуйте подключиться к БД:

**Вариант A: Через sudo (без пароля):**
```bash
sudo -u postgres psql -d FamilyDB
```

**Вариант B: С паролем:**
```bash
PGPASSWORD=1 psql -h localhost -U postgres -d FamilyDB
```

**Вариант C: Через Unix socket:**
```bash
sudo -u postgres psql
\c FamilyDB
```

---

### 5. Если подключились, проверьте данные:
```sql
-- Количество записей
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM posters;
SELECT COUNT(*) FROM attendances;

-- Структура таблиц
\dt

-- Выход
\q
```

---

### 6. Проверьте логи бота:
```bash
sudo journalctl -u tusabot -n 50 --no-pager
```

Ищите строки с "DB" или "database" или "Failed to init DB"

---

### 7. Проверьте API:
```bash
curl http://localhost:8000/health
```

Должен вернуть:
```json
{"status":"healthy","database":"connected"}
```

---

## 🔧 Если БД не подключается:

### Проблема 1: "password authentication failed"

**Решение:** Сброс пароля postgres
```bash
sudo -u postgres psql
ALTER USER postgres WITH PASSWORD '1';
\q
```

---

### Проблема 2: "database FamilyDB does not exist"

**Решение:** Создать базу
```bash
sudo -u postgres createdb FamilyDB
cd /opt/tusabot
source venv/bin/activate
python3 << EOF
import asyncio
from db import create_pool, init_schema

async def setup():
    pool = await create_pool()
    await init_schema(pool)
    await pool.close()
    print("✅ Схема БД создана!")

asyncio.run(setup())
EOF
```

---

### Проблема 3: "Peer authentication failed"

**Решение:** Изменить метод аутентификации
```bash
sudo nano /etc/postgresql/14/main/pg_hba.conf
```

Найдите строку:
```
local   all             postgres                                peer
```

Замените на:
```
local   all             postgres                                md5
```

Перезапустите:
```bash
sudo systemctl restart postgresql
```

---

## 📊 Скрипт полной диагностики:

```bash
ssh root@5.129.250.86 << 'EOF'
echo "=== ДИАГНОСТИКА БД ==="
echo ""
echo "1. PostgreSQL статус:"
systemctl is-active postgresql

echo ""
echo "2. Переменные .env:"
cd /opt/tusabot
grep "DB_" .env

echo ""
echo "3. Попытка подключения через sudo:"
sudo -u postgres psql -d FamilyDB -c "SELECT 'БД доступна!' as status;" 2>&1

echo ""
echo "4. Количество записей:"
sudo -u postgres psql -d FamilyDB -c "SELECT 'users' as table_name, COUNT(*) FROM users UNION ALL SELECT 'posters', COUNT(*) FROM posters;" 2>&1

echo ""
echo "5. Логи бота (последние 10 строк):"
journalctl -u tusabot -n 10 --no-pager | grep -i "db\|database"

echo ""
echo "6. API health check:"
curl -s http://localhost:8000/health

echo ""
echo "=== ДИАГНОСТИКА ЗАВЕРШЕНА ==="
EOF
```

---

## ✅ После исправления:

Перезапустите все сервисы:
```bash
sudo systemctl restart postgresql
sudo systemctl restart tusabot
sudo systemctl restart tusabot-api
```

