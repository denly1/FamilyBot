"""
FastAPI backend для подключения веб-приложения к PostgreSQL
Предоставляет REST API для получения афиш из базы данных
"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import asyncpg
from contextlib import asynccontextmanager
import logging
import httpx

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TusaBotAPI")

# Настройки БД из переменных окружения
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "FamilyDB")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "1")

# Telegram Bot Token для получения файлов
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Глобальный пул соединений
db_pool: Optional[asyncpg.Pool] = None


# Модели данных
class Poster(BaseModel):
    id: int
    file_id: str
    caption: Optional[str]
    ticket_url: Optional[str]
    created_at: str
    is_active: bool


class PosterForWeb(BaseModel):
    """Модель афиши для веб-приложения (без file_id)"""
    id: int
    title: str  # Первая строка caption
    subtitle: str  # Остальной caption
    ticket_url: Optional[str]
    image_url: str  # URL для получения изображения через Telegram Bot API
    created_at: str


# Lifespan context manager для управления пулом БД
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            min_size=1,
            max_size=10,
        )
        logger.info("Database pool created successfully")
    except Exception as e:
        logger.error(f"Failed to create database pool: {e}")
        raise
    
    yield
    
    # Shutdown
    if db_pool:
        await db_pool.close()
        logger.info("Database pool closed")


# Создание приложения FastAPI
app = FastAPI(
    title="TusaBot API",
    description="API для получения афиш мероприятий",
    version="1.0.0",
    lifespan=lifespan
)

# Настройка CORS для доступа из веб-приложения
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Эндпоинты API

@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "message": "TusaBot API",
        "version": "1.0.0",
        "endpoints": {
            "/posters": "Получить все активные афиши",
            "/posters/latest": "Получить последнюю афишу",
            "/posters/{poster_id}": "Получить афишу по ID"
        }
    }


@app.get("/health")
async def health_check():
    """Проверка здоровья API"""
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database pool not initialized")
    
    try:
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")


@app.get("/posters")
async def get_posters():
    """Получить все активные афиши"""
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, file_id, caption, ticket_url, created_at, is_active
                FROM posters
                WHERE is_active = true
                ORDER BY created_at DESC
                """
            )
            
            posters = []
            for row in rows:
                file_id = row['file_id']
                is_local_file = file_id.startswith('/posters/')
                
                caption = row['caption'] or ""
                lines = caption.split('\n', 1)
                title = lines[0] if lines else "Мероприятие"
                subtitle = lines[1] if len(lines) > 1 else ""
                
                posters.append({
                    "id": row['id'],
                    "file_id": file_id,
                    "photo_url": file_id if is_local_file else f"/photo/{file_id}",
                    "caption": caption,
                    "title": title,
                    "subtitle": subtitle,
                    "ticket_url": row['ticket_url'],
                    "created_at": row['created_at'].isoformat(),
                    "is_active": row['is_active']
                })
            
            return posters
    except Exception as e:
        logger.error(f"Failed to fetch posters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/posters/latest")
async def get_latest_poster():
    """Получить последнюю активную афишу"""
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, file_id, caption, ticket_url, created_at, is_active
                FROM posters
                WHERE is_active = true
                ORDER BY created_at DESC
                LIMIT 1
                """
            )
            
            if not row:
                raise HTTPException(status_code=404, detail="No active posters found")
            
            # Парсим caption для разделения на title и subtitle
            caption = row['caption'] or ""
            lines = caption.split('\n', 1)
            title = lines[0] if lines else "Мероприятие"
            subtitle = lines[1] if len(lines) > 1 else ""
            
            # file_id теперь может быть путем к файлу (/posters/poster_123.jpg) или Telegram file_id
            file_id = row['file_id']
            is_local_file = file_id.startswith('/posters/')
            
            return {
                "id": row['id'],
                "file_id": file_id,
                "photo_url": file_id if is_local_file else f"/photo/{file_id}",  # Прямой путь или через API
                "caption": caption,
                "title": title,
                "subtitle": subtitle,
                "ticket_url": row['ticket_url'],
                "created_at": row['created_at'].isoformat(),
                "is_active": row['is_active']
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch latest poster: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/posters/{poster_id}")
async def get_poster(poster_id: int):
    """Получить афишу по ID"""
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, file_id, caption, ticket_url, created_at, is_active
                FROM posters
                WHERE id = $1
                """,
                poster_id
            )
            
            if not row:
                raise HTTPException(status_code=404, detail="Poster not found")
            
            return {
                "id": row['id'],
                "file_id": row['file_id'],
                "caption": row['caption'],
                "ticket_url": row['ticket_url'],
                "created_at": row['created_at'].isoformat(),
                "is_active": row['is_active']
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch poster {poster_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """Получить общую статистику"""
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        async with db_pool.acquire() as conn:
            # Статистика пользователей
            user_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_users,
                    COUNT(vk_id) as users_with_vk,
                    COUNT(CASE WHEN gender = 'male' THEN 1 END) as male_users,
                    COUNT(CASE WHEN gender = 'female' THEN 1 END) as female_users
                FROM users
            """)
            
            # Статистика афиш
            poster_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_posters,
                    COUNT(CASE WHEN is_active = true THEN 1 END) as active_posters
                FROM posters
            """)
            
            return {
                "users": {
                    "total": user_stats['total_users'],
                    "with_vk": user_stats['users_with_vk'],
                    "male": user_stats['male_users'],
                    "female": user_stats['female_users']
                },
                "posters": {
                    "total": poster_stats['total_posters'],
                    "active": poster_stats['active_posters']
                }
            }
    except Exception as e:
        logger.error(f"Failed to fetch stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/photo/{file_id}")
async def get_photo(file_id: str):
    """Получить фото афиши через Telegram Bot API"""
    if not BOT_TOKEN:
        raise HTTPException(status_code=503, detail="Bot token not configured")
    
    try:
        # Получаем информацию о файле
        async with httpx.AsyncClient() as client:
            file_info_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
            file_response = await client.get(file_info_url)
            file_data = file_response.json()
            
            if not file_data.get("ok"):
                raise HTTPException(status_code=404, detail="File not found")
            
            file_path = file_data["result"]["file_path"]
            
            # Скачиваем файл
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            photo_response = await client.get(file_url)
            
            if photo_response.status_code != 200:
                raise HTTPException(status_code=404, detail="Failed to download photo")
            
            # Возвращаем фото
            return StreamingResponse(
                iter([photo_response.content]),
                media_type="image/jpeg",
                headers={"Cache-Control": "public, max-age=86400"}  # Кеш на 24 часа
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get photo {file_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
