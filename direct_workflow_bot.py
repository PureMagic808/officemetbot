#!/usr/bin/env python3
"""
Прямой запуск Telegram-бота для workflow run_bot.
Запускается напрямую из workflow, минуя main.py.
"""
import os
import sys
import signal
import logging
import json
import random
import time

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Обработчик сигналов для корректного завершения
def signal_handler(sig, frame):
    logger.info('Получен сигнал завершения, выходим...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Проверяем наличие токена
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("Токен бота не найден! Установите переменную окружения TELEGRAM_BOT_TOKEN")
    sys.exit(1)

# Импортируем Telegram библиотеки
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application, CommandHandler, ContextTypes,
        CallbackQueryHandler, CallbackContext
    )
except ImportError:
    logger.error("Ошибка импорта библиотек telegram. Установите python-telegram-bot!")
    sys.exit(1)

# Импортируем данные о мемах и фильтр контента
try:
    from meme_data import MEMES
    from content_filter import is_suitable_meme, BLOCKED_URL_PATTERNS
except ImportError as e:
    logger.error(f"Не удалось импортировать нужные модули: {e}")
    sys.exit(1)

# Глобальное состояние бота для хранения данных пользователей
user_states = {}

# Пытаемся загрузить предыдущее состояние бота
try:
    if os.path.exists('bot_state.json'):
        with open('bot_state.json', 'r') as f:
            loaded_data = json.load(f)
            # Преобразуем строковые ключи в числовые и "sent_memes" в множества
            for user_id_str, user_data in loaded_data.items():
                user_id = int(user_id_str)
                if "sent_memes" in user_data and isinstance(user_data["sent_memes"], list):
                    user_data["sent_memes"] = set(user_data["sent_memes"])
                user_states[user_id] = user_data
        logger.info(f"Загружено состояние для {len(user_states)} пользователей")
except Exception as e:
    logger.warning(f"Не удалось загрузить предыдущее состояние бота: {e}")

# Подготавливаем отфильтрованные мемы (без рекламы, спорта и т.д.)
logger.info("Фильтрация мемов...")
filtered_memes = {k: v for k, v in MEMES.items() if is_suitable_meme(v)}

if not filtered_memes:
    logger.warning("После фильтрации не осталось мемов! Используем весь набор")
    filtered_memes = MEMES

logger.info(f"Доступно {len(filtered_memes)} мемов из {len(MEMES)} после фильтрации")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start. Отправляет первый мем пользователю."""
    user_id = update.effective_user.id
    username = update.effective_user.username or 'Пользователь'
    logger.info(f"Пользователь {username} (ID: {user_id}) запустил бота")
    
    # Инициализируем состояние пользователя, если его нет
    if user_id not in user_states:
        user_states[user_id] = {
            "ratings": {},
            "sent_memes": set(),
            "current_meme_id": None,
        }
    
    # Приветствуем пользователя
    await update.message.reply_text(
        f"Привет, {username}! Я бот для оценки мемов.\n"
        "Я буду отправлять тебе мемы, а ты можешь оценивать их 👍 или 👎\n"
        "Сейчас я отправлю тебе первый мем:"
    )
    
    # Отправляем первый мем
    await send_random_meme(update, context)

async def send_random_meme(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет случайный мем пользователю."""
    user_id = update.effective_user.id
    
    # Инициализируем состояние пользователя, если его нет
    if user_id not in user_states:
        user_states[user_id] = {
            "ratings": {},
            "sent_memes": set(),
            "current_meme_id": None,
        }
    
    # Получаем список уже отправленных мемов для этого пользователя
    sent_memes = user_states[user_id].get("sent_memes", set())
    
    # Получаем список идентификаторов всех отфильтрованных мемов
    meme_ids = list(filtered_memes.keys())
    
    # Если пользователь уже видел 70% всех мемов, очищаем историю частично
    if len(sent_memes) >= int(len(meme_ids) * 0.7):
        logger.info(f"Пользователь {user_id} уже видел много мемов, сбрасываем часть истории")
        # Сохраняем только 5 последних мемов для непрерывности и избегания повторений
        sent_memes_list = list(sent_memes)
        sent_memes = set(sent_memes_list[-5:])
        user_states[user_id]["sent_memes"] = sent_memes
    
    # Выбираем мемы, которые еще не были отправлены недавно
    available_memes = [m_id for m_id in meme_ids if m_id not in sent_memes]
    
    # Если все мемы уже были показаны, выбираем случайный из всех
    if not available_memes:
        logger.info(f"Пользователь {user_id} уже видел все доступные мемы, выбираем случайный")
        meme_id = random.choice(meme_ids)
    else:
        # Выбираем случайный мем из непросмотренных
        meme_id = random.choice(available_memes)
    
    # Получаем мем из коллекции отфильтрованных мемов
    meme = filtered_memes.get(meme_id)
    
    # Сохраняем информацию о текущем отправленном меме
    user_states[user_id]["current_meme_id"] = meme_id
    user_states[user_id].setdefault("sent_memes", set()).add(meme_id)
    
    # Создаем клавиатуру с кнопками для оценки
    keyboard = [
        [
            InlineKeyboardButton("👍", callback_data="rating:1"),
            InlineKeyboardButton("👎", callback_data="rating:-1"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем мем с изображением, если оно есть
    if "image_url" in meme and meme["image_url"]:
        try:
            # Отправляем изображение с подписью
            await update.effective_chat.send_photo(
                photo=meme["image_url"],
                caption=meme.get("text", ""),
                reply_markup=reply_markup
            )
            logger.info(f"Отправлен мем с изображением {meme_id} пользователю {user_id}")
        except Exception as e:
            logger.error(f"Ошибка при отправке изображения: {e}")
            # В случае ошибки отправляем только текст
            await update.effective_chat.send_message(
                text=f"{meme.get('text', 'Мем без текста')}",
                reply_markup=reply_markup
            )
            logger.info(f"Отправлен текстовый мем {meme_id} после ошибки изображения")
    else:
        # Отправляем только текст, если изображения нет
        await update.effective_chat.send_message(
            text=meme.get("text", "Мем без текста"),
            reply_markup=reply_markup
        )
        logger.info(f"Отправлен текстовый мем {meme_id} пользователю {user_id}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий на кнопки рейтинга."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data
    
    if callback_data.startswith("rating:"):
        rating = int(callback_data.split(":")[1])
        current_meme_id = user_states[user_id].get("current_meme_id")
        
        if current_meme_id:
            # Сохраняем оценку
            user_states[user_id].setdefault("ratings", {})[current_meme_id] = rating
            logger.info(f"Пользователь {user_id} оценил мем {current_meme_id} с рейтингом {rating}")
            
            # Убираем кнопки оценки
            await query.edit_message_reply_markup(reply_markup=None)
            
            # Сохраняем состояние бота
            try:
                # Преобразуем множества в списки для JSON
                json_data = {}
                for u_id, u_data in user_states.items():
                    json_data[str(u_id)] = u_data.copy()
                    if "sent_memes" in json_data[str(u_id)] and isinstance(json_data[str(u_id)]["sent_memes"], set):
                        json_data[str(u_id)]["sent_memes"] = list(json_data[str(u_id)]["sent_memes"])
                
                with open('bot_state.json', 'w') as f:
                    json.dump(json_data, f)
            except Exception as e:
                logger.warning(f"Не удалось сохранить состояние бота: {e}")
            
            # Отправляем сообщение в зависимости от оценки
            if rating > 0:
                await update.effective_chat.send_message("👍 Спасибо за положительную оценку! Вот следующий мем:")
            else:
                await update.effective_chat.send_message("👎 Понял, этот мем не понравился. Вот следующий:")
            
            # Отправляем следующий мем
            await send_random_meme(update, context)
        else:
            logger.warning(f"Не найден текущий мем для пользователя {user_id}")
            await update.effective_chat.send_message("Произошла ошибка. Попробуйте ввести /start для перезапуска.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help."""
    await update.message.reply_text(
        "Я бот для оценки мемов. Вот доступные команды:\n"
        "/start - Начать взаимодействие и получить первый мем\n"
        "/next - Получить следующий мем без оценки текущего\n"
        "/help - Показать это сообщение с помощью\n\n"
        "После получения мема вы можете оценить его кнопками 👍 или 👎"
    )

async def next_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /next для пропуска текущего мема."""
    await update.message.reply_text("Вот следующий мем:")
    await send_random_meme(update, context)

def main():
    """Основная функция для запуска бота."""
    try:
        logger.info("Инициализация приложения бота...")
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Регистрируем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("next", next_command))
        application.add_handler(CallbackQueryHandler(button_callback))
        
        # Запускаем бота в режиме polling
        logger.info("Запуск бота в режиме polling...")
        application.run_polling(poll_interval=1.0, timeout=30)
        
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    # Добавляем небольшую задержку для стабильности
    time.sleep(1)
    logger.info("=== ПРЯМОЙ ЗАПУСК TELEGRAM БОТА ===")
    main()