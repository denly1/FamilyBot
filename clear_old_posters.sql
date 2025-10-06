-- Скрипт для очистки старых афиш из базы данных
-- Запустите этот скрипт в pgAdmin или psql, чтобы удалить все старые афиши
-- и начать с чистого листа

-- Показать текущие афиши
SELECT id, file_id, caption, ticket_url, created_at, is_active 
FROM posters 
ORDER BY created_at DESC;

-- Удалить все афиши (раскомментируйте следующую строку для выполнения)
-- DELETE FROM posters;

-- Или удалить только неактивные афиши
-- DELETE FROM posters WHERE is_active = false;

-- Проверить результат
-- SELECT COUNT(*) as total_posters FROM posters;
