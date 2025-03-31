#!/usr/bin/env python3
"""
Основной файл для запуска Telegram-бота на Railway.
Этот файл объединяет основную функциональность бота для запуска на хостинге.
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

# Для работы с Telegram API
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Импортируем собственные модули
from meme_data import MEMES, MEME_SOURCES
from advanced_filter import is_suitable_meme_advanced
from vk_utils import VKMemesFetcher
from recommendation_engine import (
    update_user_preferences, 
    recommend_memes, 
    get_user_preferences_stats, 
    analyze_user_history
)
import meme_analytics

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
UPDATE_INTERVAL = 3600  # Интервал обновления в секундах (1 час)
MIN_MEMES_COUNT = 50    # Минимальное количество мемов, которое должно быть доступно
MAX_MEMES_TO_FETCH = 20 # Максимальное количество мемов для получения за одно обновление

# Получение группы ВК для мемов офисных работников
VK_GROUP_IDS = [212383311, 122474322, 199128812, 211736252, 57846937, 174497945, 203067105, 207831020, 162629380, 164118441]

# Флаг для управления процессом обновления
update_thread_running = False

def signal_handler(sig, frame):
    """Обработчик сигнала для корректного завершения работы бота"""
    logger.info("Получен сигнал завершения. Завершаем работу бота...")
    global update_thread_running
    update_thread_running = False
    # Сохраняем мемы перед выходом
    save_memes_to_cache()
    sys.exit(0)

def save_memes_to_cache():
    """Сохраняет коллекцию мемов в файл кэша"""
    try:
        with open(MEMES_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(memes_collection, f, ensure_ascii=False, indent=2)
        logger.info(f"Сохранено {len(memes_collection)} мемов в кэш")
        
        # Сохраняем также отклоненные мемы для дальнейшего анализа
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

def update_memes():
    """Функция для периодического обновления мемов"""
    global update_thread_running
    global memes_collection
    
    try:
        # VK API токен для доступа к мемам с публичных страниц
        vk_token = os.environ.get("VK_TOKEN", "")
        if not vk_token:
            logger.warning("VK_TOKEN не найден, будет использована только стандартная коллекция мемов")
            # Копируем стандартную коллекцию, если нет токена VK
            if not memes_collection:
                for meme_id, meme_data in MEMES.items():
                    if is_suitable_meme_advanced(meme_data):
                        memes_collection[meme_id] = meme_data
                    else:
                        rejected_memes[meme_id] = meme_data
            return
        
        # Инициализация клиента VK
        vk_client = VKMemesFetcher(vk_token)
        
        update_thread_running = True
        logger.info("Запущен поток обновления мемов")
        
        # Если у нас нет кэшированных мемов, инициализируем из статического списка
        if not memes_collection:
            for meme_id, meme_data in MEMES.items():
                if is_suitable_meme_advanced(meme_data):
                    memes_collection[meme_id] = meme_data
                else:
                    rejected_memes[meme_id] = meme_data
            save_memes_to_cache()
        
        while update_thread_running:
            try:
                # Проверяем, нужно ли обновление (если мемов меньше минимального количества)
                if len(memes_collection) < MIN_MEMES_COUNT:
                    logger.info(f"Количество мемов ({len(memes_collection)}) меньше минимального {MIN_MEMES_COUNT}. Запускаем обновление...")
                    fetch_and_add_new_memes(vk_client, MAX_MEMES_TO_FETCH)
                
                # Периодическое обновление
                logger.info("Выполняется регулярное обновление мемов...")
                fetch_and_add_new_memes(vk_client, 10)  # Получаем 10 мемов за раз
                
                # Сохраняем обновленную коллекцию
                save_memes_to_cache()
                
                # Ждем заданный интервал перед следующим обновлением
                time.sleep(UPDATE_INTERVAL)
            except Exception as e:
                logger.error(f"Ошибка в процессе обновления мемов: {e}")
                time.sleep(60)  # В случае ошибки ждем минуту и пробуем снова
    except Exception as e:
        logger.error(f"Критическая ошибка в потоке обновления мемов: {e}")
        update_thread_running = False

def fetch_and_add_new_memes(vk_client, count=10):
    """Получает новые мемы из VK и добавляет их в коллекцию"""
    global memes_collection, rejected_memes
    
    logger.info(f"Получение {count} новых мемов...")
    new_memes_count = 0
    rejected_count = 0
    attempts = 0
    max_attempts = count * 5  # Увеличили максимум попыток получения для лучшего фильтра
    
    while new_memes_count < count and attempts < max_attempts:
        attempts += 1
        
        try:
            # Получаем случайный мем из VK
            image_url, text = vk_client.get_random_meme(VK_GROUP_IDS)
            
            if not image_url:
                logger.warning("Не удалось получить URL изображения мема")
                continue
            
            # Создаем новый ID для мема на основе хеша URL и текста
            meme_id = f"vk_{abs(hash(image_url + text))}"
            
            # Проверяем, есть ли такой мем уже в коллекции или в отклоненных
            if meme_id in memes_collection or meme_id in rejected_memes:
                logger.debug(f"Мем {meme_id} уже существует в коллекции или отклонен ранее")
                continue
            
            # Создаем объект мема
            new_meme = {
                "image_url": image_url,
                "text": text,
                "source": "vk_auto_update",
                "tags": ["офис", "мем", "автообновление"],
                "timestamp": datetime.now().isoformat()
            }
            
            # Проверяем через улучшенный фильтр контента
            if is_suitable_meme_advanced(new_meme):
                memes_collection[meme_id] = new_meme
                new_memes_count += 1
                logger.info(f"Добавлен новый мем {meme_id}")
            else:
                rejected_memes[meme_id] = new_meme
                rejected_count += 1
                logger.info(f"Отклонен мем {meme_id} как неподходящий (реклама)")
        
        except Exception as e:
            logger.error(f"Ошибка при получении мема: {e}")
    
    logger.info(f"Получено {new_memes_count} новых мемов, отклонено {rejected_count} из {attempts} попыток")
    return new_memes_count

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start. Отправляет первый мем пользователю."""
    user = update.effective_user
    user_id = user.id
    username = user.username
    
    logger.info(f"Команда /start от пользователя {username} (ID: {user_id})")
    
    # Инициализируем состояние пользователя
    if user_id not in user_states:
        user_states[user_id] = {
            "username": username,
            "current_meme": None,
            "viewed_memes": [],
            "ratings": {}
        }
        
    # Записываем активность пользователя в аналитику
    try:
        meme_analytics.record_user_session(user_id)
    except Exception as e:
        logger.error(f"Ошибка при записи сессии пользователя в аналитику: {e}")
    
    # Приветственное сообщение
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "👋 Привет! Я бот для просмотра мемов.\n"
            "Используйте /start для начала, 👍/👎 для оценки мема, /next для пропуска."
        )
    )
    
    # Отправляем первый мем
    await send_random_meme(update, context)

async def send_random_meme(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет случайный мем пользователю."""
    user = update.effective_user
    user_id = user.id
    
    if user_id not in user_states:
        # Если пользователь не инициализирован, запускаем start
        await start(update, context)
        return
    
    # Получаем все доступные мемы, которые пользователь еще не видел
    viewed_memes = user_states[user_id].get("viewed_memes", [])
    available_memes = [meme_id for meme_id in memes_collection if meme_id not in viewed_memes]
    
    # Если все мемы просмотрены или доступных мемов мало, начинаем сначала
    if not available_memes or len(available_memes) < 5:
        logger.info(f"Пользователь {user_id} просмотрел все мемы, сбрасываем историю")
        user_states[user_id]["viewed_memes"] = []
        available_memes = list(memes_collection.keys())
    
    # Проверяем, достаточно ли оценок у пользователя для рекомендаций
    ratings = user_states[user_id].get("ratings", {})
    
    if len(ratings) >= 5:
        # У пользователя достаточно оценок для персонализированных рекомендаций
        try:
            # Получаем рекомендованные мемы для пользователя
            recommended_memes = recommend_memes(user_id, memes_collection, 10)
            
            # Выбираем мем из рекомендованных, который пользователь еще не видел
            recommended_unseen = [m for m in recommended_memes if m not in viewed_memes]
            
            if recommended_unseen:
                # Если есть непросмотренные рекомендации, используем их
                logger.info(f"Отправляем персонализированную рекомендацию для пользователя {user_id}")
                meme_id = recommended_unseen[0]  # Берем первый рекомендованный мем
            else:
                # Если нет, выбираем случайный мем
                meme_id = random.choice(available_memes)
        except Exception as e:
            logger.error(f"Ошибка при получении рекомендаций: {e}")
            # В случае ошибки выбираем случайный мем
            meme_id = random.choice(available_memes)
    else:
        # Недостаточно оценок для рекомендаций - выбираем случайный мем
        meme_id = random.choice(available_memes)
    meme = memes_collection[meme_id]
    
    # Создаем клавиатуру для оценки
    keyboard = [
        [
            InlineKeyboardButton("👍", callback_data=f"rate:{meme_id}:1"),
            InlineKeyboardButton("👎", callback_data=f"rate:{meme_id}:-1")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем мем пользователю
    text = meme.get("text", "")
    image_url = meme.get("image_url", "")
    
    try:
        if image_url:
            message = await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=image_url,
                caption=text,
                reply_markup=reply_markup
            )
        else:
            message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                reply_markup=reply_markup
            )
        
        # Обновляем состояние пользователя
        user_states[user_id]["current_meme"] = meme_id
        user_states[user_id]["viewed_memes"].append(meme_id)
        
        # Записываем просмотр в аналитику
        try:
            meme_analytics.record_meme_view(meme_id, user_id)
        except Exception as e:
            logger.error(f"Ошибка при записи просмотра мема в аналитику: {e}")
        
        # Логируем информацию о показанном меме
        logger.info(f"Отправлен мем {meme_id} пользователю {user_id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке мема: {e}")
        # В случае ошибки с текущим мемом, попробуем другой
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Произошла ошибка при загрузке мема. Давайте попробуем другой!"
        )
        # Помечаем проблемный мем
        if meme_id in memes_collection:
            logger.warning(f"Удаляем проблемный мем {meme_id} из коллекции")
            rejected_memes[meme_id] = memes_collection.pop(meme_id)
            save_memes_to_cache()
        
        # Рекурсивно вызываем функцию еще раз для отправки другого мема
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
        
        # Обновляем рейтинг мема в состоянии пользователя
        if user_id in user_states:
            if "ratings" not in user_states[user_id]:
                user_states[user_id]["ratings"] = {}
            user_states[user_id]["ratings"][meme_id] = rating
            
            # Обновляем предпочтения пользователя для рекомендаций
            try:
                update_user_preferences(user_id, meme_id, rating, memes_collection)
            except Exception as e:
                logger.error(f"Ошибка при обновлении предпочтений пользователя: {e}")
            
            # Записываем оценку в аналитику
            try:
                meme_analytics.record_meme_rating(meme_id, user_id, rating)
            except Exception as e:
                logger.error(f"Ошибка при записи оценки мема в аналитику: {e}")
        
        # Отправляем следующий мем
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
            "/stats - Показать статистику просмотренных мемов\n"
            "/report - Отметить текущий мем как рекламный\n"
            "/recommend - Получить персонализированные рекомендации\n\n"
            "Используйте кнопки 👍/👎 для оценки мемов. "
            "Чем больше мемов вы оцените, тем лучше будут персональные рекомендации!"
        )
    )

async def next_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /next для пропуска текущего мема."""
    user_id = update.effective_user.id
    
    if user_id in user_states:
        # Просто отправляем следующий мем без записи оценки
        await send_random_meme(update, context)
    else:
        # Если пользователь не инициализирован, запускаем start
        await start(update, context)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /stats для показа статистики мемов."""
    user_id = update.effective_user.id
    
    if user_id not in user_states:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="У вас пока нет статистики. Начните просмотр мемов с команды /start."
        )
        return
    
    viewed_count = len(user_states[user_id].get("viewed_memes", []))
    ratings = user_states[user_id].get("ratings", {})
    positive_count = sum(1 for r in ratings.values() if r > 0)
    negative_count = sum(1 for r in ratings.values() if r < 0)
    
    # Получаем статистику о предпочтениях пользователя
    try:
        preferences = get_user_preferences_stats(user_id)
        mood = "Определение настроения:"
        
        if preferences:
            for category, score in preferences.items():
                if score > 0:
                    mood += f"\n• {category}: {'❤️' * min(int(score/20)+1, 5)}"
    except Exception as e:
        logger.error(f"Ошибка при получении статистики предпочтений: {e}")
        mood = "Не удалось определить предпочтения."
    
    # Общая статистика по всем пользователям
    try:
        engagement_stats = meme_analytics.get_user_engagement_stats()
        total_users = engagement_stats.get("total_users", 0)
        total_ratings = engagement_stats.get("total_ratings", 0)
    except Exception as e:
        logger.error(f"Ошибка при получении общей статистики: {e}")
        total_users = 0
        total_ratings = 0
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "📊 Ваша статистика:\n\n"
            f"Просмотрено мемов: {viewed_count}\n"
            f"Понравилось: {positive_count}\n"
            f"Не понравилось: {negative_count}\n\n"
            f"{mood}\n\n"
            f"🌍 Общая статистика:\n"
            f"Всего пользователей: {total_users}\n"
            f"Всего оценок: {total_ratings}\n"
            f"Доступно мемов: {len(memes_collection)}"
        )
    )

async def report_ad_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /report для отметки мема как рекламного."""
    user_id = update.effective_user.id
    
    if user_id not in user_states or "current_meme" not in user_states[user_id]:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Нет активного мема для отметки. Начните просмотр с команды /start."
        )
        return
    
    current_meme_id = user_states[user_id]["current_meme"]
    
    if current_meme_id in memes_collection:
        # Перемещаем мем из основной коллекции в отклоненные
        meme = memes_collection.pop(current_meme_id)
        rejected_memes[current_meme_id] = meme
        logger.info(f"Мем {current_meme_id} отмечен как рекламный пользователем {user_id}")
        
        # Сохраняем обновленную коллекцию
        save_memes_to_cache()
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Спасибо! Мем отмечен как рекламный и будет исключен из показов. Переходим к следующему мему."
        )
        
        # Показываем следующий мем
        await send_random_meme(update, context)
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Мем не найден в коллекции. Возможно, он уже был отмечен или удален."
        )
        await send_random_meme(update, context)

async def recommend_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /recommend для предоставления персонализированных рекомендаций."""
    user_id = update.effective_user.id
    
    if user_id not in user_states:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="У вас пока нет оценок для рекомендаций. Начните просмотр с команды /start."
        )
        return
    
    ratings = user_states[user_id].get("ratings", {})
    
    if len(ratings) < 5:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Для качественных рекомендаций нужно оценить хотя бы 5 мемов. Вы оценили: {len(ratings)}. Продолжайте просмотр!"
        )
        return
    
    try:
        # Получаем рекомендации на основе предпочтений пользователя
        recommended_memes = recommend_memes(user_id, memes_collection, 5)
        
        # Проверяем, что рекомендации получены
        if not recommended_memes:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Не удалось сформировать рекомендации. Попробуйте оценить больше разнообразных мемов."
            )
            return
        
        # Отправляем сообщение о рекомендациях
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🔍 Вот мемы, которые должны вам понравиться на основе ваших предпочтений:"
        )
        
        # Показываем первую рекомендацию
        meme_id = recommended_memes[0]
        meme = memes_collection[meme_id]
        
        # Создаем клавиатуру для оценки
        keyboard = [
            [
                InlineKeyboardButton("👍", callback_data=f"rate:{meme_id}:1"),
                InlineKeyboardButton("👎", callback_data=f"rate:{meme_id}:-1")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Отправляем рекомендованный мем
        text = meme.get("text", "")
        image_url = meme.get("image_url", "")
        
        try:
            if image_url:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=image_url,
                    caption=text,
                    reply_markup=reply_markup
                )
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=text,
                    reply_markup=reply_markup
                )
            
            # Обновляем состояние пользователя
            user_states[user_id]["current_meme"] = meme_id
            if meme_id not in user_states[user_id]["viewed_memes"]:
                user_states[user_id]["viewed_memes"].append(meme_id)
            
            # Записываем просмотр в аналитику
            try:
                meme_analytics.record_meme_view(meme_id, user_id)
            except Exception as e:
                logger.error(f"Ошибка при записи просмотра рекомендованного мема в аналитику: {e}")
        
        except Exception as e:
            logger.error(f"Ошибка при отправке рекомендованного мема: {e}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Произошла ошибка при загрузке рекомендованного мема. Попробуйте выполнить команду /start."
            )
    
    except Exception as e:
        logger.error(f"Ошибка при формировании рекомендаций: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Произошла ошибка при формировании рекомендаций. Попробуйте позже."
        )

def main():
    """Основная функция для запуска бота"""
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("=== ЗАПУСК TELEGRAM БОТА НА RAILWAY ===")
    
    # Получение токена Telegram бота из переменных окружения
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("ОШИБКА: Не указан токен бота в переменной окружения TELEGRAM_BOT_TOKEN")
        logger.error("==================== ИНСТРУКЦИЯ ====================")
        logger.error("Для работы бота на Railway необходимо настроить переменную окружения TELEGRAM_BOT_TOKEN:")
        logger.error("1. Откройте ваш проект на Railway")
        logger.error("2. Перейдите в раздел Variables")
        logger.error("3. Добавьте переменную TELEGRAM_BOT_TOKEN с вашим токеном от @BotFather")
        logger.error("4. Перезапустите деплой, нажав кнопку 'Redeploy'")
        logger.error("=====================================================")
        # Завершаем работу бота с ошибкой, так как без токена он не может работать
        logger.error("Бот не может быть запущен без действительного токена. Завершение работы.")
        sys.exit(1)
    
    # Загружаем аналитические данные
    try:
        meme_analytics._load_analytics_files()
        logger.info("Аналитические данные успешно загружены")
    except Exception as e:
        logger.error(f"Ошибка при загрузке аналитических данных: {e}")
    
    # Загружаем мемы из кэша или используем стандартную коллекцию
    if not load_memes_from_cache():
        logger.info("Кэш мемов не найден, используем стандартную коллекцию")
        for meme_id, meme_data in MEMES.items():
            if is_suitable_meme_advanced(meme_data):
                memes_collection[meme_id] = meme_data
            else:
                rejected_memes[meme_id] = meme_data
    
    logger.info(f"Доступно {len(memes_collection)} мемов после агрессивной фильтрации рекламы")
    logger.info(f"Отклонено {len(rejected_memes)} мемов как рекламные")
    
    # Запускаем поток обновления мемов
    update_thread = threading.Thread(target=update_memes)
    update_thread.daemon = True
    update_thread.start()
    
    # Создаем приложение бота
    application = Application.builder().token(token).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("next", next_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("report", report_ad_command))
    application.add_handler(CommandHandler("recommend", recommend_command))
    
    # Регистрируем обработчик кнопок
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Запускаем бота
    logger.info("Запуск бота в режиме polling...")
    application.run_polling()

if __name__ == "__main__":
    main()
