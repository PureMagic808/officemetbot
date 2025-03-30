#!/usr/bin/env python3
"""
Специальный файл для запуска ТОЛЬКО бота без веб-интерфейса.
Этот файл должен запускаться из workflow run_bot.
"""
import os
import sys
import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stdout)

logger = logging.getLogger(__name__)
logger.info("Запуск ТОЛЬКО Telegram бота через bot_only.py...")

# Импортируем данные для мемов и функцию фильтрации
from meme_data import MEMES, is_suitable_meme, MEME_SOURCES

# Проверяем наличие токена
token = os.environ.get("TELEGRAM_BOT_TOKEN")
if not token:
    logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения!")
    logger.error("Пожалуйста, добавьте переменную окружения TELEGRAM_BOT_TOKEN с токеном вашего бота")
    sys.exit(1)

# Словарь для хранения информации о пользователях
user_states = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start. Отправляет первый мем пользователю."""
    user_id = update.effective_user.id
    username = update.effective_user.username or "Anonymous"
    
    logger.info(f"Пользователь {username} (ID: {user_id}) запустил бота")
    
    # Приветственное сообщение
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Привет! Я бот Мемолюб! Я буду показывать тебе смешные мемы, а ты их оценивай. Вот первый мем:"
    )
    
    # Инициализируем состояние пользователя, если это первый запуск
    if user_id not in user_states:
        user_states[user_id] = {
            "seen_memes": set(),
            "ratings": {}  # Словарь для хранения оценок мемов
        }
    
    # Отправляем первый мем
    await send_random_meme(update, context)

async def send_random_meme(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет случайный мем пользователю."""
    user_id = update.effective_user.id
    user_data = user_states.get(user_id, {"seen_memes": set(), "ratings": {}})
    
    # Получаем список мемов, которые пользователь еще не видел
    unseen_memes = [meme_id for meme_id in MEMES.keys() if meme_id not in user_data["seen_memes"]]
    
    # Если пользователь уже видел все мемы, сбрасываем историю
    if not unseen_memes:
        user_data["seen_memes"] = set()
        unseen_memes = list(MEMES.keys())
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Ты просмотрел все мемы! Начинаем показывать сначала."
        )
    
    # Выбираем случайный мем, убедившись, что он подходит (не реклама, не спорт)
    suitable_meme_found = False
    attempts = 0
    max_attempts = 5  # Максимальное количество попыток найти подходящий мем
    
    while not suitable_meme_found and attempts < max_attempts and unseen_memes:
        # Выбираем случайный мем
        meme_id = random.choice(unseen_memes)
        meme = MEMES[meme_id]
        
        # Проверяем, является ли мем подходящим (не реклама, не спорт и т.д.)
        if is_suitable_meme(meme):
            suitable_meme_found = True
            logger.info(f"Найден подходящий мем ID: {meme_id}")
        else:
            # Если мем не подходит, исключаем его из списка и пробуем снова
            unseen_memes.remove(meme_id)
            user_data["seen_memes"].add(meme_id)  # Помечаем как просмотренный, чтобы больше не показывать
            logger.info(f"Мем ID {meme_id} отфильтрован как неподходящий (реклама/спорт)")
            attempts += 1
    
    # Если не удалось найти подходящий мем после нескольких попыток, берем любой
    if not suitable_meme_found:
        logger.warning("Не удалось найти подходящий мем, показываем любой доступный")
        if unseen_memes:
            meme_id = random.choice(unseen_memes)
            meme = MEMES[meme_id]
        else:
            # Если все мемы просмотрены, берем любой
            meme_id = random.choice(list(MEMES.keys()))
            meme = MEMES[meme_id]
    
    # Добавляем мем в список просмотренных
    user_data["seen_memes"].add(meme_id)
    
    # Создаем кнопки для оценки
    keyboard = [
        [
            InlineKeyboardButton("👍", callback_data=f"like_{meme_id}"),
            InlineKeyboardButton("👎", callback_data=f"dislike_{meme_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем мем
    # Определяем, какой тип мема отправить (текст или изображение)
    if "image_url" in meme:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=meme["image_url"],
            caption=meme.get("caption", ""),
            reply_markup=reply_markup
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=meme["text"],
            reply_markup=reply_markup
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий на кнопки рейтинга."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Получаем информацию о кнопке
    data = query.data
    action, meme_id = data.split("_", 1)
    meme_id = int(meme_id)
    
    # Обновляем рейтинги пользователя
    if user_id in user_states:
        if action == "like":
            user_states[user_id]["ratings"][meme_id] = 1
            logger.info(f"Пользователь {user_id} поставил лайк мему {meme_id}")
        else:
            user_states[user_id]["ratings"][meme_id] = -1
            logger.info(f"Пользователь {user_id} поставил дизлайк мему {meme_id}")
    
    # Отправляем следующий мем
    await send_random_meme(update, context)

def main():
    """Основная функция запуска бота."""
    logger.info("Запуск Telegram-бота через bot_only.py...")
    
    try:
        # Инициализируем бота
        application = Application.builder().token(token).build()
        
        # Регистрируем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_callback))
        
        # Запускаем бота
        logger.info("Telegram-бот запущен и ожидает сообщений...")
        application.run_polling()
        return True
    
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    # Запускаем бота
    main()