import os
from dotenv import load_dotenv
import asyncpg
from typing import Optional, Dict, Any, List

# Загружаем переменные окружения из .env файла
load_dotenv()

class Database:
    _pool = None
    
    @classmethod
    async def get_pool(cls):
        """Создает и возвращает пул подключений к базе данных"""
        if cls._pool is None:
            cls._pool = await asyncpg.create_pool(
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", "5432")),
                database=os.getenv("DB_NAME", "FamilyDB"),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", "1")
            )
        return cls._pool
    
    @classmethod
    async def close_pool(cls):
        """Закрывает пул подключений"""
        if cls._pool is not None:
            await cls._pool.close()
            cls._pool = None


class UserRepository:
    """Класс для работы с таблицей пользователей"""
    
    @staticmethod
    async def create_or_update_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создает или обновляет данные пользователя"""
        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            user = await conn.fetchrow("""
                INSERT INTO users (tg_id, name, gender, age, vk_id, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
                ON CONFLICT (tg_id) 
                DO UPDATE SET 
                    name = EXCLUDED.name,
                    gender = EXCLUDED.gender,
                    age = EXCLUDED.age,
                    vk_id = EXCLUDED.vk_id,
                    updated_at = NOW()
                RETURNING *
            """, 
            user_data.get('tg_id'),
            user_data.get('name'),
            user_data.get('gender'),
            user_data.get('age'),
            user_data.get('vk_id')
            )
            return dict(user) if user else None
    
    @staticmethod
    async def get_user(tg_id: int) -> Optional[Dict[str, Any]]:
        """Получает данные пользователя по Telegram ID"""
        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT * FROM users WHERE tg_id = $1", 
                tg_id
            )
            return dict(user) if user else None


class PosterRepository:
    """Класс для работы с таблицей афиш"""
    
    @staticmethod
    async def create_poster(poster_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создает новую афишу"""
        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            poster = await conn.fetchrow("""
                INSERT INTO posters (file_id, caption, ticket_url, is_active, created_at)
                VALUES ($1, $2, $3, $4, NOW())
                RETURNING *
            """,
            poster_data.get('file_id'),
            poster_data.get('caption'),
            poster_data.get('ticket_url'),
            poster_data.get('is_active', True)
            )
            return dict(poster) if poster else None
    
    @staticmethod
    async def get_active_posters() -> List[Dict[str, Any]]:
        """Получает список активных афиш"""
        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            posters = await conn.fetch(
                "SELECT * FROM posters WHERE is_active = TRUE ORDER BY created_at DESC"
            )
            return [dict(poster) for poster in posters]


class AttendanceRepository:
    """Класс для работы с таблицей посещений"""
    
    @staticmethod
    async def mark_attendance(user_id: int, poster_id: int) -> Dict[str, Any]:
        """Отмечает пользователя на мероприятии"""
        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            attendance = await conn.fetchrow("""
                INSERT INTO attendances (user_id, poster_id, attended_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (user_id, poster_id) 
                DO UPDATE SET attended_at = NOW()
                RETURNING *
            """, user_id, poster_id)
            return dict(attendance) if attendance else None
    
    @staticmethod
    async def get_user_attendances(user_id: int) -> List[Dict[str, Any]]:
        """Получает список мероприятий, на которые записался пользователь"""
        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            attendances = await conn.fetch("""
                SELECT a.*, p.caption, p.ticket_url 
                FROM attendances a
                JOIN posters p ON a.poster_id = p.id
                WHERE a.user_id = $1
                ORDER BY a.attended_at DESC
            """, user_id)
            return [dict(att) for att in attendances]
