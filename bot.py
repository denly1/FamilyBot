import os
import logging
import asyncio
from datetime import datetime, timedelta, time, timezone
from pathlib import Path
import pytz
from typing import Set, Optional
import re
import httpx

# Simple validators
def is_valid_url(url: str) -> bool:
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    return bool(re.match(r"^(https?://)[\w\-]+(\.[\w\-]+)+(:\d+)?(/[\w\-._~:/?#\[\]@!$&'()*+,;=%]*)?$", url))

def is_valid_caption(c: str) -> bool:
    # Telegram photo caption limit is 1024 chars for older APIs; use 1024 as a safe cap
    return c is not None and len(c) <= 1024

from dotenv import load_dotenv, dotenv_values, find_dotenv
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    BotCommand,
    WebAppInfo,
)
from telegram.constants import ChatMemberStatus
from telegram.error import Forbidden, RetryAfter, BadRequest, TimedOut, NetworkError, TelegramError
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    PicklePersistence,
    ContextTypes,
    TypeHandler,
    filters,
)
from telegram.request import HTTPXRequest
from db import (
    create_pool, init_schema, upsert_user, get_user, get_user_by_username, 
    get_all_user_ids, get_user_stats, export_users_to_excel, deactivate_users,
    create_poster, get_active_posters, get_latest_poster, get_poster_by_id,
    deactivate_poster, delete_poster as db_delete_poster, update_poster_ticket_url,
    mark_attendance, get_user_attendances, get_poster_attendances, get_attendance_stats,
    get_admin_ids as db_get_admin_ids, add_admin as db_add_admin, remove_admin as db_remove_admin
)

# ----------------------
# Logging
# ----------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("TusaBot")

# ----------------------
# Env config
# ----------------------
_DOTENV_PATH = find_dotenv(usecwd=True) or os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=_DOTENV_PATH, override=True)
_ENV_FALLBACK = dotenv_values(dotenv_path=_DOTENV_PATH)  # read .env directly as fallback


def _clean_env(v: str) -> str:
    v = (v or "").strip()
    # remove surrounding single or double quotes if present
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        v = v[1:-1].strip()
    return v


def _get_env(key: str, default: str = "") -> str:
    v = os.getenv(key)
    if v is None or v == "":
        v = _ENV_FALLBACK.get(key, default)
    return _clean_env(v)


BOT_TOKEN = _get_env("BOT_TOKEN", "")
ADMIN_USER_ID_STR = _get_env("ADMIN_USER_ID", "")
ADMIN_USER_ID = int(ADMIN_USER_ID_STR) if ADMIN_USER_ID_STR.isdigit() else 0
ADMIN_USER_ID_2_STR = _get_env("ADMIN_USER_ID_2", "")
ADMIN_USER_ID_2 = int(ADMIN_USER_ID_2_STR) if ADMIN_USER_ID_2_STR.isdigit() else 0
ADMIN_USER_ID_3_STR = _get_env("ADMIN_USER_ID_3", "")
ADMIN_USER_ID_3 = int(ADMIN_USER_ID_3_STR) if ADMIN_USER_ID_3_STR.isdigit() else 0
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@mediafamm")
CHANNEL_USERNAME_2 = os.getenv("CHANNEL_USERNAME_2", "@thefamilymsk")
CHAT_USERNAME = os.getenv("CHAT_USERNAME", "@familyychaat")

def _normalize_channel(value: str):
    v = (value or "").strip()
    # numeric chat id like -1001234567890
    if v.startswith("-100") and v[4:].isdigit():
        return int(v)
    # strip t.me prefixes
    for prefix in ("https://t.me/", "http://t.me/", "t.me/"):
        if v.lower().startswith(prefix):
            v = v[len(prefix):]
            break
    if not v.startswith("@"):
        v = f"@{v}"
    return v

CHANNEL_ID = _normalize_channel(CHANNEL_USERNAME)
CHANNEL_ID_2 = _normalize_channel(CHANNEL_USERNAME_2)
CHAT_ID = _normalize_channel(CHAT_USERNAME)
WEEKLY_DAY = int(_get_env("WEEKLY_DAY", "4"))  # 0=Mon..6=Sun
WEEKLY_HOUR_LOCAL = int(_get_env("WEEKLY_HOUR", "12"))
WEEKLY_MINUTE = int(_get_env("WEEKLY_MINUTE", "0"))
# VK integration removed - only Telegram channels now
# Proxy settings
PROXY_URL = _get_env("PROXY_URL", "")
# Convert MSK (UTC+3) local hour to UTC for job queue
WEEKLY_HOUR_UTC = (WEEKLY_HOUR_LOCAL - 3) % 24

logger.info("Loaded .env from: %s", _DOTENV_PATH)

REENGAGE_TEXT = (
    "Мы очень скучаем без тебя 🥹\n"
    "Новая неделя, новые вечеринки 🥳\n"
    "Возвращайся скорее, будем делать тыц тыц тыц как в старые добрые 💃🕺🏻"
)

DATA_DIR = Path(__file__).parent / "data"
PERSISTENCE_FILE = DATA_DIR / "bot_data.pkl"

# ----------------------
# Helpers
# ----------------------

def ensure_data_dir() -> None:
    DATA_DIR.mkdir(exist_ok=True)


def week_key_for_date(dt: datetime) -> str:
    iso_year, iso_week, _ = dt.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def previous_week_key(now: datetime) -> str:
    last_week_date = now - timedelta(days=7)
    return week_key_for_date(last_week_date)


async def is_user_subscribed(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> tuple[bool, bool, bool]:
    """Проверить подписку пользователя на каналы и чат
    
    Returns:
        tuple[bool, bool, bool]: (канал 1, канал 2, чат)
    """
    channel1_ok = False
    channel2_ok = False
    chat_ok = False
    
    # Проверяем первый канал
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        channel1_ok = member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.warning("Failed to check subscription for user %s on %s: %s", user_id, CHANNEL_USERNAME, e)
    
    # Проверяем второй канал
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME_2, user_id)
        channel2_ok = member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.warning("Failed to check subscription for user %s on %s: %s", user_id, CHANNEL_USERNAME_2, e)
    
    # Проверяем чат/группу
    try:
        member = await context.bot.get_chat_member(CHAT_USERNAME, user_id)
        chat_ok = member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.warning("Failed to check chat membership for user %s on %s: %s", user_id, CHAT_USERNAME, e)
    
    return channel1_ok, channel2_ok, chat_ok


async def get_bot_channel_status(context: ContextTypes.DEFAULT_TYPE) -> str:
    try:
        bot_member = await context.bot.get_chat_member(CHANNEL_USERNAME, context.bot.id)
        if bot_member.status == "administrator":
            return f"Бот имеет права администратора в {CHANNEL_USERNAME} ✅"
        else:
            return f"⚠️ Бот не является администратором {CHANNEL_USERNAME}. Проверка подписки может работать некорректно."
    except Exception as e:
        logger.warning("Failed to get bot status in channel %s: %s", CHANNEL_USERNAME, e)
        return f"❌ Не удалось проверить статус бота в {CHANNEL_USERNAME}. Убедитесь, что бот добавлен в канал как администратор."


def get_known_users(context: ContextTypes.DEFAULT_TYPE) -> Set[int]:
    bd = context.bot_data
    if "known_users" not in bd:
        bd["known_users"] = set()
    return bd["known_users"]


def get_db_pool(context: ContextTypes.DEFAULT_TYPE):
    try:
        return context.application.bot_data.get("db_pool")
    except Exception:
        return None


# ----------------------
# Универсальный механизм рассылки
# ----------------------

# Telegram позволяет ботам ~30 сообщений/сек в сумме по всем чатам.
# Берём запас и шлём ~25/сек => пауза 0.04 сек. Это главное, что раньше ломало рассылку.
BROADCAST_DELAY_SEC = 0.04
# Сколько раз повторять при сетевых сбоях / TimedOut
BROADCAST_NETWORK_RETRIES = 3


async def _safe_send_one(send_callable, uid: int) -> str:
    """Пытается отправить сообщение одному пользователю.

    Возвращает одно из: 'ok', 'blocked', 'not_found', 'failed'.
    Сам обрабатывает RetryAfter (ждёт и повторяет) и сетевые сбои.
    """
    network_attempts = 0
    # Защита от бесконечных RetryAfter
    flood_attempts = 0
    while True:
        try:
            await send_callable(uid)
            return "ok"
        except Forbidden:
            # Пользователь заблокировал бота или удалил чат
            logger.info("Broadcast: user %s blocked the bot", uid)
            return "blocked"
        except RetryAfter as e:
            flood_attempts += 1
            wait = float(getattr(e, "retry_after", 1)) + 1.0
            if flood_attempts > 5:
                logger.warning("Broadcast: too many RetryAfter for %s, giving up", uid)
                return "failed"
            logger.info("Broadcast: flood wait %.1fs for %s", wait, uid)
            await asyncio.sleep(wait)
            continue
        except BadRequest as e:
            msg = str(e).lower()
            if (
                "chat not found" in msg
                or "user is deactivated" in msg
                or "peer_id_invalid" in msg
                or "bot was blocked" in msg
                or "user not found" in msg
            ):
                logger.info("Broadcast: user %s unreachable (%s)", uid, e)
                return "not_found"
            logger.warning("Broadcast BadRequest for %s: %s", uid, e)
            return "failed"
        except (TimedOut, NetworkError) as e:
            network_attempts += 1
            if network_attempts >= BROADCAST_NETWORK_RETRIES:
                logger.warning("Broadcast: network failure for %s after %d tries: %s",
                               uid, network_attempts, e)
                return "failed"
            await asyncio.sleep(1.5 * network_attempts)
            continue
        except TelegramError as e:
            logger.warning("Broadcast Telegram error for %s: %s", uid, e)
            return "failed"
        except Exception as e:
            logger.warning("Broadcast failed to %s: %s", uid, e)
            return "failed"


async def _collect_broadcast_recipients(context: ContextTypes.DEFAULT_TYPE) -> list[int]:
    """Возвращает полный актуальный список tg_id получателей.

    Источник правды — БД (таблица users). В дополнение берём in-memory кеш
    known_users, чтобы не потерять тех, кто только что нажал /start.
    """
    ids: Set[int] = set()
    pool = get_db_pool(context)
    if pool:
        try:
            db_ids = await get_all_user_ids(pool)
            ids.update(db_ids)
        except Exception as e:
            logger.warning("Broadcast: failed to load users from DB: %s", e)
    ids.update(get_known_users(context))
    return sorted(ids)


async def perform_broadcast(
    context: ContextTypes.DEFAULT_TYPE,
    send_callable,
    *,
    progress_message=None,
    progress_every: int = 25,
) -> dict:
    """Рассылает сообщение всем пользователям и возвращает подробную статистику.

    send_callable(uid) — корутина, делающая один вызов context.bot.send_* для конкретного uid.
    progress_message — (опц.) объект Message, который будет периодически обновляться прогрессом.
    """
    recipients = await _collect_broadcast_recipients(context)
    total = len(recipients)
    stats = {
        "total": total,
        "ok": 0,
        "blocked": 0,
        "not_found": 0,
        "failed": 0,
        "failed_ids": [],
    }
    if total == 0:
        return stats

    known = get_known_users(context)
    deactivated_ids: list[int] = []
    for idx, uid in enumerate(recipients, 1):
        result = await _safe_send_one(send_callable, uid)
        stats[result] += 1
        if result in ("blocked", "not_found"):
            known.discard(uid)
            deactivated_ids.append(uid)
        elif result == "failed":
            stats["failed_ids"].append(uid)

        # Прогресс в админ-сообщении
        if progress_message is not None and (idx % progress_every == 0 or idx == total):
            try:
                await progress_message.edit_text(
                    f"📤 Рассылка идёт...\n"
                    f"Обработано: {idx}/{total}\n"
                    f"✅ Доставлено: {stats['ok']}\n"
                    f"🚫 Заблокировали бота: {stats['blocked']}\n"
                    f"🗑 Недоступны: {stats['not_found']}\n"
                    f"⚠️ Ошибок: {stats['failed']}"
                )
            except Exception:
                pass

        # Защита от флуд-лимита
        await asyncio.sleep(BROADCAST_DELAY_SEC)

    # Деактивируем в БД всех, кто заблокировал бота или недоступен
    if deactivated_ids:
        pool = get_db_pool(context)
        if pool:
            try:
                await deactivate_users(pool, deactivated_ids)
                logger.info("Broadcast: deactivated %d users in DB", len(deactivated_ids))
            except Exception as e:
                logger.warning("Broadcast: failed to deactivate users: %s", e)

    return stats


def format_broadcast_report(stats: dict, *, extra: str = "") -> str:
    """Человеко-читаемый отчёт по результатам рассылки."""
    lines = [
        "✅ **Рассылка завершена**",
        "",
        f"👥 Всего получателей: **{stats['total']}**",
        f"✅ Доставлено: **{stats['ok']}**",
        f"🚫 Заблокировали бота: **{stats['blocked']}**",
        f"🗑 Удалены / недоступны: **{stats['not_found']}**",
        f"⚠️ Ошибок отправки: **{stats['failed']}**",
    ]
    failed_ids = stats.get("failed_ids") or []
    if failed_ids:
        shown = ", ".join(str(u) for u in failed_ids[:20])
        more = "" if len(failed_ids) <= 20 else f" и ещё {len(failed_ids) - 20}"
        lines.append("")
        lines.append(f"ID с ошибками: `{shown}`{more}")
    if extra:
        lines.append("")
        lines.append(extra)
    return "\n".join(lines)


async def load_user_data_from_db(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Загружает данные пользователя из БД в context.user_data"""
    logger.info("=== LOAD_USER_DATA_FROM_DB START ===")
    logger.info("Loading data for user_id: %s", user_id)
    
    pool = get_db_pool(context)
    logger.info("DB pool exists: %s", pool is not None)
    
    if not pool:
        logger.warning("No DB pool available for user %s", user_id)
        logger.info("Setting registered=False due to no DB pool")
        context.user_data["registered"] = False
        logger.info("=== LOAD_USER_DATA_FROM_DB END (no pool) ===")
        return
    
    try:
        logger.info("Calling get_user from DB...")
        user_in_db = await get_user(pool, user_id)
        logger.info("DB query result for user %s: %s", user_id, user_in_db)
        
        if user_in_db:
            # Загружаем все доступные данные
            context.user_data["name"] = user_in_db.get("name")
            context.user_data["gender"] = user_in_db.get("gender")
            context.user_data["age"] = user_in_db.get("age")
            
            # Проверяем полноту регистрации - нужны минимум имя, пол и возраст
            has_required_data = (
                user_in_db.get("name") and 
                user_in_db.get("gender") and 
                user_in_db.get("age") is not None
            )
            
            if has_required_data:
                context.user_data["registered"] = True
                logger.info("User %s fully registered - loaded from DB: name=%s, gender=%s, age=%s", 
                           user_id, user_in_db.get("name"), user_in_db.get("gender"), user_in_db.get("age"))
            else:
                context.user_data["registered"] = False
                logger.info("User %s in DB but incomplete: name=%s, gender=%s, age=%s", 
                           user_id, user_in_db.get("name"), user_in_db.get("gender"), user_in_db.get("age"))
        else:
            # Пользователя нет в БД - сбрасываем регистрацию
            logger.info("User NOT found in DB - clearing all registration data")
            context.user_data["registered"] = False
            context.user_data.pop("name", None)
            context.user_data.pop("gender", None)
            context.user_data.pop("age", None)
            context.user_data.pop("registration_step", None)
            logger.info("User %s not found in DB - reset registration", user_id)
            logger.info("Final user_data after reset: registered=%s, name=%s, gender=%s, age=%s", 
                       context.user_data.get("registered"), 
                       context.user_data.get("name"),
                       context.user_data.get("gender"),
                       context.user_data.get("age"))
        
        logger.info("=== LOAD_USER_DATA_FROM_DB END ===")
    except Exception as e:
        logger.warning("Failed to load user data from DB for user %s: %s", user_id, e)
        logger.info("Setting registered=False due to DB error")
        context.user_data["registered"] = False
        logger.info("=== LOAD_USER_DATA_FROM_DB END (error) ===")




# Владельцы бота (задаются в .env) — имеют полный доступ, включая управление ролями
OWNER_IDS: Set[int] = {i for i in (ADMIN_USER_ID, ADMIN_USER_ID_2, ADMIN_USER_ID_3) if i}


def is_owner(user_id: int) -> bool:
    """Владелец — задаётся только через .env, полный доступ ко всем функциям"""
    return bool(user_id) and user_id in OWNER_IDS


def get_admins(context: ContextTypes.DEFAULT_TYPE) -> Set[int]:
    """Владельцы (.env) + администраторы, назначенные владельцем (кэш из БД)"""
    bd = context.bot_data
    sub_admins: Set[int] = bd.get("sub_admins", set())
    return OWNER_IDS | sub_admins


async def refresh_admins_cache(context_or_app) -> None:
    """Перезагрузить список администраторов из БД в кэш bot_data"""
    bot_data = context_or_app.bot_data
    pool = bot_data.get("db_pool")
    if not pool:
        return
    try:
        ids = await db_get_admin_ids(pool)
        bot_data["sub_admins"] = set(ids)
    except Exception as e:
        logger.warning("Failed to refresh admins cache: %s", e)


def build_manage_admins_view(context: ContextTypes.DEFAULT_TYPE):
    """Собрать текст и кнопки для экрана управления ролями (только для владельца)"""
    sub_admins = sorted(context.bot_data.get("sub_admins", set()))

    text = "👑 **Управление ролями**\n\n"

    text += "**Владельцы** _(полный доступ, задаются в .env)_\n"
    for owner_id in sorted(OWNER_IDS):
        text += f"• `{owner_id}` 👑\n"

    text += "\n**Администраторы**\n"
    if sub_admins:
        for admin_id in sub_admins:
            text += f"• `{admin_id}` 🛡\n"
    else:
        text += "_Пока никого не назначено_\n"

    kb = []
    for admin_id in sub_admins:
        kb.append([InlineKeyboardButton(f"❌ Снять {admin_id}", callback_data=f"admin:remove_admin:{admin_id}")])
    kb.append([InlineKeyboardButton("➕ Добавить администратора", callback_data="admin:add_admin_start")])
    kb.append([InlineKeyboardButton("◀️ Назад в панель", callback_data="admin:refresh")])

    return text, kb


# ----------------------
# VK helpers
# ----------------------

VK_PROFILE_RE = re.compile(r"(?:https?://)?(?:www\.)?vk\.com/(id\d+|[A-Za-z0-9_\.]+)", re.IGNORECASE)


def extract_vk_id(text: str) -> Optional[str]:
    if not text:
        return None
    text = text.strip()
    m = VK_PROFILE_RE.search(text)
    if m:
        return m.group(1)
    # if numeric id
    if text.isdigit():
        return f"id{text}"
    return None


# VK membership check removed


# VK subscription check removed


# VK broadcast removed


# ----------------------
# Handlers
# ----------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return
    
    get_known_users(context).add(user.id)
    
    # НЕ создаем запись автоматически - только загружаем существующие данные
    pool = get_db_pool(context)
    
    # Загружаем данные пользователя из БД
    if pool:
        await load_user_data_from_db(context, user.id)
    else:
        logger.warning("No DB pool - cannot load user data")
        context.user_data["registered"] = False
    
    # Проверяем, завершена ли регистрация пользователя более надежно
    user_data = context.user_data
    is_registered = (
        user_data.get("registered") == True and 
        user_data.get("name") and 
        user_data.get("gender") and 
        user_data.get("age") is not None
    )
    
    # Проверяем незавершенную регистрацию
    has_partial_data = user_data.get("name") or user_data.get("gender") or user_data.get("age") is not None
    
    logger.info("=== START COMMAND DEBUG ===")
    logger.info("User ID: %s", user.id)
    logger.info("DB Pool exists: %s", pool is not None)
    logger.info("user_data.registered: %s", user_data.get("registered"))
    logger.info("user_data.name: %s", user_data.get("name"))
    logger.info("user_data.gender: %s", user_data.get("gender"))
    logger.info("user_data.age: %s", user_data.get("age"))
    logger.info("is_registered: %s", is_registered)
    logger.info("has_partial_data: %s", has_partial_data)
    logger.info("=== END DEBUG ===")
    
    if is_registered:
        # Пользователь уже зарегистрирован - показываем сообщение и кнопку меню
        # Сбрасываем флаг регистрации если он остался
        user_data.pop("registration_step", None)
        user_data.pop("awaiting_username_check", None)
        
        kb = [[InlineKeyboardButton("🎉 Перейти в меню", callback_data="back_to_menu")]]
        await update.effective_chat.send_message(
            "🎉 Вы уже зарегистрированы у нас на вечеринках!\n\n"
            f"👤 Ваши данные:\n"
            f"• Имя: {user_data.get('name', 'Не указано')}\n"
            f"• Пол: {'Мужской' if user_data.get('gender') == 'male' else 'Женский' if user_data.get('gender') == 'female' else 'Не указан'}\n"
            f"• Возраст: {user_data.get('age', 'Не указан')} лет\n\n"
            "Добро пожаловать обратно! 🥳",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return
    
    # Если есть частичные данные, продолжаем с того места где остановились
    if has_partial_data and not is_registered:
        # Определяем на каком этапе остановились
        if not user_data.get("name"):
            user_data["registration_step"] = "name"
            await update.effective_chat.send_message(
                "👋 Продолжим регистрацию!\n\n"
                "Как вас зовут? (Введите ваше имя)"
            )
        elif not user_data.get("gender"):
            user_data["registration_step"] = "gender"
            kb = [
                [InlineKeyboardButton("👨 Мужской", callback_data="gender_male")],
                [InlineKeyboardButton("👩 Женский", callback_data="gender_female")]
            ]
            await update.effective_chat.send_message(
                f"Отлично, {user_data.get('name')}! 😊\n\n"
                "Укажите ваш пол:",
                reply_markup=InlineKeyboardMarkup(kb)
            )
        elif user_data.get("age") is None:
            user_data["registration_step"] = "age"
            await update.effective_chat.send_message(
                "Последний шаг! 🎯\n\n"
                "Укажите ваш возраст (числом):\n"
                "Например: 25"
            )
        return
    
    # Начинаем регистрацию с начала
    user_data["registration_step"] = "name"
    logger.info("Starting registration for user %s", user.id)
    await update.effective_chat.send_message(
        "🎉 Добро пожаловать на наши вечеринки!\n\n"
        "Для начала давайте знакомиться.\n"
        "Как вас зовут? (Введите ваше имя)"
    )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать главное меню с кнопками и статусами подписки"""
    user = update.effective_user
    if not user:
        return

    # Добавляем пользователя в известные
    get_known_users(context).add(user.id)
    
    # Загружаем данные пользователя из БД
    await load_user_data_from_db(context, user.id)

    # Проверяем регистрацию более надежно
    user_data = context.user_data
    is_registered = (
        user_data.get("registered") == True and 
        user_data.get("name") and 
        user_data.get("gender") and 
        user_data.get("age") is not None
    )
    
    logger.info("Menu command for user %s: registered=%s, name=%s, gender=%s, age=%s", 
               user.id, user_data.get("registered"), user_data.get("name"), 
               user_data.get("gender"), user_data.get("age"))
    
    if not is_registered:
        logger.info("User %s not registered - showing registration message", user.id)
        await update.effective_chat.send_message(
            "❗ Для использования меню необходимо пройти регистрацию.\n\n"
            "Нажмите /start для начала регистрации."
        )
        return

    # Показываем главное меню
    await show_main_menu(update, context)


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать главное меню с текущей афишей и навигацией"""
    user = update.effective_user
    if not user:
        return
    
    # Загружаем данные пользователя из БД (в том числе VK ID)
    await load_user_data_from_db(context, user.id)
    
    # КРИТИЧЕСКИ ВАЖНО: Проверяем регистрацию перед показом меню!
    user_data = context.user_data
    is_registered = (
        user_data.get("registered") == True and 
        user_data.get("name") and 
        user_data.get("gender") and 
        user_data.get("age") is not None
    )
    
    logger.info("show_main_menu for user %s: registered=%s", user.id, is_registered)
    
    if not is_registered:
        logger.info("User %s not registered in show_main_menu - redirecting to registration", user.id)
        await update.effective_chat.send_message(
            "❗ Для доступа к меню необходимо пройти регистрацию.\n\n"
            "Нажмите /start для начала регистрации."
        )
        return
    
    # Получаем все афиши
    all_posters = context.bot_data.get("all_posters", [])
    current_poster = context.bot_data.get("poster")
    
    # Если есть текущая афиша, но её нет в списке всех афиш, добавляем
    if current_poster and current_poster not in all_posters:
        all_posters.append(current_poster)
        context.bot_data["all_posters"] = all_posters
    
    if not all_posters:
        # Нет афиш - показываем заглушку
        kb = []
        if user.id in get_admins(context):
            kb.append([InlineKeyboardButton("🛠 Админ-панель", callback_data="open_admin")])
        
        await update.effective_chat.send_message(
            "🎭 Пока нет доступных афиш\n\n"
            "Следите за обновлениями!",
            reply_markup=InlineKeyboardMarkup(kb) if kb else None
        )
        return
    
    # Получаем текущий индекс афиши (по умолчанию - последняя)
    if "current_poster_index" not in context.user_data and all_posters:
        context.user_data["current_poster_index"] = len(all_posters) - 1
    current_poster_index = context.user_data.get("current_poster_index", 0)
    if current_poster_index >= len(all_posters):
        current_poster_index = len(all_posters) - 1
        context.user_data["current_poster_index"] = current_poster_index
    elif current_poster_index < 0:
        current_poster_index = 0
        context.user_data["current_poster_index"] = current_poster_index
    
    # Показываем текущую афишу
    poster = all_posters[current_poster_index]
    
    # Создаем кнопки навигации и действий
    nav_buttons = []
    
    # Навигация по афишам (если больше одной)
    if len(all_posters) > 1:
        nav_row = []
        if current_poster_index > 0:
            nav_row.append(InlineKeyboardButton("⬅️ Предыдущая", callback_data="poster_prev"))
        if current_poster_index < len(all_posters) - 1:
            nav_row.append(InlineKeyboardButton("➡️ Следующая", callback_data="poster_next"))
        if nav_row:
            nav_buttons.append(nav_row)
    
    # Основные кнопки действий в правильном порядке
    action_buttons = []
    
    # 1. Кнопка билетов (если есть ссылка)
    if poster.get("ticket_url"):
        action_buttons.append([InlineKeyboardButton("🎫 Купить билет", url=poster["ticket_url"])])
    
    # Админские кнопки
    if user and user.id in get_admins(context):
        admin_row = []
        admin_row.append(InlineKeyboardButton("🛠 Админ-панель", callback_data="open_admin"))
        if len(all_posters) > 0:
            admin_row.append(InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_poster:{current_poster_index}"))
        action_buttons.append(admin_row)
    
    # Собираем все кнопки
    all_buttons = nav_buttons + action_buttons
    
    # Отправляем или редактируем афишу
    try:
        caption = poster.get("caption", "")
        if len(all_posters) > 1:
            caption += f"\n\n📍 Афиша {current_poster_index + 1} из {len(all_posters)}"
        
        file_id = poster.get("file_id")
        photo_path = poster.get("photo_path")
        
        # Проверяем что file_id существует
        if not file_id:
            logger.error("Poster has no file_id: %s", poster)
            await update.effective_chat.send_message(
                "❌ Ошибка: афиша не содержит фото.\n\nПожалуйста, пересоздайте афишу.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛠 Админ-панель", callback_data="open_admin")]]) if user.id in get_admins(context) else None
            )
            return
        
        logger.info("Sending poster with file_id: %s, photo_path: %s", file_id, photo_path)
        
        # Убираем админскую клавиатуру если была
        keyboard_remove_msg = await update.effective_chat.send_message(
            "📋 Главное меню", 
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Пытаемся отправить афишу - сначала с file_id, если не работает - с локального файла
        photo_sent = False
        
        # Попытка 1: Используем Telegram file_id
        if file_id and not file_id.startswith('/'):
            try:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=file_id,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup(all_buttons)
                )
                photo_sent = True
                logger.info("Poster sent successfully using file_id")
            except Exception as e:
                logger.warning("Failed to send with file_id: %s, trying local file...", e)
        
        # Попытка 2: Используем локальный файл если file_id не сработал
        if not photo_sent and photo_path:
            try:
                local_file = Path(__file__).parent / "project" / "public" / photo_path.lstrip("/")
                if local_file.exists():
                    with open(local_file, 'rb') as photo_file:
                        await context.bot.send_photo(
                            chat_id=update.effective_chat.id,
                            photo=photo_file,
                            caption=caption,
                            reply_markup=InlineKeyboardMarkup(all_buttons)
                        )
                    photo_sent = True
                    logger.info("Poster sent successfully using local file: %s", local_file)
                else:
                    logger.error("Local file not found: %s", local_file)
            except Exception as e:
                logger.error("Failed to send with local file: %s", e)
        
        if not photo_sent:
            raise Exception("Failed to send poster with both file_id and local file")
        
        # Удаляем сообщение "Главное меню" чтобы не дублировать
        try:
            await keyboard_remove_msg.delete()
        except:
            pass  # Игнорируем ошибки удаления
            
    except Exception as e:
        logger.exception("Failed to send poster: %s", e)
        await update.effective_chat.send_message(
            "❌ Ошибка при загрузке афиши.\n\n"
            "Возможные причины:\n"
            "• Фото было удалено из Telegram\n"
            "• File ID устарел\n\n"
            "Решение: пересоздайте афишу через /admin",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛠 Админ-панель", callback_data="open_admin")]]) if user and user.id in get_admins(context) else None
        )


async def show_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user:
        await update.effective_chat.send_message(f"Ваш ID: {user.id}")


async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    try:
        await query.answer()
        user = query.from_user
        data = query.data
        
        logger.info("Button pressed by user %s: %s", user.id, data)

        # Загружаем данные пользователя из БД
        await load_user_data_from_db(context, user.id)

        if data == "check_all":
            tg1_ok, tg2_ok, chat_ok = await is_user_subscribed(context, user.id)

            # Формируем сообщение с простым форматом
            lines = ["🔍 **Статус подписок:**\n"]
            
            # Первый Telegram канал
            tg1_icon = "✅" if tg1_ok else "❌"
            tg1_url = f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"
            lines.append(f"{tg1_icon} [{CHANNEL_USERNAME}]({tg1_url}) (MEDIA FAM)")
            
            # Второй Telegram канал
            tg2_icon = "✅" if tg2_ok else "❌"
            tg2_url = f"https://t.me/{CHANNEL_USERNAME_2.lstrip('@')}"
            lines.append(f"{tg2_icon} [THE FAMILY]({tg2_url})")
            
            # Чат/группа
            chat_icon = "✅" if chat_ok else "❌"
            chat_url = f"https://t.me/{CHAT_USERNAME.lstrip('@')}"
            lines.append(f"{chat_icon} [Family Guests 💬]({chat_url})")
            
            # Итоговый статус - нужны все три
            all_ok = tg1_ok and tg2_ok and chat_ok
            if all_ok:
                lines.append("\n🎉 **Все проверки пройдены!**")
            else:
                lines.append("\n⚠️ **Требуется подписка на все каналы и чат**")
            
            text = "\n".join(lines)
            
            # Кнопки действий
            btns = []
            
            # Кнопки подписки (если не подписан)
            if not tg1_ok:
                btns.append([InlineKeyboardButton("📢 Подписаться на MEDIA FAM", url=tg1_url)])
            if not tg2_ok:
                btns.append([InlineKeyboardButton("🎉 Подписаться на THE FAMILY", url=tg2_url)])
            if not chat_ok:
                btns.append([InlineKeyboardButton("💬 Вступить в чат Family Guests", url=chat_url)])
            
            btns.append([InlineKeyboardButton("🔄 Перепроверить", callback_data="check_all")])
            btns.append([InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")])
            
            # Удаляем старое сообщение и отправляем новое
            try:
                await query.message.delete()
            except Exception:
                pass
            await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text=text, 
                reply_markup=InlineKeyboardMarkup(btns), 
                parse_mode="Markdown"
                )
        
        elif data == "show_current_poster":
            # Показать актуальную афишу (последнюю)
            all_posters = context.bot_data.get("all_posters", [])
            if all_posters:
                context.user_data["current_poster_index"] = len(all_posters) - 1
            # UX: удаляем старое сообщение и отправляем новое фото афиши
            try:
                await query.message.delete()
            except Exception:
                pass
            await show_main_menu(update, context)
        
        elif data == "poster":
            # Показать актуальную афишу (последнюю) - для совместимости
            all_posters = context.bot_data.get("all_posters", [])
            if all_posters:
                context.user_data["current_poster_index"] = len(all_posters) - 1
            try:
                await query.message.delete()
            except Exception:
                pass
            await show_main_menu(update, context)
        
        elif data == "open_admin":
            # Открыть админ-панель через callback
            await admin_panel(update, context)
        
        elif data == "back_to_menu":
            # Загружаем данные пользователя из БД перед показом меню
            await load_user_data_from_db(context, user.id)
            
            # Сбрасываем индекс афиши на последнюю (самую новую)
            all_posters = context.bot_data.get("all_posters", [])
            if all_posters:
                context.user_data["current_poster_index"] = len(all_posters) - 1
            try:
                await query.message.delete()
            except Exception:
                pass
            await show_main_menu(update, context)
        
        elif data == "poster_prev":
            # Переход к предыдущей афише
            all_posters = context.bot_data.get("all_posters", [])
            current_index = context.user_data.get("current_poster_index", len(all_posters) - 1 if all_posters else 0)
            if current_index > 0:
                context.user_data["current_poster_index"] = current_index - 1
            try:
                await query.message.delete()
            except Exception:
                pass
            await show_main_menu(update, context)
        
        elif data.startswith("delete_poster:"):
            # Удаление афиши по индексу из главного меню
            try:
                poster_index = int(data.split(":", 1)[1])
                all_posters = context.bot_data.get("all_posters", [])
                
                if poster_index < 0 or poster_index >= len(all_posters):
                    await query.answer("❌ Афиша не найдена")
                    return
                
                poster = all_posters[poster_index]
                poster_id = poster.get("id")
                
                if not poster_id:
                    await query.answer("❌ ID афиши не найден")
                    return
                
                # Подтверждение удаления
                await query.edit_message_caption(
                    caption=f"❓ Удалить эту афишу?\n\n{poster.get('caption', '')[:100]}...",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete:{poster_id}")],
                        [InlineKeyboardButton("❌ Отмена", callback_data="back_to_menu")]
                    ])
                )
            except Exception as e:
                logger.error(f"Error in delete_poster handler: {e}")
                await query.answer(f"❌ Ошибка: {e}")
        
        elif data.startswith("confirm_delete:"):
            # Подтверждение удаления конкретной афиши
            try:
                poster_id = int(data.split(":", 1)[1])
                pool = get_db_pool(context)
                
                if not pool:
                    await query.edit_message_text("❌ База данных недоступна")
                    return
                
                # Получаем афишу для удаления
                poster = await get_poster_by_id(pool, poster_id)
                if not poster:
                    await query.edit_message_text("❌ Афиша не найдена")
                    return
                
                # Удаляем фото из папки project/public/posters/
                file_id = poster.get("file_id", "")
                if file_id.startswith("/posters/") or file_id.startswith("posters/"):
                    try:
                        file_path = Path(__file__).parent / "project" / "public" / file_id.lstrip("/")
                        if file_path.exists():
                            file_path.unlink()
                            logger.info(f"Deleted photo file: {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to delete photo file: {e}")
                
                # Удаляем из БД
                try:
                    await db_delete_poster(pool, poster_id)
                    logger.info(f"Deleted poster from DB: {poster_id}")
                except Exception as e:
                    logger.error(f"Failed to delete poster from DB: {e}")
                    await query.edit_message_text(f"❌ Ошибка удаления из БД: {e}")
                    return
                
                # Обновляем локальный кэш
                all_posters = context.bot_data.get("all_posters", [])
                context.bot_data["all_posters"] = [p for p in all_posters if p.get("id") != poster_id]
                
                current_poster = context.bot_data.get("poster")
                if current_poster and current_poster.get("id") == poster_id:
                    # Загружаем новую текущую афишу из БД
                    active_posters = await get_active_posters(pool)
                    if active_posters:
                        context.bot_data["poster"] = active_posters[-1]
                        context.bot_data["all_posters"] = active_posters
                    else:
                        context.bot_data.pop("poster", None)
                        context.bot_data["all_posters"] = []
                    
                caption = poster.get("caption", "Без описания")[:50]
                remaining = len(context.bot_data.get("all_posters", []))
                
                await query.edit_message_text(
                    f"✅ **Афиша удалена:**\n{caption}\n\n"
                    f"Осталось активных афиш: {remaining}",
                    parse_mode="Markdown"
                )
            except (ValueError, IndexError) as e:
                logger.error(f"Error deleting poster: {e}")
                await query.edit_message_text(f"❌ Ошибка при удалении афиши: {e}")
        
        elif data == "cancel_delete":
            await query.edit_message_text("❌ Удаление отменено")
        
        elif data == "poster_next":
            # Переход к следующей афише
            all_posters = context.bot_data.get("all_posters", [])
            current_index = context.user_data.get("current_poster_index", len(all_posters) - 1 if all_posters else 0)
            if current_index < len(all_posters) - 1:
                context.user_data["current_poster_index"] = current_index + 1
            try:
                await query.message.delete()
            except Exception:
                pass
            await show_main_menu(update, context)
        
        elif data.startswith("gender_"):
            # Обработка выбора пола
            gender = data.split("_", 1)[1]
            context.user_data["gender"] = gender
            context.user_data["registration_step"] = "age"
            
            # Сохраняем пол в БД
            pool = get_db_pool(context)
            if pool:
                try:
                    await upsert_user(pool, tg_id=user.id, gender=gender, username=user.username)
                    logger.info("Gender saved to DB for user %s: %s", user.id, gender)
                except Exception as e:
                    logger.warning("Failed to save gender to DB: %s", e)
            
            gender_text = {
                "male": "мужской",
                "female": "женский"
            }.get(gender, "")
            
            await query.edit_message_text(
                f"Пол: {gender_text} ✅\n\n"
                "Теперь укажите ваш возраст (только число)\n"
                "Например: 18"
            )
        
        elif data == "past_event":
            # Уведомление о прошедшем мероприятии
            await query.answer("Это мероприятие уже прошло 📅")
        
        elif data.startswith("admin:"):
            sub = data.split(":", 1)[1]
            if user.id not in get_admins(context):
                await query.edit_message_text("Недостаточно прав.")
                return
            
            # Функции, доступные только владельцу
            owner_only_subs = {"check_by_username", "users_count", "manage_admins", "add_admin_start"}
            if (sub in owner_only_subs or sub.startswith("remove_admin:")) and not is_owner(user.id):
                await query.answer("Доступно только владельцу", show_alert=True)
                return
            
            if sub == "manage_admins":
                context.user_data.pop("awaiting_new_admin_id", None)
                text, kb = build_manage_admins_view(context)
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
                return
            
            elif sub == "add_admin_start":
                context.user_data["awaiting_new_admin_id"] = True
                await query.edit_message_text(
                    "➕ **Новый администратор**\n\n"
                    "Пришлите один из вариантов:\n"
                    "• Telegram ID (число)\n"
                    "• @username\n"
                    "• Перешлите сюда его сообщение\n\n"
                    "И он сразу получит доступ к панели администратора.\n\n"
                    "💡 Узнать свой ID можно командой /id.\n"
                    "⚠️ Поиск по @username работает, только если пользователь хотя бы раз запускал бота.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="admin:manage_admins")]]),
                    parse_mode="Markdown"
                )
                return
            
            elif sub.startswith("remove_admin:"):
                target_id = int(sub.split(":", 1)[1])
                pool = get_db_pool(context)
                if pool:
                    try:
                        await db_remove_admin(pool, target_id)
                        await refresh_admins_cache(context)
                    except Exception as e:
                        logger.warning("Failed to remove admin %s: %s", target_id, e)
                await query.answer(f"Администратор {target_id} снят ✅")
                text, kb = build_manage_admins_view(context)
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
                return
            
            if sub == "create_poster":
                # init draft
                ud = context.user_data
                ud["poster_draft"] = {"step": "photo", "file_id": None, "caption": None, "ticket_url": None}
                await query.edit_message_text(
                    "Шаг 1/4: пришлите фото афиши",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("◀️ Назад в панель", callback_data="admin:back_to_panel")],
                        [InlineKeyboardButton("❌ Отмена", callback_data="admin:cancel_poster")],
                    ]),
                )
            
            elif sub == "broadcast_now":
                # Проверяем наличие афиши
                if not context.bot_data.get("all_posters"):
                    await query.edit_message_text("❌ Афиш нет. Сначала создайте афишу.")
                    return
                await query.edit_message_text("📤 Рассылка афиши запускается...")
                progress_msg = query.message
                stats = await do_weekly_broadcast(context, progress_message=progress_msg)
                if stats is None:
                    await query.edit_message_text("❌ Нет афиш или получателей")
                else:
                    try:
                        await query.edit_message_text(
                            format_broadcast_report(stats),
                            parse_mode="Markdown",
                        )
                    except Exception:
                        await query.edit_message_text(format_broadcast_report(stats))
            
            elif sub == "set_ticket":
                context.user_data["awaiting_ticket"] = True
                await query.edit_message_text("Пришлите ссылку для кнопки «Купить билет»")
            
            elif sub == "delete_poster":
                # Показываем список афиш для удаления
                pool = get_db_pool(context)
                if pool:
                    try:
                        active_posters = await get_active_posters(pool)
                        if not active_posters:
                            await query.edit_message_text("❌ Нет активных афиш для удаления")
                            return
                        
                        # Создаём кнопки для каждой афиши
                        buttons = []
                        for poster in active_posters:
                            caption = poster.get("caption", "Без описания")[:50]
                            if len(poster.get("caption", "")) > 50:
                                caption += "..."
                            created = poster.get("created_at", "")
                            if isinstance(created, str):
                                created = created[:10]  # Только дата
                            
                            button_text = f"🗑 {caption} ({created})"
                            buttons.append([InlineKeyboardButton(button_text, callback_data=f"confirm_delete:{poster['id']}")])
                        
                        # Кнопка отмены
                        buttons.append([InlineKeyboardButton("❌ Отмена", callback_data="admin:back_to_panel")])
                        
                        await query.edit_message_text(
                            "🗑 **Выберите афишу для удаления:**\n\n"
                            f"Всего активных афиш: {len(active_posters)}",
                            reply_markup=InlineKeyboardMarkup(buttons),
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        logger.error(f"Failed to list posters for deletion: {e}")
                        await query.edit_message_text(f"❌ Ошибка загрузки афиш: {e}")
                else:
                    await query.edit_message_text("❌ База данных недоступна")
            
            elif sub == "broadcast_text":
                context.user_data["awaiting_broadcast_text"] = True
                context.user_data["broadcast_button_url"] = None
                await query.edit_message_text(
                    "📢 **Рассылка всем пользователям**\n\n"
                    "Вы можете отправить:\n"
                    "• 📝 Просто текст\n"
                    "• 🖼 Только фото\n"
                    "• 🖼📝 Фото с текстом (в caption)\n\n"
                    "💡 **Для добавления кнопки со ссылкой:**\n"
                    "Отправьте текст в формате:\n"
                    "`Ваш текст | Текст кнопки | https://ссылка`\n\n"
                    "**Пример:**\n"
                    "`Новая вечеринка! | Купить билет | https://example.com`\n\n"
                    "Отправьте сообщение:",
                    parse_mode="Markdown"
                )
            
            elif sub == "stats":
                count = len(get_known_users(context))
                await query.edit_message_text(f"Пользователей: {count}")
            
            elif sub == "back_to_panel":
                context.user_data.pop("poster_draft", None)
                await admin_panel(update, context)
            
            elif sub == "confirm_poster":
                draft = context.user_data.get("poster_draft") or {}
                # Validate poster before saving
                if not draft.get("file_id"):
                    await query.edit_message_text("❌ Не загружено фото афиши. Начните заново.")
                    return
                caption_ok = is_valid_caption(draft.get("caption") or "")
                link_ok = (not draft.get("ticket_url")) or is_valid_url(draft.get("ticket_url"))
                if not caption_ok:
                    await query.edit_message_text("❌ Слишком длинная подпись. Максимум 1024 символа.")
                    return
                if not link_ok:
                    await query.edit_message_text("❌ Некорректная ссылка на билеты. Укажите URL формата https://...")
                    return
                
                # Сохраняем афишу в БД (теперь с путем к фото)
                pool = get_db_pool(context)
                poster_id = None
                if pool:
                    try:
                        poster_id = await create_poster(
                            pool,
                            file_id=draft.get("photo_path") or draft["file_id"],  # Используем photo_path если есть
                            caption=draft.get("caption") or "",
                            ticket_url=draft.get("ticket_url")
                        )
                        logger.info("Poster saved to DB with ID: %s, photo_path: %s", poster_id, draft.get("photo_path"))
                    except Exception as e:
                        logger.error("Failed to save poster to DB: %s", e)
                        await query.edit_message_text(f"❌ Ошибка сохранения в БД: {e}")
                        return
                
                # Также сохраняем в bot_data для обратной совместимости
                poster = {
                    "id": poster_id,
                    "file_id": draft["file_id"], 
                    "photo_path": draft.get("photo_path"),  # Добавляем путь к фото
                    "caption": draft.get("caption") or "", 
                    "ticket_url": draft.get("ticket_url")
                }
                context.bot_data["poster"] = poster
                
                # Добавляем афишу в список всех афиш
                all_posters = context.bot_data.get("all_posters", [])
                all_posters.append(poster)
                context.bot_data["all_posters"] = all_posters
                
                # Сбрасываем индекс для всех пользователей на последнюю афишу
                # чтобы новая афиша показывалась сразу
                for uid in context.application.user_data:
                    user_data = context.application.user_data[uid]
                    user_data["current_poster_index"] = len(all_posters) - 1
                
                context.user_data.pop("poster_draft", None)
                # Опубликовать в чат админу одним сообщением (фото+текст+кнопка)
                rm = None
                if poster.get("ticket_url"):
                    rm = InlineKeyboardMarkup([[InlineKeyboardButton("Купить билет", url=poster["ticket_url"])]])
                await context.bot.send_photo(
                    chat_id=query.message.chat_id, 
                    photo=poster["file_id"], 
                    caption=poster.get("caption", ""), 
                    reply_markup=rm
                )
                
                db_status = f"💾 ID в БД: {poster_id}" if poster_id else "⚠️ Не сохранено в БД"
                await query.edit_message_text(
                    f"✅ Афиша сохранена и опубликована!\n\n"
                    f"{db_status}\n"
                    f"Всего афиш: {len(all_posters)}"
                )
            
            elif sub == "cancel_poster":
                context.user_data.pop("poster_draft", None)
                await query.edit_message_text("Создание афиши отменено ❌")
            
            elif sub == "users_count":
                # Показать количество пользователей
                pool = get_db_pool(context)
                if pool:
                    try:
                        stats = await get_user_stats(pool)
                        text = f"👥 **Статистика пользователей**\n\n"
                        text += f"• Всего пользователей: {stats.get('total_users', 0)}\n"
                        text += f"• Мужчин: {stats.get('male_users', 0)}\n"
                        text += f"• Женщин: {stats.get('female_users', 0)}\n"
                        text += f"• Зарегистрировано сегодня: {stats.get('today_registrations', 0)}"
                    except Exception as e:
                        text = f"❌ Ошибка получения статистики: {e}"
                else:
                    text = f"👥 Пользователей в кеше: {len(get_known_users(context))}"
                
                kb = [[InlineKeyboardButton("🔙 Назад в панель", callback_data="admin:refresh")]]
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
            
            elif sub == "list_posters":
                # Показать список всех афиш
                all_posters = context.bot_data.get("all_posters", [])
                if not all_posters:
                    text = "📋 Список афиш пуст"
                else:
                    text = f"📋 **Список всех афиш ({len(all_posters)}):**\n\n"
                    current_poster = context.bot_data.get("poster")
                    
                    for i, poster in enumerate(all_posters):
                        caption = poster.get("caption", "Без описания")
                        if len(caption) > 40:
                            caption = caption[:40] + "..."
                        
                        status = "🟢 ТЕКУЩАЯ" if poster == current_poster else "⚪"
                        ticket_status = "🎫" if poster.get("ticket_url") else "❌"
                        
                        text += f"{i+1}. {status} {caption}\n   Билеты: {ticket_status}\n\n"
                
                kb = [[InlineKeyboardButton("🔙 Назад в панель", callback_data="admin:refresh")]]
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
            
            elif sub == "check_by_username":
                # Проверка подписки по username/ID в режиме непрерывной проверки
                context.user_data["awaiting_username_check"] = True
                context.user_data["continuous_check_mode"] = True
                kb = [[InlineKeyboardButton("🔙 Завершить проверку", callback_data="admin:stop_check")]]
                await query.edit_message_text(
                    "🔍 **Режим массовой проверки активирован**\n\n"
                    "Отправьте username (с @) или Telegram ID пользователя:\n\n"
                    "**Примеры:**\n"
                    "• Username: `@durov`\n"
                    "• ID: `123456789`\n\n"
                    "💡 После проверки сразу можно вводить следующий username\n"
                    "Нажмите '🔙 Завершить проверку' для выхода",
                    reply_markup=InlineKeyboardMarkup(kb),
                    parse_mode="Markdown"
                )
            
            elif sub == "stop_check":
                # Завершение режима непрерывной проверки
                context.user_data["awaiting_username_check"] = False
                context.user_data["continuous_check_mode"] = False
                await query.edit_message_text(
                    "✅ Режим проверки завершен\n\n"
                    "Возвращение в админ-панель...",
                    parse_mode="Markdown"
                )
                await asyncio.sleep(1)
                await admin_panel(update, context)
            
            elif sub == "refresh":
                # Обновить админ-панель
                await admin_panel(update, context)
        
        elif data == "broadcast:confirm_text":
            # Подтверждение текстовой рассылки
            preview = context.user_data.get("broadcast_preview")
            if not preview or preview.get("type") != "text":
                await query.edit_message_text("❌ Ошибка: данные рассылки не найдены")
                return

            text_content = preview.get("text")
            entities = preview.get("entities", [])
            button_markup = preview.get("button_markup")
            button_text = preview.get("button_text")

            # Стартовое сообщение о прогрессе
            await query.edit_message_text("📤 Рассылка запускается...")
            progress_msg = query.message

            async def _send_text(uid: int):
                await context.bot.send_message(
                    uid,
                    text_content,
                    entities=entities,
                    reply_markup=button_markup,
                )

            stats = await perform_broadcast(
                context,
                _send_text,
                progress_message=progress_msg,
            )

            # Очищаем данные
            context.user_data.pop("broadcast_preview", None)

            extra = f"🔘 С кнопкой: {button_text}" if button_markup else ""
            try:
                await query.edit_message_text(
                    format_broadcast_report(stats, extra=extra),
                    parse_mode="Markdown",
                )
            except Exception:
                # Fallback без Markdown на случай проблем с форматированием
                await query.edit_message_text(format_broadcast_report(stats, extra=extra))

        elif data == "broadcast:confirm_photo":
            # Подтверждение фото рассылки
            preview = context.user_data.get("broadcast_preview")
            if not preview or preview.get("type") != "photo":
                await query.edit_message_text("❌ Ошибка: данные рассылки не найдены")
                return

            photo = preview.get("photo")
            caption = preview.get("caption", "")
            caption_entities = preview.get("caption_entities", [])
            button_markup = preview.get("button_markup")
            button_text = preview.get("button_text")

            await query.edit_message_text("📤 Рассылка запускается...")
            progress_msg = query.message

            async def _send_photo(uid: int):
                await context.bot.send_photo(
                    uid,
                    photo=photo,
                    caption=caption,
                    caption_entities=caption_entities,
                    reply_markup=button_markup,
                )

            stats = await perform_broadcast(
                context,
                _send_photo,
                progress_message=progress_msg,
            )

            # Очищаем данные
            context.user_data.pop("broadcast_preview", None)

            extra = f"🔘 С кнопкой: {button_text}" if button_markup else ""
            try:
                await query.edit_message_text(
                    format_broadcast_report(stats, extra=extra),
                    parse_mode="Markdown",
                )
            except Exception:
                await query.edit_message_text(format_broadcast_report(stats, extra=extra))
        
        elif data == "broadcast:cancel":
            # Отмена рассылки
            context.user_data.pop("broadcast_preview", None)
            await query.edit_message_text("❌ Рассылка отменена")
    
    except Exception as e:
        logger.exception("handle_buttons failed: %s", e)
        try:
            await query.answer("Произошла ошибка, попробуйте еще раз", show_alert=False)
        except Exception:
            pass


async def send_poster_to_chat(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    all_posters = context.bot_data.get("all_posters", [])
    if not all_posters:
        await context.bot.send_message(chat_id, "Афиш пока нет ;(")
        return
    
    # Берем последнюю (самую новую) афишу для рассылки
    poster = all_posters[-1]
    file_id = poster.get("file_id")
    caption = poster.get("caption", "")
    ticket_url = poster.get("ticket_url")
    
    try:
        reply_markup = None
        if ticket_url:
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🎫 Купить билет", url=ticket_url)]])
        await context.bot.send_photo(chat_id=chat_id, photo=file_id, caption=caption, reply_markup=reply_markup)
    except Forbidden:
        logger.info("Cannot send message to chat_id %s (blocked or privacy)", chat_id)
    except Exception as e:
        logger.exception("Failed to send poster to %s: %s", chat_id, e)


# ----------------------
# Admin commands
# ----------------------

async def admin_only(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    return bool(user and (user.id in get_admins(context)))


async def save_poster(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await admin_only(update, context):
        return
    msg = update.message
    if not msg:
        return
    # If command is a reply to a photo, use that; otherwise, try this message
    photo_msg = msg.reply_to_message if (msg.reply_to_message and msg.reply_to_message.photo) else msg
    if not photo_msg.photo:
        await msg.reply_text("Пожалуйста, ответь этой командой на сообщение с фото афиши и подписью.")
        return
    largest = photo_msg.photo[-1]
    file_id = largest.file_id
    caption = photo_msg.caption or ""
    poster = context.bot_data.get("poster", {})
    ticket_url = poster.get("ticket_url")
    context.bot_data["poster"] = {"file_id": file_id, "caption": caption, "ticket_url": ticket_url}
    await msg.reply_text("Афиша сохранена ✅ (фото и подпись). Для ссылки используйте /set_ticket <url>")


async def set_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await admin_only(update, context):
        return
    msg = update.message
    if not msg:
        return
    if not context.args:
        await msg.reply_text("Укажи ссылку: /set_ticket https://...")
        return
    url = context.args[0].strip()
    poster = context.bot_data.get("poster") or {}
    poster["ticket_url"] = url
    context.bot_data["poster"] = poster
    await msg.reply_text("Ссылка на покупку билета сохранена ✅")


async def delete_poster(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await admin_only(update, context):
        return
    context.bot_data.pop("poster", None)
    await update.message.reply_text("Афиша удалена. Загрузите новую с /save_poster")


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отобразить улучшенную админ-панель с inline кнопками."""
    user = update.effective_user
    if not user or user.id not in get_admins(context):
        await update.effective_chat.send_message("Эта команда доступна только администратору.")
        return
    owner = is_owner(user.id)
    
    # Получаем статистику из БД
    pool = get_db_pool(context)
    stats = {}
    if pool:
        try:
            stats = await get_user_stats(pool)
        except Exception as e:
            logger.warning("Failed to get stats: %s", e)
    
    # Показать информацию об афишах и пользователях
    all_posters = context.bot_data.get("all_posters", [])
    current_poster = context.bot_data.get("poster")
    
    status_text = "🛠 **Админ-панель TusaBot**\n"
    status_text += ("👑 Роль: Владелец\n\n" if owner else "🛡 Роль: Администратор\n\n")
    
    # Статистика афиш
    status_text += "📊 **Афиши:**\n"
    status_text += f"• Всего афиш: {len(all_posters)}\n"
    if current_poster:
        status_text += "• Текущая афиша: ✅ есть\n"
        if current_poster.get("ticket_url"):
            status_text += "• Ссылка на билеты: ✅ есть\n"
        else:
            status_text += "• Ссылка на билеты: ❌ нет\n"
    else:
        status_text += "• Текущая афиша: ❌ нет\n"
    
    # Статистика пользователей из БД
    status_text += "\n👥 **Пользователи:**\n"
    if stats:
        active = stats.get('total_users', 0)
        total_all = stats.get('total_all', active)
        inactive = total_all - active
        status_text += f"• Активных подписчиков: {active}\n"
        if inactive > 0:
            status_text += f"• Заблокировали бота: {inactive}\n"
        status_text += f"• Мужчин: {stats.get('male_users', 0)}\n"
        status_text += f"• Женщин: {stats.get('female_users', 0)}\n"
        status_text += f"• Сегодня: {stats.get('today_registrations', 0)}\n"
    else:
        status_text += f"• Активных подписчиков: {len(get_known_users(context))}\n"
    
    # Inline кнопки: базовый набор доступен и владельцу, и администратору
    admin_buttons = [
        # Управление афишами
        [
            InlineKeyboardButton("🧩 Создать афишу", callback_data="admin:create_poster"),
            InlineKeyboardButton("📋 Список афиш", callback_data="admin:list_posters")
        ],
        [
            InlineKeyboardButton("📤 Разослать афишу", callback_data="admin:broadcast_now"),
            InlineKeyboardButton("🗑 Удалить афишу", callback_data="admin:delete_poster")
        ],
        # Настройки и рассылки
        [
            InlineKeyboardButton("📝 Текстовая рассылка", callback_data="admin:broadcast_text")
        ],
        [
            InlineKeyboardButton("🔄 Обновить", callback_data="admin:refresh")
        ],
    ]
    
    # Функции, доступные только владельцу
    if owner:
        admin_buttons.append([
            InlineKeyboardButton("👥 Пользователи", callback_data="admin:users_count")
        ])
        admin_buttons.append([
            InlineKeyboardButton("👑 Управление админами", callback_data="admin:manage_admins")
        ])
    
    admin_buttons.append([InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")])
    
    await update.effective_chat.send_message(
        status_text, 
        reply_markup=InlineKeyboardMarkup(admin_buttons),
        parse_mode="Markdown"
    )


async def broadcast_now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await admin_only(update, context):
        return
    if not context.bot_data.get("all_posters"):
        await update.message.reply_text("❌ Афиш нет. Сначала создайте афишу.")
        return
    progress_msg = await update.message.reply_text("📤 Рассылка афиши запускается...")
    stats = await do_weekly_broadcast(context, progress_message=progress_msg)
    if stats is None:
        await progress_msg.edit_text("❌ Нет афиш или получателей")
        return
    try:
        await progress_msg.edit_text(
            format_broadcast_report(stats),
            parse_mode="Markdown",
        )
    except Exception:
        await progress_msg.edit_text(format_broadcast_report(stats))


async def broadcast_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Рассылка текста (с фото или без) всем пользователям.
    
    Использование:
    - /broadcast_text ваш текст - отправит текст всем
    - /broadcast_text (в reply на фото) - отправит фото с caption всем
    - Просто отправьте фото с caption /broadcast_text текст - отправит фото с текстом
    """
    if not await admin_only(update, context):
        return
    
    # Проверяем есть ли фото в сообщении
    photo = None
    caption = None
    
    if update.message.photo:
        # Фото отправлено напрямую
        photo = update.message.photo[-1].file_id
        # Caption может быть с /broadcast_text или без
        raw_caption = update.message.caption or ""
        if raw_caption.startswith("/broadcast_text"):
            caption = raw_caption.partition(' ')[2].strip()
        else:
            caption = raw_caption
    elif update.message.reply_to_message and update.message.reply_to_message.photo:
        # Reply на фото
        photo = update.message.reply_to_message.photo[-1].file_id
        # Текст из команды или из caption оригинального фото
        if context.args:
            caption = update.message.text.partition(' ')[2]
        else:
            caption = update.message.reply_to_message.caption or ""
    else:
        # Обычный текст без фото
        if not context.args:
            await update.message.reply_text(
                "📢 **Формат рассылки:**\n\n"
                "**Текст:** /broadcast_text ваш текст\n"
                "**Фото + текст:** отправьте фото с caption `/broadcast_text текст`\n"
                "**Или:** reply на фото командой `/broadcast_text текст`",
                parse_mode="Markdown"
            )
            return
        caption = update.message.text.partition(' ')[2]
    
    # Рассылаем через единый helper с rate-limit и обработкой ошибок
    progress_msg = await update.message.reply_text("📤 Рассылка запускается...")

    if photo:
        async def _send(uid: int):
            await context.bot.send_photo(uid, photo=photo, caption=caption)
    else:
        async def _send(uid: int):
            await context.bot.send_message(uid, caption)

    stats = await perform_broadcast(
        context,
        _send,
        progress_message=progress_msg,
    )

    try:
        await progress_msg.edit_text(
            format_broadcast_report(stats),
            parse_mode="Markdown",
        )
    except Exception:
        await progress_msg.edit_text(format_broadcast_report(stats))


# ----------------------
# Weekly jobs
# ----------------------

async def finalize_previous_week_and_reengage(context: ContextTypes.DEFAULT_TYPE) -> None:
    now = datetime.now(timezone.utc)
    prev_key = previous_week_key(now)

    for uid in list(get_known_users(context)):
        ud = context.application.user_data.setdefault(uid, {})
        attended_weeks: Set[str] = ud.get("attended_weeks", set())
        missed_in_row = int(ud.get("missed_in_row", 0))
        if prev_key in attended_weeks:
            ud["missed_in_row"] = 0
        else:
            missed_in_row += 1
            ud["missed_in_row"] = missed_in_row
            if missed_in_row > 2:
                try:
                    await context.bot.send_message(uid, REENGAGE_TEXT)
                except Forbidden:
                    logger.info("Cannot message user %s (blocked)", uid)
                except Exception as e:
                    logger.warning("Re-engage send failed to %s: %s", uid, e)
        context.application.user_data[uid] = ud


async def do_weekly_broadcast(context: ContextTypes.DEFAULT_TYPE, *, progress_message=None) -> Optional[dict]:
    """Рассылка последней афиши всем пользователям бота в личные сообщения.

    Возвращает словарь статистики (см. perform_broadcast) или None, если
    нет получателей/афиш.
    """
    # Получаем последнюю афишу для рассылки
    all_posters = context.bot_data.get("all_posters", [])
    if not all_posters:
        logger.info("No posters to broadcast")
        return None

    poster = all_posters[-1]
    file_id = poster.get("file_id")
    caption = poster.get("caption") or ""
    ticket_url = poster.get("ticket_url")
    reply_markup = None
    if ticket_url:
        reply_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🎫 Купить билет", url=ticket_url)]]
        )

    async def _send_poster(uid: int):
        await context.bot.send_photo(
            chat_id=uid,
            photo=file_id,
            caption=caption,
            reply_markup=reply_markup,
        )

    stats = await perform_broadcast(
        context,
        _send_poster,
        progress_message=progress_message,
    )

    logger.info(
        "Weekly broadcast completed: delivered=%d, blocked=%d, not_found=%d, failed=%d (total=%d)",
        stats["ok"], stats["blocked"], stats["not_found"], stats["failed"], stats["total"],
    )

    # Отправляем админу отчёт (если прогресс не шёл в какой-то чат напрямую)
    if progress_message is None:
        admin_id = ADMIN_USER_ID
        if admin_id:
            try:
                await context.bot.send_message(
                    admin_id,
                    format_broadcast_report(stats),
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.warning("Failed to send broadcast report to admin: %s", e)

    return stats


async def weekly_job(context: CallbackContext) -> None:
    await do_weekly_broadcast(context)


def schedule_weekly(app: Application) -> None:
    job_queue = app.job_queue
    send_time_utc = time(hour=WEEKLY_HOUR_UTC, minute=WEEKLY_MINUTE, tzinfo=pytz.utc)
    job_queue.run_daily(weekly_job, time=send_time_utc, days=(WEEKLY_DAY,))
    logger.info(
        "Scheduled weekly broadcast: day=%s at %02d:%02d UTC (local %02d:%02d MSK)",
        WEEKLY_DAY,
        WEEKLY_HOUR_UTC,
        WEEKLY_MINUTE,
        WEEKLY_HOUR_LOCAL,
        WEEKLY_MINUTE,
    )


async def _notify_admin_start(_: CallbackContext) -> None:
    if ADMIN_USER_ID:
        try:
            await _.bot.send_message(ADMIN_USER_ID, "Бот запущен ✅")
        except Exception:
            pass


# ----------------------
# Registration Handler
# ----------------------

async def handle_registration_step(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, user, user_data: dict, reg_step: str) -> None:
    """Обработка шагов регистрации"""
    pool = get_db_pool(context)
    
    if reg_step == "name":
        name = text.strip()
        user_data["name"] = name
        user_data["registration_step"] = "gender"
        
        # Создаем минимальную запись в БД с именем
        if pool:
            try:
                await upsert_user(pool, tg_id=user.id, name=name, username=user.username)
                logger.info("Name saved to DB for user %s: %s", user.id, name)
            except Exception as e:
                logger.warning("Failed to save name to DB: %s", e)
        
        kb = [
            [InlineKeyboardButton("👨 Мужской", callback_data="gender_male")],
            [InlineKeyboardButton("👩 Женский", callback_data="gender_female")]
        ]
        await update.message.reply_text(
            f"Приятно познакомиться, {name}! 😊\n\n"
            "Укажите ваш пол:",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return
    
    elif reg_step == "age":
        # Проверяем формат возраста
        try:
            age = int(text.strip())
            if age < 14 or age > 100:
                await update.message.reply_text(
                    "❌ Неверный возраст!\n\n"
                    "Пожалуйста, введите возраст от 14 до 100 лет\n"
                    "Например: 25"
                )
                return
                
            user_data["age"] = age
            user_data["registered"] = True
            user_data.pop("registration_step", None)
            
            # Завершаем регистрацию - берем имя из памяти, а если нет - из БД
            name = user_data.get("name")
            if not name and pool:
                try:
                    async with pool.acquire() as conn:
                        row = await conn.fetchrow("SELECT name FROM users WHERE tg_id = $1", user.id)
                        if row and row['name']:
                            name = row['name']
                            user_data["name"] = name
                except Exception as e:
                    logger.warning("Failed to load name from DB: %s", e)
            
            if not name:
                name = "Не указано"
            
            gender_text = {
                "male": "мужской",
                "female": "женский"
            }.get(user_data.get("gender", ""), "не указан")
            
            # Обновляем все данные в БД
            if pool:
                try:
                    await upsert_user(
                        pool,
                        tg_id=user.id,
                        name=name,
                        gender=user_data.get("gender"),
                        age=age,
                        username=user.username,
                    )
                    logger.info("Registration completed for user %s: %s", user.id, name)
                except Exception as e:
                    logger.warning("DB upsert after registration failed: %s", e)
            
            kb = [[InlineKeyboardButton("🎉 Перейти в меню", callback_data="back_to_menu")]]
            await update.message.reply_text(
                f"🎉 Отлично! Вы прошли регистрацию!\n\n"
                f"📝 Ваши данные:\n"
                f"• Имя: {name}\n"
                f"• Пол: {gender_text}\n"
                f"• Возраст: {age} лет\n\n"
                f"Теперь вы можете посещать наши вечеринки! 🥳",
                reply_markup=InlineKeyboardMarkup(kb)
            )
            return
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат возраста!\n\n"
                "Пожалуйста, введите возраст числом\n"
                "Например: 18"
            )
            return


# ----------------------
# Bootstrap
# ----------------------

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Registration flow
    if update.message and update.message.text:
        text = update.message.text
        user = update.effective_user
        user_data = context.user_data
        
        # ПРИОРИТЕТ 1: Обработка регистрации (должна быть ПЕРВОЙ!)
        reg_step = user_data.get("registration_step")
        if reg_step:
            # Пользователь в процессе регистрации - обрабатываем только это
            await handle_registration_step(update, context, text, user, user_data, reg_step)
            return
        
        # ПРИОРИТЕТ 2: Проверка подписки по username/ID (для админов)
        if user_data.get("awaiting_username_check"):
            # НЕ сбрасываем флаг здесь! Он будет сброшен после обработки, если НЕ в режиме continuous
            
            input_text = text.strip()
            target_user_id = None
            username_display = input_text
            
            try:
                # Проверяем, это ID или username
                if input_text.isdigit():
                    # Это ID
                    target_user_id = int(input_text)
                    username_display = f"ID {input_text}"
                else:
                    # Это username - ищем в БД
                    username = input_text.lstrip('@')
                    username_display = f"@{username}"
                    
                    # Ищем пользователя в БД по username
                    pool = get_db_pool(context)
                    if pool:
                        try:
                            user_in_db = await get_user_by_username(pool, username)
                            if user_in_db:
                                target_user_id = user_in_db.get("tg_id")
                                logger.info(f"Found user by username @{username}: ID={target_user_id}")
                            else:
                                # Если не нашли в БД, пробуем через get_chat (для публичных профилей)
                                try:
                                    target_chat = await context.bot.get_chat(f"@{username}")
                                    target_user_id = target_chat.id
                                    logger.info(f"Found user by get_chat @{username}: ID={target_user_id}")
                                except Exception:
                                    pass
                        except Exception as e:
                            logger.error(f"Error searching user by username in DB: {e}")
                    
                    if not target_user_id:
                        # Проверяем режим
                        if context.user_data.get("continuous_check_mode"):
                            kb = [[InlineKeyboardButton("🔙 Завершить проверку", callback_data="admin:stop_check")]]
                            await update.message.reply_text(
                                f"❌ Пользователь @{username} не найден\n\n"
                                f"Возможные причины:\n"
                                f"• Username указан неверно\n"
                                f"• Пользователь не взаимодействовал с ботом\n"
                                f"• Профиль скрыт или удален\n\n"
                                f"💡 Попробуйте ввести другой username или используйте Telegram ID",
                                reply_markup=InlineKeyboardMarkup(kb)
                            )
                            # НЕ сбрасываем флаги
                        else:
                            context.user_data["awaiting_username_check"] = False
                            await update.message.reply_text(
                                f"❌ Пользователь @{username} не найден\n\n"
                                f"Возможные причины:\n"
                                f"• Username указан неверно\n"
                                f"• Пользователь не взаимодействовал с ботом\n"
                                f"• Профиль скрыт или удален\n\n"
                                f"💡 **Рекомендация:** Используйте Telegram ID\n"
                                f"Попросите пользователя написать @userinfobot",
                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад в панель", callback_data="admin:refresh")]])
                            )
                        return
                
                if not target_user_id:
                    await update.message.reply_text(
                        "❌ Не удалось определить ID пользователя",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад в панель", callback_data="admin:refresh")]])
                    )
                    return
                
                # Проверяем подписки на каналы и чат
                tg1_ok, tg2_ok, chat_ok = await is_user_subscribed(context, target_user_id)
                
                # Формируем отчет (экранируем специальные символы Markdown)
                def escape_markdown(text):
                    """Экранирует специальные символы для Markdown"""
                    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
                    for char in special_chars:
                        text = text.replace(char, '\\' + char)
                    return text
                
                username_safe = escape_markdown(str(username_display))
                
                report = f"🔍 **Проверка подписок для {username_safe}**\n\n"
                report += f"👤 Telegram ID: `{target_user_id}`\n\n"
                report += "📺 **Telegram каналы:**\n"
                report += f"{'✅' if tg1_ok else '❌'} {CHANNEL_USERNAME} \\(MEDIA FAM\\)\n"
                report += f"{'✅' if tg2_ok else '❌'} {CHANNEL_USERNAME_2} \\(THE FAMILY\\)\n\n"
                report += "💬 **Telegram чат:**\n"
                report += f"{'✅' if chat_ok else '❌'} {CHAT_USERNAME} \\(Family Guests\\)\n"
                
                all_ok = tg1_ok and tg2_ok and chat_ok
                report += f"\n{'🎉 **Все подписки активны\\!**' if all_ok else '⚠️ **Не все подписки активны**'}"
                
                # Кнопки в зависимости от режима
                if context.user_data.get("continuous_check_mode"):
                    # Режим непрерывной проверки - оставляем флаг активным
                    kb = [[InlineKeyboardButton("🔙 Завершить проверку", callback_data="admin:stop_check")]]
                    await update.message.reply_text(
                        report + "\n\n💡 Введите следующий username или нажмите 'Завершить проверку'",
                        reply_markup=InlineKeyboardMarkup(kb),
                        parse_mode="MarkdownV2"
                    )
                    # НЕ сбрасываем флаг awaiting_username_check!
                else:
                    # Обычный режим - одна проверка
                    context.user_data["awaiting_username_check"] = False
                    await update.message.reply_text(
                        report,
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад в панель", callback_data="admin:refresh")]]),
                        parse_mode="MarkdownV2"
                    )
                return
                
            except Exception as e:
                logger.error("Error checking subscriptions by username: %s", e)
                
                # Проверяем режим
                if context.user_data.get("continuous_check_mode"):
                    kb = [[InlineKeyboardButton("🔙 Завершить проверку", callback_data="admin:stop_check")]]
                    await update.message.reply_text(
                        f"❌ Ошибка при проверке подписок:\n{str(e)}\n\n"
                        f"💡 Попробуйте ввести другой username",
                        reply_markup=InlineKeyboardMarkup(kb)
                    )
                    # НЕ сбрасываем флаги
                else:
                    context.user_data["awaiting_username_check"] = False
                    await update.message.reply_text(
                        f"❌ Ошибка при проверке подписок:\n{str(e)}",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад в панель", callback_data="admin:refresh")]])
                    )
                return
        
        # Админские команды теперь только через inline кнопки в админ-панели
        # Оставляем только обработку ввода данных
        # Handle admin text inputs
        if context.user_data.get("awaiting_new_admin_id"):
            if not is_owner(user.id):
                context.user_data["awaiting_new_admin_id"] = False
                return
            context.user_data["awaiting_new_admin_id"] = False
            target_id = None
            raw_text = (update.message.text or "").strip()
            if update.message.forward_from:
                target_id = update.message.forward_from.id
            elif update.message.reply_to_message and update.message.reply_to_message.from_user:
                target_id = update.message.reply_to_message.from_user.id
            elif raw_text.isdigit():
                target_id = int(raw_text)
            elif raw_text.startswith("@") or raw_text:
                username = raw_text.lstrip("@").strip()
                pool = get_db_pool(context)
                found_user = await get_user_by_username(pool, username) if pool else None
                if found_user:
                    target_id = found_user["tg_id"]
                else:
                    await update.message.reply_text(
                        f"❌ Пользователь @{username} не найден в базе (он должен хотя бы раз запускать бота)."
                    )
                    return
            if not target_id:
                await update.message.reply_text(
                    "❌ Не удалось определить пользователя. Пришлите Telegram ID (число), @username "
                    "или перешлите сообщение пользователя."
                )
                return
            if is_owner(target_id):
                await update.message.reply_text("Этот пользователь уже владелец бота.")
                return
            pool = get_db_pool(context)
            if pool:
                try:
                    await db_add_admin(pool, target_id, user.id)
                    await refresh_admins_cache(context)
                except Exception as e:
                    logger.warning("Failed to add admin %s: %s", target_id, e)
                    await update.message.reply_text(f"❌ Не удалось назначить администратора: {e}")
                    return
            text, kb = build_manage_admins_view(context)
            await update.message.reply_text(
                f"✅ Пользователь {target_id} назначен администратором!\n\n{text}",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode="Markdown"
            )
            return
        
        if context.user_data.get("awaiting_ticket"):
            context.user_data["awaiting_ticket"] = False
            url = update.message.text.strip()
            poster = context.bot_data.get("poster") or {}
            poster["ticket_url"] = url
            context.bot_data["poster"] = poster
            await update.message.reply_text("Ссылка сохранена ✅")
            return
            
        if context.user_data.get("awaiting_broadcast_text"):
            # Сохраняем сообщение для предпросмотра
            original_text = update.message.text
            original_entities = update.message.entities or []  # Сохраняем форматирование
            
            # Парсим формат: "Текст | Текст кнопки | URL"
            # Ищем последние два разделителя " | " с конца, чтобы поддерживать переносы строк в тексте
            button_markup = None
            button_text = None
            button_url = None
            text_content = original_text
            adjusted_entities = original_entities
            
            if " | " in original_text:
                # Ищем последний разделитель (перед URL)
                last_separator = original_text.rfind(" | ")
                if last_separator != -1:
                    # Ищем предпоследний разделитель (перед текстом кнопки)
                    second_last_separator = original_text.rfind(" | ", 0, last_separator)
                    
                    if second_last_separator != -1:
                        # Нашли оба разделителя - парсим на 3 части
                        text_content = original_text[:second_last_separator].strip()
                        button_text = original_text[second_last_separator + 3:last_separator].strip()
                        button_url = original_text[last_separator + 3:].strip()
                        
                        # Корректируем entities для обрезанного текста
                        # Entities указывают на позиции в исходном тексте
                        # Нужно оставить только те, что относятся к text_content
                        text_length = len(text_content)
                        adjusted_entities = []
                        for entity in original_entities:
                            # Если entity начинается в пределах text_content
                            if entity.offset < text_length:
                                # Обрезаем entity если он выходит за пределы
                                new_entity = entity
                                if entity.offset + entity.length > text_length:
                                    # Создаем новый entity с обрезанной длиной
                                    from telegram import MessageEntity
                                    new_entity = MessageEntity(
                                        type=entity.type,
                                        offset=entity.offset,
                                        length=text_length - entity.offset,
                                        url=entity.url,
                                        user=entity.user,
                                        language=entity.language
                                    )
                                adjusted_entities.append(new_entity)
                        
                        # Создаем кнопку
                        if button_text and button_url:
                            button_markup = InlineKeyboardMarkup([
                                [InlineKeyboardButton(button_text, url=button_url)]
                            ])
                            logger.info("Broadcast with button: text='%s', url='%s'", button_text, button_url)
            
            # Сохраняем данные для подтверждения
            context.user_data["broadcast_preview"] = {
                "text": text_content,
                "entities": adjusted_entities,
                "button_markup": button_markup,
                "button_text": button_text,
                "type": "text"
            }
            context.user_data["awaiting_broadcast_text"] = False
            
            # Отправляем предпросмотр
            await update.message.reply_text(
                "📝 Предпросмотр рассылки:"
            )
            
            # Отправляем сообщение с форматированием
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text_content,
                entities=adjusted_entities,  # Передаем скорректированное форматирование
                reply_markup=button_markup
            )
            
            # Спрашиваем подтверждение
            await update.message.reply_text(
                "✅ Всё верно? Отправить рассылку?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Да, отправить", callback_data="broadcast:confirm_text")],
                    [InlineKeyboardButton("❌ Нет, отменить", callback_data="broadcast:cancel")]
                ])
            )
            return
        
        # Poster draft: expecting caption or link
        draft = context.user_data.get("poster_draft")
        if draft:
            step = draft.get("step")
            if step == "caption":
                draft["caption"] = update.message.text
                draft["step"] = "link"
                context.user_data["poster_draft"] = draft
                await update.message.reply_text(
                    "Шаг 3/4: пришлите ссылку для кнопки «Купить билет»",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❌ Отмена", callback_data="admin:cancel_poster")],
                        [InlineKeyboardButton("◀️ Назад в панель", callback_data="admin:back_to_panel")],
                    ]),
                )
                return
            if step == "link":
                url = update.message.text.strip()
                draft["ticket_url"] = url
                draft["step"] = "preview"
                context.user_data["poster_draft"] = draft
                # Предпросмотр: отправим фото с подписью и кнопкой
                rm = None
                if url:
                    rm = InlineKeyboardMarkup([[InlineKeyboardButton("Купить билет", url=url)]])
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=draft["file_id"],
                    caption=draft.get("caption") or "",
                    reply_markup=rm,
                )
                await update.message.reply_text(
                    "Шаг 4/4: подтвердить публикацию?",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("✅ Подтвердить", callback_data="admin:confirm_poster")],
                        [InlineKeyboardButton("❌ Отмена", callback_data="admin:cancel_poster")],
                        [InlineKeyboardButton("◀️ Назад в панель", callback_data="admin:back_to_panel")],
                    ]),
                )
                return
        # VK handling removed - only Telegram channels now


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Проверяем рассылку фото
    if context.user_data.get("awaiting_broadcast_text"):
        photo = update.message.photo[-1].file_id
        original_caption = update.message.caption or ""
        original_caption_entities = update.message.caption_entities or []  # Сохраняем форматирование
        
        # Парсим формат кнопки в caption: "Текст | Текст кнопки | URL"
        # Ищем последние два разделителя " | " с конца, чтобы поддерживать переносы строк в тексте
        button_markup = None
        button_text = None
        button_url = None
        caption = original_caption
        adjusted_caption_entities = original_caption_entities
        
        if " | " in original_caption:
            # Ищем последний разделитель (перед URL)
            last_separator = original_caption.rfind(" | ")
            if last_separator != -1:
                # Ищем предпоследний разделитель (перед текстом кнопки)
                second_last_separator = original_caption.rfind(" | ", 0, last_separator)
                
                if second_last_separator != -1:
                    # Нашли оба разделителя - парсим на 3 части
                    caption = original_caption[:second_last_separator].strip()
                    button_text = original_caption[second_last_separator + 3:last_separator].strip()
                    button_url = original_caption[last_separator + 3:].strip()
                    
                    # Корректируем caption_entities для обрезанного текста
                    caption_length = len(caption)
                    adjusted_caption_entities = []
                    for entity in original_caption_entities:
                        if entity.offset < caption_length:
                            new_entity = entity
                            if entity.offset + entity.length > caption_length:
                                from telegram import MessageEntity
                                new_entity = MessageEntity(
                                    type=entity.type,
                                    offset=entity.offset,
                                    length=caption_length - entity.offset,
                                    url=entity.url,
                                    user=entity.user,
                                    language=entity.language
                                )
                            adjusted_caption_entities.append(new_entity)
                    
                    # Создаем кнопку
                    if button_text and button_url:
                        button_markup = InlineKeyboardMarkup([
                            [InlineKeyboardButton(button_text, url=button_url)]
                        ])
                        logger.info("Broadcast photo with button: text='%s', url='%s'", button_text, button_url)
        
        # Сохраняем данные для подтверждения
        context.user_data["broadcast_preview"] = {
            "photo": photo,
            "caption": caption,
            "caption_entities": adjusted_caption_entities,
            "button_markup": button_markup,
            "button_text": button_text,
            "type": "photo"
        }
        context.user_data["awaiting_broadcast_text"] = False
        
        # Отправляем предпросмотр
        await update.message.reply_text(
            "📝 Предпросмотр рассылки:"
        )
        
        # Отправляем фото с форматированием
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=photo,
            caption=caption,
            caption_entities=adjusted_caption_entities,  # Передаем скорректированное форматирование
            reply_markup=button_markup
        )
        
        # Спрашиваем подтверждение
        await update.message.reply_text(
            "✅ Всё верно? Отправить рассылку?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Да, отправить", callback_data="broadcast:confirm_photo")],
                [InlineKeyboardButton("❌ Нет, отменить", callback_data="broadcast:cancel")]
            ])
        )
        return

    # Poster draft: expecting photo at step 'photo'
    draft = context.user_data.get("poster_draft")
    if draft and draft.get("step") == "photo" and update.message.photo:
        largest = update.message.photo[-1]
        file_id = largest.file_id
        
        # Скачиваем фото и сохраняем локально
        try:
            # Получаем файл из Telegram
            file = await context.bot.get_file(file_id)
            
            # Создаем папку для афиш если её нет
            posters_dir = Path(__file__).parent / "project" / "public" / "posters"
            posters_dir.mkdir(parents=True, exist_ok=True)
            
            # Генерируем уникальное имя файла
            import time
            timestamp = int(time.time())
            file_ext = file.file_path.split('.')[-1] if '.' in file.file_path else 'jpg'
            filename = f"poster_{timestamp}.{file_ext}"
            local_path = posters_dir / filename
            
            # Скачиваем файл
            await file.download_to_drive(local_path)
            
            # Сохраняем путь для веб-приложения (относительный путь)
            web_path = f"/posters/{filename}"
            
            draft["file_id"] = file_id  # Оставляем для бота
            draft["photo_path"] = web_path  # Для веб-приложения
            draft["step"] = "caption"
            context.user_data["poster_draft"] = draft
            
            logger.info(f"Photo saved to {local_path}, web path: {web_path}")
            
            await update.message.reply_text(
                "✅ Фото сохранено!\n\nШаг 2/4: пришлите текст (подпись) для афиши",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Отмена", callback_data="admin:cancel_poster")],
                    [InlineKeyboardButton("◀️ Назад в панель", callback_data="admin:back_to_panel")],
                ]),
            )
        except Exception as e:
            logger.error(f"Failed to download photo: {e}")
            await update.message.reply_text(
                "❌ Ошибка при сохранении фото. Попробуйте еще раз.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад в панель", callback_data="admin:back_to_panel")],
                ]),
            )
        return
    # если фото вне мастера — ничего не делаем


def build_app() -> Application:
    """Build and configure the Application"""
    ensure_data_dir()
    # ВРЕМЕННО отключаем persistence для тестирования регистрации
    # persistence = PicklePersistence(filepath=str(PERSISTENCE_FILE))
    persistence = None
    
    # Create request with generous timeouts (дефолт httpx = 5 сек, на медленных
    # хостингах / при блокировках получаем TimedOut; увеличиваем до 30 сек).
    # Если задан PROXY_URL — пускаем весь трафик через прокси (HTTP или SOCKS5).
    _common_kwargs = dict(
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=10.0,
    )
    if PROXY_URL:
        request = HTTPXRequest(proxy=PROXY_URL, **_common_kwargs)
        # Для long-polling нужен больший read_timeout
        get_updates_request = HTTPXRequest(
            proxy=PROXY_URL,
            connect_timeout=30.0,
            read_timeout=40.0,
            write_timeout=30.0,
            pool_timeout=10.0,
        )
        logger.info("Using proxy: %s", PROXY_URL.split('@')[-1] if '@' in PROXY_URL else PROXY_URL)
    else:
        request = HTTPXRequest(**_common_kwargs)
        get_updates_request = HTTPXRequest(
            connect_timeout=30.0,
            read_timeout=40.0,
            write_timeout=30.0,
            pool_timeout=10.0,
        )

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .persistence(persistence)
        .request(request)
        .get_updates_request(get_updates_request)
        .build()
    )

    # DB lifecycle
    async def _on_startup(app: Application):
        try:
            pool = await create_pool()
            await init_schema(pool)
            app.bot_data["db_pool"] = pool
            
            # Загружаем администраторов, назначенных владельцем
            await refresh_admins_cache(app)
            
            # Загружаем существующих пользователей из БД
            user_ids = await get_all_user_ids(pool)
            app.bot_data["known_users"] = set(user_ids)
            
            # Загружаем активные афиши из БД
            try:
                posters_from_db = await get_active_posters(pool)
                if posters_from_db:
                    # Конвертируем в формат bot_data
                    all_posters = []
                    for p in posters_from_db:
                        all_posters.append({
                            "id": p["id"],
                            "file_id": p["file_id"],
                            "caption": p["caption"],
                            "ticket_url": p["ticket_url"]
                        })
                    app.bot_data["all_posters"] = all_posters
                    # Последняя афиша становится текущей
                    if all_posters:
                        app.bot_data["poster"] = all_posters[-1]
                    logger.info("Loaded %d active posters from DB", len(all_posters))
                else:
                    app.bot_data["all_posters"] = []
                    logger.info("No active posters in DB")
            except Exception as e:
                logger.warning("Failed to load posters from DB: %s", e)
                app.bot_data["all_posters"] = []
            
            # Настраиваем команды бота (только для обычных пользователей)
            commands = [
                BotCommand("start", "Начать работу с ботом"),
                BotCommand("menu", "Главное меню")
            ]
            await app.bot.set_my_commands(commands)
            
            logger.info("DB pool initialized, schema ready, loaded %d users, commands set", len(user_ids))
        except Exception as e:
            logger.error("Failed to init DB: %s", e)

    async def _on_shutdown(app: Application):
        pool = app.bot_data.get("db_pool")
        if pool:
            try:
                await pool.close()
                logger.info("DB pool closed")
            except Exception as e:
                logger.warning("Error closing DB pool: %s", e)

    async def _notify_admin_start(context: ContextTypes.DEFAULT_TYPE):
        # Уведомление админу убрано по запросу
        pass

    # Обработчик команды /app для отображения мини-приложения
    async def show_web_app(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # Локальный URL для тестирования
        web_app_url = "http://localhost:8000/index.html"
        
        # Создаем кнопку с веб-приложением
        keyboard = [
            [
                InlineKeyboardButton(
                    "Открыть приложение",
                    web_app=WebAppInfo(url=web_app_url)
                )
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Нажмите кнопку ниже, чтобы открыть приложение:",
            reply_markup=reply_markup
        )

    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("app", show_web_app))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("id", show_id))
    app.add_handler(CommandHandler("broadcast_text", broadcast_text))
    app.add_handler(CommandHandler("broadcast_now", broadcast_now))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Register lifecycle handlers - удалено неправильный handler
    app.post_init = _on_startup
    app.post_shutdown = _on_shutdown

    # ===== АВТОРАССЫЛКА ОТКЛЮЧЕНА =====
    # Раскомментируйте строку ниже, чтобы включить автоматическую еженедельную рассылку
    # schedule_weekly(app)
    # ==================================
    
    # Notify admin shortly after start
    app.job_queue.run_once(_notify_admin_start, when=1)
    return app


def main() -> None:
    app = build_app()
    logger.info("Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
