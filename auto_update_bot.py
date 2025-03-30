#!/usr/bin/env python3
"""
Телеграм-бот с функцией автоматического обновления контента мемов
и улучшенной фильтрацией рекламы.
"""
import logging
import os
import signal
import sys
import threading
import time
import random
import json
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from meme_data import MEMES, MEME_SOURCES
from content_filter import is_suitable_meme
from vk_utils import VKMemesFetcher

# Настройка логирования
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stdout)
logger = logging.getLogger(__name__)

# Путь к файлу для сохранения мемов
MEMES_CACHE_FILE = "cached_memes.json"

# Словарь для хранения состояния пользователей
user_states = {}

# Кэшированные отфильтрованные мемы
memes_collection = {}

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
    except Exception as e:
        logger.error(f"Ошибка при сохранении мемов в кэш: {e}")

def load_memes_from_cache():
    """Загружает мемы из файла кэша, если он существует"""
    global memes_collection
    try:
        if os.path.exists(MEMES_CACHE_FILE):
            with open(MEMES_CACHE_FILE, 'r', encoding='utf-8') as f:
                loaded_memes = json.load(f)
                if loaded_memes and isinstance(loaded_memes, dict):
                    memes_collection = loaded_memes
                    logger.info(f"Загружено {len(memes_collection)} мемов из кэша")
                    return True
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
                    if is_suitable_meme(meme_data):
                        memes_collection[meme_id] = meme_data
            return
        
        # Инициализация клиента VK
        vk_client = VKMemesFetcher(vk_token)
        
        update_thread_running = True
        logger.info("Запущен поток обновления мемов")
        
        # Если у нас нет кэшированных мемов, инициализируем из статического списка
        if not memes_collection:
            for meme_id, meme_data in MEMES.items():
                if is_suitable_meme(meme_data):
                    memes_collection[meme_id] = meme_data
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
    global memes_collection
    
    logger.info(f"Получение {count} новых мемов...")
    new_memes_count = 0
    attempts = 0
    max_attempts = count * 2  # Максимум попыток получения мемов
    
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
            
            # Проверяем, есть ли такой мем уже в коллекции
            if meme_id in memes_collection:
                logger.debug(f"Мем {meme_id} уже существует в коллекции")
                continue
            
            # Создаем объект мема
            new_meme = {
                "image_url": image_url,
                "text": text,
                "source": "vk_auto_update",
                "tags": ["офис", "мем", "автообновление"],
                "timestamp": datetime.now().isoformat()
            }
            
            # Проверяем через фильтр контента
            if is_suitable_meme(new_meme):
                memes_collection[meme_id] = new_meme
                new_memes_count += 1
                logger.info(f"Добавлен новый мем {meme_id}")
            else:
                logger.info(f"Мем отфильтрован как неподходящий")
        
        except Exception as e:
            logger.error(f"Ошибка при получении мема: {e}")
    
    logger.info(f"Получено {new_memes_count} новых мемов из {attempts} попыток")
    return new_memes_count

def main():
    """Основная функция запуска бота"""
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("=== ЗАПУСК TELEGRAM БОТА С АВТООБНОВЛЕНИЕМ МЕМОВ ===")
    
    # Получение токена Telegram бота
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("Не указан токен бота в переменной окружения TELEGRAM_BOT_TOKEN")
        sys.exit(1)
    
    # Загружаем мемы из кэша или используем стандартную коллекцию
    if not load_memes_from_cache():
        logger.info("Кэш мемов не найден, используем стандартную коллекцию")
        for meme_id, meme_data in MEMES.items():
            if is_suitable_meme(meme_data):
                memes_collection[meme_id] = meme_data
    
    logger.info(f"Доступно {len(memes_collection)} мемов")
    
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
                "Я бот для просмотра мемов! 👋\n\n"
                "📌 Команды:\n"
                "/start - Начать просмотр мемов\n"
                "/next - Пропустить текущий мем\n"
                "/stats - Показать статистику мемов\n"
                "/help - Показать эту справку\n\n"
                "Просто нажимайте 👍 или 👎, чтобы оценить мем, и я автоматически отправлю следующий."
                "\n\nМемы автоматически обновляются из источников."
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
        viewed_count = len(user_states.get(user_id, {}).get("viewed_memes", []))
        liked_count = sum(1 for rating in user_states.get(user_id, {}).get("ratings", {}).values() if rating > 0)
        disliked_count = sum(1 for rating in user_states.get(user_id, {}).get("ratings", {}).values() if rating < 0)
        
        # Отправляем статистику
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "📊 Статистика мемов:\n\n"
                f"Всего мемов: {total_memes}\n"
                f"Вы просмотрели: {viewed_count}\n"
                f"Понравились: {liked_count} 👍\n"
                f"Не понравились: {disliked_count} 👎\n\n"
                "Мемы автоматически обновляются каждый час!"
            )
        )
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("next", next_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Запускаем бота
    logger.info("Запуск бота в режиме polling...")
    application.run_polling()

if __name__ == "__main__":
    main()