#!/usr/bin/env python3
"""
Улучшенный файл для запуска Telegram-бота на Railway с исправлениями проблем загрузки мемов.
Обеспечивает обновление мемов в реальном времени с сохранением фильтрации рекламы.
"""
import logging
import os
import signal
import sys
import threading
import time
import random
import json
from datetime import datetime

import vk_api
import requests
from io import BytesIO
try:
    from PIL import Image
except ImportError:
    pass  # PIL может быть недоступен в некоторых средах

# Для работы с Telegram API
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, error
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Импортируем собственные модули
from meme_data import MEMES, MEME_SOURCES, is_suitable_meme
from recommendation_engine import (
    update_user_preferences, 
    recommend_memes, 
    get_user_preferences_stats, 
    analyze_user_history
)
import meme_analytics
from vk_utils import fetch_vk_memes

# Настройка логирования
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stdout)
logger = logging.getLogger(__name__)

# Путь к файлу для сохранения мемов
MEMES_CACHE_FILE = "cached_filtered_memes.json"
REJECTED_CACHE_FILE = "rejected_memes.json"

# Словарь для хранения состояния пользователей
user_states = {}

# Кэшированные отфильтрованные мемы
memes_collection = {}

# Словарь отклоненных мемов для анализа
rejected_memes = {}

# Конфигурация обновления мемов
UPDATE_INTERVAL = 1800  # Интервал обновления в секундах (30 минут)
MIN_MEMES_COUNT = 50    # Минимальное количество мемов
MAX_MEMES_TO_FETCH = 20 # Максимальное количество мемов за одно обновление

# Публичные группы VK для мемов, синхронизированные с MEME_SOURCES
VK_GROUP_IDS = [
    212383311,  # public212383311 (Мемы для офисных работников)
    189934484,  # office_rat (предположительный ID, уточните)
    177133249,  # corporateethics
    211736252,  # club211736252 (Нетворкинг мемы)
    197824345,  # hr_mem
    167608937,  # workbench_mem
    159672532,  # the_working_day
    148463127,  # office.mems
    149391075,  # zapiskibezdushi
    29534144,   # office_plankton
]

# Флаг для управления процессом обновления
update_thread_running = False

# Инициализация VK API
vk_token = os.getenv("VK_TOKEN")
if not vk_token:
    logger.error("VK_TOKEN не задан в переменных окружения")
    sys.exit(1)

try:
    vk_session = vk_api.VkApi(token=vk_token)
    vk = vk_session.get_api()
    logger.info("VK API успешно инициализирован")
except vk_api.AuthError as e:
    logger.error(f"Ошибка авторизации VK API: {e}")
    sys.exit(1)

def signal_handler(sig, frame):
    """Обработчик сигнала для корректного завершения работы бота"""
    logger.info("Получен сигнал завершения. Завершаем работу бота...")
    global update_thread_running
    update_thread_running = False
    save_memes_to_cache()
    sys.exit(0)

def save_memes_to_cache():
    """Сохраняет коллекцию мемов в файл кэша"""
    try:
        with open(MEMES_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(memes_collection, f, ensure_ascii=False, indent=2)
        logger.info(f"Сохранено {len(memes_collection)} мемов в кэш")
        
        with open(REJECTED_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(rejected_memes, f, ensure_ascii=False, indent=2)
        logger.info(f"Сохранено {len(rejected_memes)} отклоненных мемов")
    except Exception as e:
        logger.error(f"Ошибка при сохранении мемов в кэш: {e}")

def load_memes_from_cache():
    """Загружает мемы из файла кэша, если он существует"""
    global memes_collection, rejected_memes
    try:
        if os.path.exists(MEMES_CACHE_FILE):
            with open(MEMES_CACHE_FILE, 'r', encoding='utf-8') as f:
                loaded_memes = json.load(f)
                if loaded_memes and isinstance(loaded_memes, dict):
                    memes_collection = loaded_memes
                    logger.info(f"Загружено {len(memes_collection)} мемов из кэша")
        
        if os.path.exists(REJECTED_CACHE_FILE):
            with open(REJECTED_CACHE_FILE, 'r', encoding='utf-8') as f:
                loaded_rejected = json.load(f)
                if loaded_rejected and isinstance(loaded_rejected, dict):
                    rejected_memes = loaded_rejected
                    logger.info(f"Загружено {len(rejected_memes)} отклоненных мемов")
        
        return len(memes_collection) > 0
    except Exception as e:
        logger.error(f"Ошибка при загрузке мемов из кэша: {e}")
        return False

def validate_image(image_url):
    """Проверяет доступность и валидность изображения"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(image_url, headers=headers, timeout=5, stream=True)
        if response.status_code != 200:
            logger.warning(f"Изображение недоступно: {image_url}, статус: {response.status_code}")
            return False
        try:
            img_data = BytesIO(response.content)
            Image.open(img_data).verify()
            return True
        except Exception as e:
            logger.error(f"Ошибка проверки изображения {image_url}: {e}")
            return False
    except Exception as e:
        logger.error(f"Ошибка загрузки изображения {image_url}: {e}")
        return False

def init_default_memes():
    """Инициализирует базовый набор мемов из VK API или статической коллекции MEMES"""
    global memes_collection, rejected_memes
    logger.info("Инициализация стандартного набора мемов")
    count_added = 0
    count_rejected = 0
    
    # Сначала пытаемся загрузить мемы из VK
    for group_id in VK_GROUP_IDS:
        memes = fetch_vk_memes(group_id, count=10)
        for meme in memes:
            meme_id = f"vk_{abs(hash(meme['image_url'] + meme['text']))}"
            if meme_id in memes_collection or meme_id in rejected_memes:
                continue
            if validate_image(meme["image_url"]) and is_suitable_meme(meme):
                memes_collection[meme_id] = meme
                count_added += 1
                logger.info(f"Добавлен мем {meme_id}")
            else:
                rejected_memes[meme_id] = meme
                count_rejected += 1
                logger.info(f"Отклонен мем {meme_id} как неподходящий или с недоступным изображением")
        time.sleep(random.uniform(0.5, 1))  # Задержка для лимитов
    
    # Если не удалось загрузить достаточно мемов из VK, используем MEMES
    if count_added < MIN_MEMES_COUNT:
        logger.info("Недостаточно мемов из VK, загружаем из статической коллекции MEMES")
        for meme_id, meme in MEMES.items():
            if meme_id in memes_collection or meme_id in rejected_memes:
                continue
            # Добавляем timestamp для совместимости
            meme = meme.copy()
            meme['timestamp'] = datetime.now().isoformat()
            if validate_image(meme["image_url"]) and is_suitable_meme(meme):
                memes_collection[meme_id] = meme
                count_added += 1
                logger.info(f"Добавлен статический мем {meme_id}")
            else:
                rejected_memes[meme_id] = meme
                count_rejected += 1
                logger.info(f"Отклонен статический мем {meme_id}")
    
    logger.info(f"Инициализировано {count_added} подходящих мемов и {count_rejected} отклоненных мемов")
    return count_added > 0

def try_fetch_memes_from_vk():
    """Проверяет возможность получения мемов из VK"""
    try:
        test_memes = fetch_vk_memes(VK_GROUP_IDS[0], count=1)
        return len(test_memes) > 0
    except Exception as e:
        logger.error(f"Ошибка при тестовом вызове VK API: {e}")
        return False

def update_memes():
    """Периодическое обновление мемов в реальном времени"""
    global update_thread_running, memes_collection
    update_thread_running = True
    logger.info("Запущен поток обновления мемов")
    
    if not try_fetch_memes_from_vk():
        logger.warning("VK API недоступен, используем кэш или статические мемы")
        if not memes_collection:
            init_default_memes()
            save_memes_to_cache()
        return
    
    while update_thread_running:
        try:
            if len(memes_collection) < MIN_MEMES_COUNT:
                logger.info(f"Количество мемов ({len(memes_collection)}) меньше минимального {MIN_MEMES_COUNT}. Запускаем обновление...")
                for group_id in VK_GROUP_IDS:
                    fetch_and_add_new_memes(group_id, MAX_MEMES_TO_FETCH // len(VK_GROUP_IDS))
                    time.sleep(random.uniform(0.5, 1))
            
            logger.info("Выполняется регулярное обновление мемов...")
            for group_id in VK_GROUP_IDS:
                fetch_and_add_new_memes(group_id, 5)
                time.sleep(random.uniform(0.5, 1))
            
            save_memes_to_cache()
            time.sleep(UPDATE_INTERVAL)
        except Exception as e:
            logger.error(f"Ошибка в процессе обновления мемов: {e}")
            time.sleep(60)

def fetch_and_add_new_memes(group_id, count=10):
    """Получает новые мемы из VK и добавляет их в коллекцию"""
    global memes_collection, rejected_memes
    logger.info(f"Получение {count} новых мемов из группы {group_id}...")
    new_memes_count = 0
    rejected_count = 0
    memes = fetch_vk_memes(group_id, count)
    
    for meme in memes:
        meme_id = f"vk_{abs(hash(meme['image_url'] + meme['text']))}"
        if meme_id in memes_collection or meme_id in rejected_memes:
            logger.debug(f"Мем {meme_id} уже существует")
            continue
        
        image_valid = validate_image(meme["image_url"])
        meme_suitable = is_suitable_meme(meme)
        if image_valid and meme_suitable:
            memes_collection[meme_id] = meme
            new_memes_count += 1
            logger.info(f"Добавлен новый мем {meme_id}")
        else:
            rejected_memes[meme_id] = meme
            rejected_count += 1
            logger.info(f"Отклонен мем {meme_id} {'из-за недоступного изображения' if not image_valid else 'как неподходящий'}")
    
    logger.info(f"Получено {new_memes_count} новых мемов, отклонено {rejected_count}")
    return new_memes_count

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start. Отправляет первый мем пользователю."""
    user = update.effective_user
    user_id = user.id
    username = user.username
    
    logger.info(f"Команда /start от пользователя {username} (ID: {user_id})")
    
    if user_id not in user_states:
        user_states[user_id] = {
            "username": username,
            "current_meme": None,
            "viewed_memes": [],
            "ratings": {}
        }
        
    try:
        meme_analytics.record_user_session(user_id)
    except Exception as e:
        logger.error(f"Ошибка при записи сессии пользователя в аналитику: {e}")
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "👋 Привет! Я бот для просмотра мемов без рекламы.\n\n"
            "Используем передовую технологию фильтрации рекламного контента. "
            "Все мемы тщательно проверяются системой фильтрации.\n\n"
            "Используйте /start для начала, 👍/👎 для оценки мема, /next для пропуска."
        )
    )
    
    await send_random_meme(update, context)

async def send_random_meme(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет случайный мем пользователю."""
    user = update.effective_user
    user_id = user.id
    
    if user_id not in user_states:
        await start(update, context)
        return
    
    if not memes_collection:
        logger.warning("Мемы отсутствуют в коллекции. Инициализация...")
        if not init_default_memes():
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="К сожалению, на данный момент нет доступных мемов. Попробуйте позже."
            )
            return
    
    viewed_memes = user_states[user_id].get("viewed_memes", [])
    available_memes = [meme_id for meme_id in memes_collection if meme_id not in viewed_memes]
    
    if not available_memes or len(available_memes) < 5:
        logger.info(f"Пользователь {user_id} просмотрел все мемы, сбрасываем историю")
        user_states[user_id]["viewed_memes"] = []
        available_memes = list(memes_collection.keys())
    
    ratings = user_states[user_id].get("ratings", {})
    if len(ratings) >= 5:
        try:
            recommended_memes = recommend_memes(user_id, memes_collection, 10)
            recommended_unseen = [m for m in recommended_memes if m not in viewed_memes]
            meme_id = recommended_unseen[0] if recommended_unseen else random.choice(available_memes)
            logger.info(f"Отправляем персонализированную рекомендацию для пользователя {user_id}")
        except Exception as e:
            logger.error(f"Ошибка при получении рекомендаций: {e}")
            meme_id = random.choice(available_memes)
    else:
        meme_id = random.choice(available_memes)
    
    if meme_id not in memes_collection:
        logger.warning(f"Мем {meme_id} не найден, выбираем другой")
        if memes_collection:
            meme_id = random.choice(list(memes_collection.keys()))
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="К сожалению, на данный момент нет доступных мемов. Попробуйте позже."
            )
            return
    
    meme = memes_collection[meme_id]
    keyboard = [
        [
            InlineKeyboardButton("👍", callback_data=f"rate:{meme_id}:1"),
            InlineKeyboardButton("👎", callback_data=f"rate:{meme_id}:-1")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = meme.get("text", "")
    image_url = meme.get("image_url", "")
    
    try:
        if image_url:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(image_url, headers=headers, timeout=10, stream=True)
            if response.status_code == 200:
                img_data = BytesIO(response.content)
                try:
                    Image.open(img_data).verify()
                    img_data.seek(0)
                    message = await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=img_data,
                        caption=text,
                        reply_markup=reply_markup
                    )
                    logger.info(f"Изображение отправлено: {image_url}")
                except Exception as e:
                    logger.error(f"Ошибка проверки изображения: {e}")
                    raise
            else:
                logger.warning(f"Не удалось загрузить изображение, статус: {response.status_code}")
                raise Exception(f"Статус: {response.status_code}")
        else:
            message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                reply_markup=reply_markup
            )
            logger.info(f"Отправлен текстовый мем")
        
        user_states[user_id]["current_meme"] = meme_id
        user_states[user_id]["viewed_memes"].append(meme_id)
        try:
            meme_analytics.record_meme_view(meme_id, user_id)
        except Exception as e:
            logger.error(f"Ошибка при записи просмотра мема: {e}")
        logger.info(f"Отправлен мем {meme_id} пользователю {user_id}")
    
    except Exception as e:
        logger.error(f"Ошибка при отправке мема {meme_id}: {e}")
        if meme_id in memes_collection:
            rejected_memes[meme_id] = memes_collection.pop(meme_id)
            save_memes_to_cache()
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Произошла ошибка при загрузке мема. Пробуем другой!"
        )
        if meme_id in user_states[user_id]["viewed_memes"]:
            user_states[user_id]["viewed_memes"].remove(meme_id)
        await send_random_meme(update, context)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий на кнопки рейтинга."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data.split(":")
    
    if data[0] == "rate":
        meme_id = data[1]
        rating = int(data[2])
        
        if user_id in user_states:
            if "ratings" not in user_states[user_id]:
                user_states[user_id]["ratings"] = {}
            user_states[user_id]["ratings"][meme_id] = rating
            
            try:
                if meme_id in memes_collection:
                    update_user_preferences(user_id, memes_collection[meme_id], rating)
                else:
                    logger.warning(f"Мем {meme_id} не найден при обновлении предпочтений")
            except Exception as e:
                logger.error(f"Ошибка при обновлении предпочтений: {e}")
            
            try:
                meme_analytics.record_meme_rating(meme_id, user_id, rating)
            except Exception as e:
                logger.error(f"Ошибка при записи оценки мема: {e}")
        
        await send_random_meme(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help."""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "🔍 Помощь по командам бота:\n\n"
            "/start - Начать просмотр мемов\n"
            "/next - Пропустить текущий мем и показать следующий\n"
            "/help - Показать эту справку\n"
            "/stats - Показать вашу статистику\n"
            "/report - Сообщить о рекламном меме\n"
            "/recommend - Получить персонализированные рекомендации"
        )
    )

async def next_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /next для пропуска текущего мема."""
    await send_random_meme(update, context)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /stats для показа статистики мемов."""
    user_id = update.effective_user.id
    
    if user_id not in user_states:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="У вас ещё нет статистики. Начните смотреть и оценивать мемы!"
        )
        return
    
    viewed_count = len(user_states[user_id].get("viewed_memes", []))
    ratings = user_states[user_id].get("ratings", {})
    positive_ratings = sum(1 for r in ratings.values() if r > 0)
    negative_ratings = sum(1 for r in ratings.values() if r < 0)
    
    try:
        preferences_stats = get_user_preferences_stats(user_id)
        history_analysis = analyze_user_history(user_id, memes_collection)
        favorite_topics = history_analysis.get("favorite_topics", [])
        topics_str = ", ".join(favorite_topics[:3]) if favorite_topics else "Офис"
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "📊 Ваша статистика:\n\n"
                f"Просмотрено мемов: {viewed_count}\n"
                f"Поставлено лайков: {positive_ratings}\n"
                f"Поставлено дизлайков: {negative_ratings}\n\n"
                f"Ваши предпочтения: {topics_str}\n\n"
                "Используйте /recommend для получения персонализированных мемов!"
            )
        )
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "📊 Ваша статистика:\n\n"
                f"Просмотрено мемов: {viewed_count}\n"
                f"Поставлено лайков: {positive_ratings}\n"
                f"Поставлено дизлайков: {negative_ratings}"
            )
        )

async def report_ad_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /report для отметки мема как рекламного."""
    user_id = update.effective_user.id
    
    if user_id not in user_states or "current_meme" not in user_states[user_id]:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Нет активного мема для жалобы. Начните просмотр с /start и потом используйте /report."
        )
        return
    
    meme_id = user_states[user_id]["current_meme"]
    
    if meme_id in memes_collection:
        rejected_memes[meme_id] = memes_collection.pop(meme_id)
        save_memes_to_cache()
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Спасибо! Мы отметили этот мем как рекламный и больше не будем его показывать."
        )
        await send_random_meme(update, context)
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Не удалось найти текущий мем. Возможно, он уже был удален."
        )

async def recommend_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /recommend для предоставления персонализированных рекомендаций."""
    user_id = update.effective_user.id
    
    if user_id not in user_states:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Пожалуйста, просмотрите и оцените несколько мемов, чтобы мы могли дать рекомендации."
        )
        return
    
    ratings = user_states[user_id].get("ratings", {})
    
    if len(ratings) < 5:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Пожалуйста, оцените еще мемов. Нужно минимум 5 оценок, а у вас {len(ratings)}."
        )
        return
    
    try:
        recommended_memes = recommend_memes(user_id, memes_collection, 1)
        if not recommended_memes:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="К сожалению, не удалось сформировать рекомендации. Попробуйте оценить больше мемов."
            )
            return
        
        meme_id = recommended_memes[0]
        if meme_id not in memes_collection:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Произошла ошибка. Рекомендованный мем недоступен."
            )
            return
        
        meme = memes_collection[meme_id]
        keyboard = [
            [
                InlineKeyboardButton("👍", callback_data=f"rate:{meme_id}:1"),
                InlineKeyboardButton("👎", callback_data=f"rate:{meme_id}:-1")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = meme.get("text", "")
        image_url = meme.get("image_url", "")
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🔍 Вот мем, который может вам понравиться:"
        )
        
        if image_url:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(image_url, headers=headers, timeout=10, stream=True)
            if response.status_code == 200:
                img_data = BytesIO(response.content)
                try:
                    Image.open(img_data).verify()
                    img_data.seek(0)
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=img_data,
                        caption=text,
                        reply_markup=reply_markup
                    )
                    logger.info(f"Рекомендованное изображение отправлено: {image_url}")
                except Exception as e:
                    logger.error(f"Ошибка проверки рекомендованного изображения: {e}")
                    raise
            else:
                logger.warning(f"Не удалось загрузить рекомендованное изображение, статус: {response.status_code}")
                raise Exception(f"Статус: {response.status_code}")
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                reply_markup=reply_markup
            )
        
        user_states[user_id]["current_meme"] = meme_id
        user_states[user_id]["viewed_memes"].append(meme_id)
        try:
            meme_analytics.record_meme_view(meme_id, user_id)
        except Exception as e:
            logger.error(f"Ошибка при записи просмотра рекомендованного мема: {e}")
    
    except Exception as e:
        logger.error(f"Ошибка при получении рекомендаций: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Произошла ошибка при формировании рекомендаций. Пожалуйста, попробуйте позже."
        )

def main():
    """Основная функция для запуска бота"""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("=== ЗАПУСК TELEGRAM БОТА НА RAILWAY ===")
    
    try:
        meme_analytics._load_analytics_files()
        logger.info("Аналитические данные успешно загружены")
    except Exception as e:
        logger.error(f"Ошибка при загрузке аналитических данных: {e}")
    
    cache_loaded = load_memes_from_cache()
    if not cache_loaded or not memes_collection:
        logger.info("Кэш мемов не загружен, инициализируем")
        init_default_memes()
    
    logger.info(f"Доступно {len(memes_collection)} мемов после фильтрации")
    logger.info(f"Отклонено {len(rejected_memes)} мемов")
    
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
        sys.exit(1)
    
    update_thread = threading.Thread(target=update_memes)
    update_thread.daemon = True
    update_thread.start()
    
    application = Application.builder().token(token).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("next", next_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("report", report_ad_command))
    application.add_handler(CommandHandler("recommend", recommend_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    LOCK_FILE = ".telegram_bot_railway_lock"
    
    def check_and_create_lock():
        if os.path.exists(LOCK_FILE):
            try:
                file_time = os.path.getmtime(LOCK_FILE)
                current_time = time.time()
                if current_time - file_time < 120:
                    try:
                        with open(LOCK_FILE, 'r') as f:
                            pid_str = f.read().strip()
                            if pid_str:
                                pid = int(pid_str)
                                try:
                                    os.kill(pid, 0)
                                    logger.warning(f"Бот уже запущен с PID {pid}. Останавливаем текущий запуск.")
                                    return False
                                except OSError:
                                    logger.warning(f"Найден lock от несуществующего процесса {pid}. Удаляем.")
                                    os.remove(LOCK_FILE)
                    except Exception as e:
                        logger.error(f"Ошибка при проверке PID в lock-файле: {e}")
                        os.remove(LOCK_FILE)
                else:
                    logger.warning(f"Найден устаревший lock-файл (возраст: {current_time - file_time:.1f}с). Удаляем.")
                    os.remove(LOCK_FILE)
            except Exception as e:
                logger.error(f"Ошибка при проверке lock-файла: {e}")
                try:
                    os.remove(LOCK_FILE)
                except:
                    pass
        
        try:
            with open(LOCK_FILE, 'w') as f:
                f.write(str(os.getpid()))
            logger.info(f"Создан lock-файл {LOCK_FILE} с PID {os.getpid()}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при создании lock-файла: {e}")
            return False
    
    def cleanup_lock():
        try:
            if os.path.exists(LOCK_FILE):
                os.remove(LOCK_FILE)
                logger.info(f"Lock-файл {LOCK_FILE} удален")
        except Exception as e:
            logger.error(f"Ошибка при удалении lock-файла: {e}")
    
    if not check_and_create_lock():
        logger.warning("Не удалось создать lock-файл или бот уже запущен. Выход.")
        sys.exit(0)
    
    original_sigterm_handler = signal.getsignal(signal.SIGTERM)
    original_sigint_handler = signal.getsignal(signal.SIGINT)
    
    def cleanup_and_forward(sig, frame):
        cleanup_lock()
        if sig == signal.SIGTERM and callable(original_sigterm_handler):
            try:
                original_sigterm_handler(sig, frame)
            except Exception as e:
                logger.error(f"Ошибка при вызове оригинального SIGTERM обработчика: {e}")
        elif sig == signal.SIGINT and callable(original_sigint_handler):
            try:
                original_sigint_handler(sig, frame)
            except Exception as e:
                logger.error(f"Ошибка при вызове оригинального SIGINT обработчика: {e}")
    
    signal.signal(signal.SIGTERM, cleanup_and_forward)
    signal.signal(signal.SIGINT, cleanup_and_forward)
    
    try:
        logger.info("Запуск бота в режиме polling...")
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            close_loop=False,
            connect_timeout=30,
            read_timeout=30
        )
    except telegram.error.Conflict as conflict_error:
        logger.error(f"Обнаружен конфликт Telegram API: {conflict_error}. Другой экземпляр бота уже запущен.")
        cleanup_lock()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        cleanup_lock()
        sys.exit(1)
    finally:
        cleanup_lock()

if __name__ == "__main__":
    main()
