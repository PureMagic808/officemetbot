#!/usr/bin/env python3
"""
Телеграм-бот с нулевой толерантностью к рекламе и функцией автоматического обновления контента.
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
# Для исправления ошибки "Import "telegram" could not be resolved"
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from meme_data import MEMES, MEME_SOURCES
from advanced_filter import is_suitable_meme_advanced
from vk_utils import VKMemesFetcher
from recommendation_engine import update_user_preferences, recommend_memes, get_user_preferences_stats, analyze_user_history
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

def main():
    """Основная функция запуска бота"""
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Проверяем, не запущен ли уже бот (предотвращаем конфликт Telegram API)
    def check_bot_process():
        try:
            import subprocess
            result = subprocess.run(
                ["ps", "aux"], 
                capture_output=True, 
                text=True
            )
            output = result.stdout
            # Ищем другие процессы бота, исключая текущий PID
            current_pid = os.getpid()
            bot_processes = []
            
            for line in output.split('\n'):
                if 'python' in line and ('bot' in line.lower() or 'telegram' in line.lower()) and str(current_pid) not in line:
                    bot_processes.append(line)
            
            if bot_processes:
                logger.warning(f"Обнаружены другие процессы бота ({len(bot_processes)}). Это может вызвать конфликт.")
                logger.warning("Первые 3 процесса:" + "\n".join(bot_processes[:3]))
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка при проверке процессов бота: {e}")
            return False
    
    # Если уже запущен экземпляр бота, просто выходим
    if check_bot_process():
        logger.warning("Бот уже запущен в другом процессе. Завершаем текущий процесс.")
        sys.exit(0)
    
    logger.info("=== ЗАПУСК TELEGRAM БОТА С НУЛЕВОЙ ТОЛЕРАНТНОСТЬЮ К РЕКЛАМЕ ===")
    
    # Получение токена Telegram бота
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("Не указан токен бота в переменной окружения TELEGRAM_BOT_TOKEN")
        sys.exit(1)
    
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
                "👋 Привет! Я бот для просмотра мемов без рекламы.\n\n"
                "Используем передовую технологию фильтрации рекламного контента. "
                "Все мемы тщательно проверяются системой фильтрации.\n\n"
                "Используйте /start для начала, 👍/👎 для оценки мема, /next для пропуска."
            )
        )
        
        # Получаем все доступные мемы, которые пользователь еще не видел
        viewed_memes = user_states[user_id].get("viewed_memes", [])
        available_memes = [meme_id for meme_id in memes_collection if meme_id not in viewed_memes]
        
        # Если все мемы просмотрены или список пуст, начинаем сначала
        if not available_memes:
            logger.info(f"Пользователь {user_id} просмотрел все мемы, сбрасываем историю")
            user_states[user_id]["viewed_memes"] = []
            available_memes = list(memes_collection.keys())
        
        # Выбираем случайный мем
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
        
        # Логируем информацию о показанном меме
        logger.info(f"Отправлен мем {meme_id} пользователю {user_id}")
    
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
        
        # Логируем информацию о показанном меме
        logger.info(f"Отправлен мем {meme_id} пользователю {user_id}")
    
    async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик нажатий на кнопки рейтинга."""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        data = query.data.split(":")
        
        if len(data) == 3 and data[0] == "rate":
            meme_id = data[1]
            rating = int(data[2])
            
            # Сохраняем оценку
            if user_id in user_states:
                if "ratings" not in user_states[user_id]:
                    user_states[user_id]["ratings"] = {}
                
                user_states[user_id]["ratings"][meme_id] = rating
                logger.info(f"Пользователь {user_id} оценил мем {meme_id}: {rating}")
                
                # Обновляем предпочтения пользователя в рекомендательной системе
                try:
                    meme = memes_collection.get(meme_id)
                    if meme:
                        # Обновляем предпочтения для рекомендательной системы
                        update_user_preferences(user_id, meme, rating)
                        logger.info(f"Обновлены предпочтения пользователя {user_id} для рекомендательной системы")
                        
                        # Записываем оценку мема в аналитику
                        meme_analytics.record_meme_rating(meme_id, user_id, rating)
                except Exception as e:
                    logger.error(f"Ошибка при обновлении предпочтений пользователя: {e}")
                
                # Редактируем сообщение, чтобы удалить кнопки
                try:
                    meme = memes_collection.get(meme_id)
                    text = meme.get("text", "") if meme else ""
                    
                    # Выбираем текст в зависимости от оценки
                    rating_text = "👍 Вам понравился этот мем!" if rating == 1 else "👎 Вам не понравился этот мем."
                    response_text = f"{rating_text}\n\nОтправляю следующий мем..."
                    
                    if query.message.photo:
                        await query.edit_message_caption(
                            caption=f"{text}\n\n{response_text}",
                            reply_markup=None
                        )
                    else:
                        await query.edit_message_text(
                            text=f"{text}\n\n{response_text}",
                            reply_markup=None
                        )
                except Exception as e:
                    logger.error(f"Ошибка при редактировании сообщения: {e}")
                
                # Отправляем следующий мем
                await send_random_meme(update, context)
    
    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /help."""
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "Я бот для просмотра мемов без рекламы! 👋\n\n"
                "📌 Команды:\n"
                "/start - Начать просмотр мемов\n"
                "/next - Пропустить текущий мем\n"
                "/stats - Показать статистику мемов\n"
                "/recommend - Получить персональные рекомендации\n"
                "/report - Отметить текущий мем как рекламный\n"
                "/help - Показать эту справку\n\n"
                "Просто нажимайте 👍 или 👎, чтобы оценить мем, и я автоматически отправлю следующий."
                "\n\nМемы автоматически обновляются и строго фильтруются от рекламы."
                "\n\n🌟 Новое! После оценки 5 мемов становятся доступны персональные рекомендации мемов."
            )
        )
    
    async def next_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /next для пропуска текущего мема."""
        user_id = update.effective_user.id
        
        if user_id in user_states and user_states[user_id].get("current_meme"):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Пропускаем текущий мем..."
            )
            await send_random_meme(update, context)
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Нет активного мема для пропуска. Используйте /start, чтобы начать просмотр."
            )
    
    async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /stats для показа статистики мемов."""
        user_id = update.effective_user.id
        
        # Подсчитываем статистику
        total_memes = len(memes_collection)
        total_rejected = len(rejected_memes)
        rejection_rate = (total_rejected / (total_memes + total_rejected)) * 100 if (total_memes + total_rejected) > 0 else 0
        
        viewed_count = len(user_states.get(user_id, {}).get("viewed_memes", []))
        liked_count = sum(1 for rating in user_states.get(user_id, {}).get("ratings", {}).values() if rating > 0)
        disliked_count = sum(1 for rating in user_states.get(user_id, {}).get("ratings", {}).values() if rating < 0)
        
        # Получаем данные о предпочтениях пользователя для рекомендательной системы
        try:
            user_prefs = get_user_preferences_stats(user_id)
            
            # Формируем сообщение о рекомендациях
            rec_message = ""
            if user_prefs["has_recommendations"]:
                # Если есть достаточно данных для рекомендаций
                rec_message = "\n\n🌟 Система рекомендаций активирована!\n"
                if user_prefs["top_keywords"] and len(user_prefs["top_keywords"]) > 0:
                    keywords = ", ".join(user_prefs["top_keywords"][:3])  # Показываем только топ-3 ключевых слова
                    rec_message += f"Судя по вашим оценкам, вам нравятся мемы с темами: {keywords}"
            else:
                # Если недостаточно данных
                ratings_needed = 5 - user_prefs["total_ratings"]
                if ratings_needed > 0:
                    rec_message = f"\n\n💫 Оцените еще {ratings_needed} мемов, чтобы активировать персональные рекомендации!"
                else:
                    rec_message = "\n\n💫 Скоро будут доступны персональные рекомендации!"
        except Exception as e:
            logger.error(f"Ошибка при получении данных рекомендательной системы: {e}")
            rec_message = "\n\nℹ️ Информация о рекомендациях временно недоступна."
        
        # Анализируем настроение пользователя на основе оценок
        mood_message = ""
        try:
            # Получаем последние 10 оценок пользователя
            ratings = user_states.get(user_id, {}).get("ratings", {})
            if ratings:
                # Считаем соотношение положительных и отрицательных
                positive_count = sum(1 for r in ratings.values() if r > 0)
                negative_count = sum(1 for r in ratings.values() if r < 0)
                total_ratings = len(ratings)
                
                if total_ratings >= 3:  # Минимум 3 оценки для определения настроения
                    positive_ratio = positive_count / total_ratings
                    
                    if positive_ratio >= 0.7:
                        mood_message = "\n\n😄 Похоже, у вас отличное настроение! Продолжаем подбирать позитивные мемы."
                    elif positive_ratio <= 0.3:
                        mood_message = "\n\n😔 Кажется, мемы вас не очень радуют. Попробуем найти что-то более интересное!"
                    else:
                        mood_message = "\n\n🙂 Ваше настроение нейтральное. Стараемся подобрать самые интересные мемы!"
        except Exception as e:
            logger.error(f"Ошибка при анализе настроения пользователя: {e}")
        
        # Анализ предпочтений
        preferences_message = ""
        try:
            ratings = user_states.get(user_id, {}).get("ratings", {})
            if len(ratings) >= 5:
                # Анализируем, какие темы нравятся пользователю
                liked_memes = [meme_id for meme_id, rating in ratings.items() if rating > 0]
                keywords = set()
                
                for meme_id in liked_memes:
                    if meme_id in memes_collection:
                        meme_text = memes_collection[meme_id].get("text", "")
                        if meme_text and len(meme_text.split()) >= 3:  # Проверяем, что текст не пустой и не слишком короткий
                            # Добавляем теги мема
                            meme_tags = memes_collection[meme_id].get("tags", [])
                            keywords.update(meme_tags)
                
                if keywords:
                    top_keywords = list(keywords)[:3]  # Берем до 3 ключевых слов
                    if top_keywords:
                        preferences_message = f"\n\n🎯 Судя по вашим оценкам, вам нравятся мемы с темой '{', '.join(top_keywords)}'"
        except Exception as e:
            logger.error(f"Ошибка при анализе предпочтений пользователя: {e}")
                    
        # Статистика обновления контента
        update_message = ""
        try:
            # Отображаем информацию о частоте обновления мемов
            update_message = "\n\n🔄 Мемы автоматически обновляются и проходят усиленную фильтрацию рекламы каждый час!"
        except Exception as e:
            logger.error(f"Ошибка при формировании сообщения об обновлениях: {e}")
        
        # Отправляем статистику
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "📊 Статистика мемов:\n\n"
                f"Всего мемов (без рекламы): {total_memes}\n"
                f"Заблокировано рекламных мемов: {total_rejected}\n"
                f"Процент блокировки рекламы: {rejection_rate:.1f}%\n\n"
                f"Вы просмотрели: {viewed_count}\n"
                f"Понравились: {liked_count} 👍\n"
                f"Не понравились: {disliked_count} 👎"
                f"{rec_message}"
                f"{mood_message}"
                f"{preferences_message}"
                f"{update_message}"
            )
        )
    
    async def report_ad_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /report для отметки мема как рекламного."""
        user_id = update.effective_user.id
        
        if user_id in user_states and user_states[user_id].get("current_meme"):
            current_meme_id = user_states[user_id]["current_meme"]
            
            # Если мем существует в коллекции
            if current_meme_id in memes_collection:
                # Перемещаем мем из обычной коллекции в отклоненные
                reported_meme = memes_collection[current_meme_id]
                rejected_memes[current_meme_id] = reported_meme
                del memes_collection[current_meme_id]
                
                # Добавляем метку что мем был отмечен пользователем
                rejected_memes[current_meme_id]["reported_by_user"] = True
                rejected_memes[current_meme_id]["report_timestamp"] = datetime.now().isoformat()
                
                # Сохраняем обновленные коллекции
                save_memes_to_cache()
                
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Спасибо! Этот мем отмечен как рекламный и будет заблокирован для всех пользователей."
                )
                
                # Отправляем новый мем
                await send_random_meme(update, context)
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Не удалось найти текущий мем для отметки. Попробуйте еще раз с другим мемом."
                )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Нет активного мема для отметки. Используйте /start, чтобы начать просмотр, а затем /report для отметки рекламы."
            )
    
    async def recommend_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /recommend для предоставления персонализированных рекомендаций."""
        user_id = update.effective_user.id
        
        # Проверяем, есть ли у пользователя достаточно оценок для рекомендаций
        ratings = user_states.get(user_id, {}).get("ratings", {})
        
        if len(ratings) < 5:
            # Если оценок мало, сообщаем сколько еще нужно
            ratings_needed = 5 - len(ratings)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Для персональных рекомендаций нужно оценить как минимум 5 мемов. Вам осталось оценить еще {ratings_needed}."
            )
            return
        
        # Получаем анализ предпочтений пользователя
        try:
            analysis = analyze_user_history(user_id, memes_collection)
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=(
                    "🔍 Ваши предпочтения в мемах:\n\n"
                    f"{analysis['message']}\n\n"
                    "Отправляю персонализированную рекомендацию..."
                )
            )
            
            # Отправляем рекомендованный мем
            if analysis['recommendations']:
                meme_id = analysis['recommendations'][0]
                
                # Обновляем текущий мем пользователя
                user_states[user_id]["current_meme"] = meme_id
                
                # Добавляем в просмотренные, если еще нет
                if meme_id not in user_states[user_id].get("viewed_memes", []):
                    user_states[user_id].setdefault("viewed_memes", []).append(meme_id)
                
                # Получаем мем и отправляем
                meme = memes_collection.get(meme_id)
                if meme:
                    # Создаем клавиатуру для оценки
                    keyboard = [
                        [
                            InlineKeyboardButton("👍", callback_data=f"rate:{meme_id}:1"),
                            InlineKeyboardButton("👎", callback_data=f"rate:{meme_id}:-1")
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    text = meme.get("text", "")
                    image_url = meme.get("image_url", "")
                    
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
                    
                    logger.info(f"Отправлена персональная рекомендация {meme_id} пользователю {user_id}")
                else:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="Извините, не удалось найти рекомендованный мем. Попробуйте еще раз или используйте /next."
                    )
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Не удалось сформировать рекомендации. Попробуйте оценить больше мемов."
                )
        
        except Exception as e:
            logger.error(f"Ошибка при выполнении команды recommend: {e}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Произошла ошибка при формировании рекомендаций. Пожалуйста, попробуйте позже."
            )
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("next", next_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("report", report_ad_command))
    application.add_handler(CommandHandler("recommend", recommend_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Проверяем наличие lockfile, чтобы избежать двойного запуска бота
    lockfile = ".telegram_bot_lock"
    if os.path.exists(lockfile):
        # Проверяем, актуален ли lockfile (создан не более 10 минут назад)
        try:
            file_time = os.path.getmtime(lockfile)
            current_time = time.time()
            if current_time - file_time < 600:  # 10 минут в секундах
                logger.warning(f"Обнаружен lockfile ({lockfile}). Бот уже запущен!")
                logger.warning("Завершаем текущий процесс бота для избежания конфликта")
                sys.exit(0)
            else:
                # Если lockfile устарел, удаляем его
                logger.warning(f"Обнаружен устаревший lockfile. Удаляем.")
                os.remove(lockfile)
        except Exception as e:
            logger.error(f"Ошибка при проверке lockfile: {e}")
            # На всякий случай удаляем lockfile
            try:
                os.remove(lockfile)
            except:
                pass
    
    # Создаем lockfile
    try:
        with open(lockfile, 'w') as f:
            f.write(str(os.getpid()))
    except Exception as e:
        logger.error(f"Ошибка при создании lockfile: {e}")
    
    try:
        # Запускаем бота в режиме polling
        logger.info("Запуск бота в режиме polling...")
        application.run_polling()
    except telegram.error.Conflict as e:
        logger.error(f"Конфликт Telegram API: {e}")
        logger.error("Обнаружен другой запущенный экземпляр бота. Завершаем работу.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        # Удаляем lockfile при завершении
        try:
            if os.path.exists(lockfile):
                os.remove(lockfile)
        except Exception as e:
            logger.error(f"Ошибка при удалении lockfile: {e}")

if __name__ == "__main__":
    main()
