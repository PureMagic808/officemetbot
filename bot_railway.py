#!/usr/bin/env python3
"""
Улучшенный файл для запуска Telegram-бота на Railway с исправлениями проблем загрузки мемов.
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
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, error
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Импортируем собственные модули
from meme_data import MEMES, MEME_SOURCES
from advanced_filter import is_suitable_meme_advanced
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

def init_default_memes():
    """
    Инициализирует базовый набор мемов из встроенной коллекции MEMES.
    Это гарантирует, что у бота всегда будет стартовый набор мемов.
    """
    global memes_collection, rejected_memes
    
    logger.info("Инициализация стандартного набора мемов")
    count_added = 0
    count_rejected = 0
    
    # Проходим по всем мемам из статической коллекции
    for meme_id, meme_data in MEMES.items():
        # Получаем URL изображения
        image_url = meme_data.get("image_url", "")
        
        # Проверяем доступность изображения, если оно есть
        is_image_valid = True
        if image_url:
            try:
                import requests
                from io import BytesIO
                from PIL import Image
                
                # Быстрая проверка URL через HEAD-запрос
                response = requests.head(image_url, timeout=5)
                
                if response.status_code != 200:
                    logger.warning(f"Изображение мема {meme_id} недоступно: {image_url}, статус: {response.status_code}")
                    is_image_valid = False
                else:
                    # Дополнительная проверка через загрузку начала изображения
                    try:
                        response = requests.get(image_url, timeout=5, stream=True)
                        if response.status_code == 200:
                            # Проверяем, что это действительно изображение
                            img_data = BytesIO(response.content)
                            Image.open(img_data).verify()
                        else:
                            logger.warning(f"Изображение мема {meme_id} не загружается: {image_url}, статус: {response.status_code}")
                            is_image_valid = False
                    except Exception as img_error:
                        logger.error(f"Ошибка при проверке формата изображения мема {meme_id}: {img_error}")
                        is_image_valid = False
            except Exception as request_error:
                logger.error(f"Ошибка при проверке доступности изображения мема {meme_id}: {request_error}")
                # Даже если проверка не удалась, мы все равно попробуем позже отправить этот мем
        
        # Проверяем, подходит ли мем по критериям фильтрации и доступно ли изображение
        if is_suitable_meme_advanced(meme_data) and is_image_valid:
            # Добавляем в основную коллекцию
            memes_collection[meme_id] = meme_data
            count_added += 1
            logger.info(f"Добавлен стандартный мем {meme_id}")
        else:
            # Добавляем в список отклоненных
            rejected_memes[meme_id] = meme_data
            count_rejected += 1
            if not is_image_valid:
                logger.info(f"Отклонен стандартный мем {meme_id} из-за проблем с изображением")
            else:
                logger.info(f"Отклонен стандартный мем {meme_id} как неподходящий (реклама или другой фильтр)")
    
    logger.info(f"Инициализировано {count_added} подходящих мемов и {count_rejected} отклоненных мемов")
    return count_added > 0

def try_fetch_memes_from_vk():
    """
    Пытается получить мемы из VK API или возвращает False, 
    если это невозможно (например, нет токена)
    """
    try:
        # VK API токен для доступа к мемам с публичных страниц
        vk_token = os.environ.get("VK_TOKEN", "")
        if not vk_token:
            logger.warning("VK_TOKEN не найден, использование только стандартной коллекции мемов")
            return False
        
        # Импортируем VK-утилиты только если есть токен
        try:
            from vk_utils import VKMemesFetcher
        except ImportError as e:
            logger.error(f"Не удалось импортировать VKMemesFetcher: {e}")
            return False
        
        # Инициализация клиента VK
        vk_client = VKMemesFetcher(vk_token)
        
        # Выполняем пробный вызов, чтобы убедиться, что API работает
        test_success = False
        try:
            # Пробуем получить один мем для проверки
            image_url, text = vk_client.get_random_meme(VK_GROUP_IDS)
            if image_url:
                test_success = True
        except Exception as e:
            logger.error(f"Тестовый вызов VK API не удался: {e}")
            return False
        
        return test_success
    except Exception as e:
        logger.error(f"Ошибка при настройке VK API: {e}")
        return False

def update_memes():
    """Функция для периодического обновления мемов"""
    global update_thread_running
    global memes_collection
    
    try:
        # Проверяем возможность получения мемов из VK
        vk_available = try_fetch_memes_from_vk()
        
        if vk_available:
            # Импортируем VK-утилиты, так как знаем, что они доступны
            from vk_utils import VKMemesFetcher
            
            # VK API токен для доступа к мемам с публичных страниц
            vk_token = os.environ.get("VK_TOKEN", "")
            
            # Инициализация клиента VK
            vk_client = VKMemesFetcher(vk_token)
            
            update_thread_running = True
            logger.info("Запущен поток обновления мемов из VK")
            
            # Если у нас нет кэшированных мемов, инициализируем из статического списка
            if not memes_collection:
                init_default_memes()
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
        else:
            # VK недоступен, используем только встроенную коллекцию
            logger.info("VK API недоступен, используем только встроенную коллекцию мемов")
            
            # Если у нас нет кэшированных мемов, инициализируем из статического списка
            if not memes_collection:
                init_default_memes()
                save_memes_to_cache()
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
            
            # Проверяем доступность изображения перед добавлением
            try:
                import requests
                from io import BytesIO
                from PIL import Image
                
                # Проверяем URL с помощью HEAD запроса
                response = requests.head(image_url, timeout=5)
                if response.status_code != 200:
                    logger.warning(f"Ссылка на изображение недоступна: {image_url}, статус: {response.status_code}")
                    rejected_memes[meme_id] = new_meme
                    rejected_count += 1
                    logger.info(f"Отклонен мем {meme_id} из-за недоступного изображения (статус: {response.status_code})")
                    continue
                
                # Пытаемся получить первый кусок изображения для проверки
                response = requests.get(image_url, timeout=5, stream=True)
                if response.status_code == 200:
                    try:
                        # Проверяем, что это действительно изображение
                        img_data = BytesIO(response.content)
                        img = Image.open(img_data)
                        img.verify()  # Проверяем целостность изображения
                        
                        # Проверяем через улучшенный фильтр контента
                        if is_suitable_meme_advanced(new_meme):
                            memes_collection[meme_id] = new_meme
                            new_memes_count += 1
                            logger.info(f"Добавлен новый мем {meme_id}")
                        else:
                            rejected_memes[meme_id] = new_meme
                            rejected_count += 1
                            logger.info(f"Отклонен мем {meme_id} как неподходящий (реклама)")
                    except Exception as img_error:
                        logger.error(f"Ошибка при проверке изображения {image_url}: {img_error}")
                        rejected_memes[meme_id] = new_meme
                        rejected_count += 1
                        logger.info(f"Отклонен мем {meme_id} из-за проблем с форматом изображения")
                else:
                    logger.warning(f"Не удалось получить изображение по URL: {image_url}, статус: {response.status_code}")
                    rejected_memes[meme_id] = new_meme
                    rejected_count += 1
                    logger.info(f"Отклонен мем {meme_id} из-за невозможности загрузить изображение")
            except Exception as validation_error:
                logger.error(f"Ошибка при валидации изображения {image_url}: {validation_error}")
                # Если не смогли проверить изображение, все равно пробуем добавить мем,
                # но только если он прошел фильтр контента
                if is_suitable_meme_advanced(new_meme):
                    memes_collection[meme_id] = new_meme
                    new_memes_count += 1
                    logger.info(f"Добавлен новый мем {meme_id} (без валидации изображения)")
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
            "👋 Привет! Я бот для просмотра мемов без рекламы.\n\n"
            "Используем передовую технологию фильтрации рекламного контента. "
            "Все мемы тщательно проверяются системой фильтрации.\n\n"
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
    
    # Проверяем, есть ли мемы в коллекции
    if not memes_collection:
        logger.warning("Мемы отсутствуют в коллекции. Инициализация стандартного набора.")
        if not init_default_memes():
            # Если не удалось инициализировать, сообщаем пользователю
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="К сожалению, на данный момент нет доступных мемов. Попробуйте позже."
            )
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
    
    # Если у нас есть ID мема, но его нет в коллекции, возможно кэш был обновлен
    # В этом случае выбираем любой доступный мем
    if meme_id not in memes_collection:
        logger.warning(f"Выбранный мем {meme_id} не найден в коллекции, выбираем другой")
        if memes_collection:
            meme_id = random.choice(list(memes_collection.keys()))
        else:
            # Если коллекция пуста, сообщаем пользователю
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="К сожалению, на данный момент нет доступных мемов. Попробуйте позже."
            )
            return
    
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
            # Проверяем доступность изображения перед отправкой
            try:
                import requests
                from io import BytesIO
                from PIL import Image
                
                # Пытаемся получить изображение
                logger.info(f"Загрузка изображения по URL: {image_url}")
                response = requests.get(image_url, timeout=10, stream=True)
                
                if response.status_code == 200:
                    # Проверим, что контент действительно изображение
                    try:
                        # Читаем первые байты для проверки формата
                        img_data = BytesIO(response.content)
                        Image.open(img_data)
                        
                        # Если всё в порядке, отправляем изображение
                        message = await context.bot.send_photo(
                            chat_id=update.effective_chat.id,
                            photo=BytesIO(response.content),  # Отправляем как файл, а не URL
                            caption=text,
                            reply_markup=reply_markup
                        )
                        logger.info(f"Изображение успешно отправлено")
                    except Exception as img_error:
                        logger.error(f"Ошибка при обработке изображения: {img_error}")
                        raise
                else:
                    logger.warning(f"Не удалось получить изображение, статус: {response.status_code}")
                    raise Exception(f"Ошибка загрузки изображения, статус: {response.status_code}")
                    
            except Exception as img_fetch_error:
                logger.error(f"Не удалось загрузить изображение: {img_fetch_error}")
                # Пробуем отправить просто по URL без предварительной загрузки
                try:
                    message = await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=image_url,
                        caption=text,
                        reply_markup=reply_markup
                    )
                    logger.info(f"Изображение отправлено напрямую через URL")
                except Exception as direct_send_error:
                    logger.error(f"Не удалось отправить изображение напрямую: {direct_send_error}")
                    # Если не удалось отправить изображение, отправляем только текст
                    message = await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"⚠️ Не удалось загрузить изображение\n\n{text}",
                        reply_markup=reply_markup
                    )
                    logger.info(f"Отправлен только текст мема вместо изображения")
        else:
            # Если у мема нет изображения, отправляем только текст
            message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                reply_markup=reply_markup
            )
            logger.info(f"Отправлен текстовый мем (без изображения)")
        
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
                # Проверяем, существует ли мем в коллекции
                if meme_id in memes_collection:
                    # Получаем данные мема для обновления предпочтений
                    meme = memes_collection[meme_id]
                    update_user_preferences(user_id, meme, rating)
                else:
                    logger.warning(f"Мем {meme_id} не найден в коллекции при обновлении предпочтений")
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
    
    # Получаем статистику пользователя
    viewed_count = len(user_states[user_id].get("viewed_memes", []))
    ratings = user_states[user_id].get("ratings", {})
    positive_ratings = sum(1 for r in ratings.values() if r > 0)
    negative_ratings = sum(1 for r in ratings.values() if r < 0)
    
    # Получаем рекомендации и предпочтения
    try:
        # Получаем статистику предпочтений пользователя
        preferences_stats = get_user_preferences_stats(user_id)
        
        # Получаем анализ истории просмотров
        history_analysis = analyze_user_history(user_id, memes_collection)
        
        # Предпочтительные темы
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
        
        # Упрощенная статистика в случае ошибки
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
        # Перемещаем мем из основной коллекции в отклоненные
        rejected_memes[meme_id] = memes_collection.pop(meme_id)
        save_memes_to_cache()
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Спасибо! Мы отметили этот мем как рекламный и больше не будем его показывать."
        )
        
        # Отправляем новый мем
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
        # Получаем персонализированные рекомендации
        recommended_memes = recommend_memes(user_id, memes_collection, 1)
        
        if not recommended_memes:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="К сожалению, не удалось сформировать рекомендации. Попробуйте оценить больше мемов."
            )
            return
        
        # Берем первую рекомендацию
        meme_id = recommended_memes[0]
        
        # Проверяем, что мем существует в коллекции
        if meme_id not in memes_collection:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Произошла ошибка. Рекомендованный мем недоступен."
            )
            return
        
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
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🔍 Вот мем, который может вам понравиться:"
        )
        
        if image_url:
            try:
                import requests
                from io import BytesIO
                from PIL import Image
                
                # Пробуем сначала получить изображение и проверить его
                try:
                    logger.info(f"Загрузка рекомендованного изображения по URL: {image_url}")
                    response = requests.get(image_url, timeout=10, stream=True)
                    
                    if response.status_code == 200:
                        # Проверяем, что это действительно изображение
                        img_data = BytesIO(response.content)
                        Image.open(img_data)
                        
                        # Отправляем изображение как файл
                        await context.bot.send_photo(
                            chat_id=update.effective_chat.id,
                            photo=BytesIO(response.content),
                            caption=text,
                            reply_markup=reply_markup
                        )
                        logger.info("Рекомендованное изображение успешно отправлено")
                    else:
                        raise Exception(f"Статус: {response.status_code}")
                except Exception as img_error:
                    logger.error(f"Ошибка при обработке рекомендованного изображения: {img_error}")
                    # Пробуем отправить напрямую по URL
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=image_url,
                        caption=text,
                        reply_markup=reply_markup
                    )
                    logger.info("Рекомендованное изображение отправлено напрямую через URL")
            except Exception as send_error:
                logger.error(f"Не удалось отправить рекомендованное изображение: {send_error}")
                # В случае неудачи отправляем только текст
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"⚠️ Не удалось загрузить изображение\n\n{text}",
                    reply_markup=reply_markup
                )
        else:
            # Если у мема нет изображения
            await context.bot.send_message(
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
            logger.error(f"Ошибка при записи просмотра рекомендованного мема в аналитику: {e}")
        
    except Exception as e:
        logger.error(f"Ошибка при получении рекомендаций: {e}")
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Произошла ошибка при формировании рекомендаций. Пожалуйста, попробуйте позже."
        )

def main():
    """Основная функция для запуска бота"""
    # Регистрируем обработчик сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("=== ЗАПУСК TELEGRAM БОТА НА RAILWAY ===")
    
    # Загружаем аналитические данные
    try:
        # Загружаем данные для аналитики
        meme_analytics._load_analytics_files()
        logger.info("Аналитические данные успешно загружены")
    except Exception as e:
        logger.error(f"Ошибка при загрузке аналитических данных: {e}")
    
    # Загружаем кэш мемов
    cache_loaded = load_memes_from_cache()
    
    # Если кэш не загружен, инициализируем из встроенной коллекции
    if not cache_loaded or not memes_collection:
        logger.info("Кэш мемов не загружен, инициализируем из встроенной коллекции")
        init_default_memes()
    
    logger.info(f"Доступно {len(memes_collection)} мемов после агрессивной фильтрации рекламы")
    logger.info(f"Отклонено {len(rejected_memes)} мемов как рекламные")
    
    # Получаем токен бота из переменных окружения
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
        sys.exit(1)
    
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
    
    # Проверяем, не запущен ли уже бот через файл блокировки
    LOCK_FILE = ".telegram_bot_railway_lock"
    
    # Функция для проверки и создания блокировочного файла
    def check_and_create_lock():
        if os.path.exists(LOCK_FILE):
            try:
                # Проверяем время создания файла
                file_time = os.path.getmtime(LOCK_FILE)
                current_time = time.time()
                
                # Если файл создан недавно (менее 2 минут назад)
                if current_time - file_time < 120:
                    try:
                        # Проверяем PID из файла
                        with open(LOCK_FILE, 'r') as f:
                            pid_str = f.read().strip()
                            if pid_str:
                                try:
                                    pid = int(pid_str)
                                    # Проверяем, существует ли процесс с таким PID
                                    try:
                                        os.kill(pid, 0)  # Сигнал 0 только проверяет существование процесса
                                        logger.warning(f"Бот уже запущен с PID {pid}. Останавливаем текущий запуск.")
                                        return False
                                    except OSError:
                                        # Процесс не существует, можно удалить старый файл
                                        logger.warning(f"Найден lock от несуществующего процесса {pid}. Удаляем.")
                                        os.remove(LOCK_FILE)
                                except ValueError:
                                    # Неверный формат PID в файле
                                    logger.warning("Неверный формат PID в lock-файле. Удаляем.")
                                    os.remove(LOCK_FILE)
                    except Exception as e:
                        logger.error(f"Ошибка при проверке PID в lock-файле: {e}")
                        os.remove(LOCK_FILE)
                else:
                    # Файл устарел, удаляем его
                    logger.warning(f"Найден устаревший lock-файл (возраст: {current_time - file_time:.1f}с). Удаляем.")
                    os.remove(LOCK_FILE)
            except Exception as e:
                logger.error(f"Ошибка при проверке lock-файла: {e}")
                try:
                    os.remove(LOCK_FILE)
                except:
                    pass
        
        # Создаем файл блокировки с текущим PID
        try:
            with open(LOCK_FILE, 'w') as f:
                f.write(str(os.getpid()))
            logger.info(f"Создан lock-файл {LOCK_FILE} с PID {os.getpid()}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при создании lock-файла: {e}")
            return False
    
    # Функция для удаления блокировочного файла при завершении
    def cleanup_lock():
        try:
            if os.path.exists(LOCK_FILE):
                os.remove(LOCK_FILE)
                logger.info(f"Lock-файл {LOCK_FILE} удален")
        except Exception as e:
            logger.error(f"Ошибка при удалении lock-файла: {e}")
    
    # Проверяем и создаем блокировку
    if not check_and_create_lock():
        # Блокировка не удалась, бот уже запущен
        logger.warning("Не удалось создать lock-файл или бот уже запущен. Выход.")
        sys.exit(0)
        
    # Устанавливаем параметры для предотвращения конфликтов
    polling_kwargs = {
        "allowed_updates": Update.ALL_TYPES,
        "drop_pending_updates": True,
        "close_loop": False,
        "connect_timeout": 30,
        "read_timeout": 30
    }
    
    # Регистрируем удаление блокировки при завершении
    original_sigterm_handler = signal.getsignal(signal.SIGTERM)
    original_sigint_handler = signal.getsignal(signal.SIGINT)
    
    def cleanup_and_forward(sig, frame):
        cleanup_lock()
        # Вызываем оригинальный обработчик, если это функция
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
        # Запускаем бота с перехватом возможной ошибки конфликта
        logger.info("Запуск бота в режиме polling...")
        # Используем параметры для предотвращения конфликтов при получении обновлений
        application.run_polling(**polling_kwargs)
    except telegram.error.Conflict as conflict_error:
        logger.error(f"Обнаружен конфликт Telegram API: {conflict_error}. Другой экземпляр бота уже запущен.")
        cleanup_lock()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        cleanup_lock()
        sys.exit(1)
    finally:
        # В любом случае удаляем файл блокировки
        cleanup_lock()

if __name__ == "__main__":
    main()
