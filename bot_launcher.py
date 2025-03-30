#!/usr/bin/env python
"""
Специальный лаунчер для запуска телеграм-бота отдельно от веб-приложения.
Используется только для workflow run_bot.
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

# Импортируем данные для мемов
from meme_data import MEMES

# Словарь для хранения информации о пользователях
user_states = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start. Отправляет первый мем пользователю."""
    user_id = update.effective_user.id
    
    # Инициализируем состояние пользователя, если это первый запуск
    if user_id not in user_states:
        user_states[user_id] = {
            "seen_memes": set(),
            "ratings": {}  # Словарь для хранения оценок мемов
        }
    
    await send_random_meme(update, context)

async def send_random_meme(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет случайный мем пользователю."""
    user_id = update.effective_user.id
    user_data = user_states.get(user_id, {"seen_memes": set()})
    
    # Получаем список мемов, которые пользователь еще не видел
    unseen_memes = [meme_id for meme_id in MEMES.keys() if meme_id not in user_data["seen_memes"]]
    
    # Если пользователь уже видел все мемы, сбрасываем историю
    if not unseen_memes:
        user_data["seen_memes"] = set()
        unseen_memes = list(MEMES.keys())
    
    # Выбираем случайный мем
    meme_id = random.choice(unseen_memes)
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
    """Основная функция для запуска бота"""
    # Получаем токен из переменных окружения
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения!")
        sys.exit(1)
    
    try:
        # Инициализируем бота
        application = Application.builder().token(token).build()
        
        # Регистрируем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_callback))
        
        # Запускаем бота
        logger.info("Telegram-бот запускается...")
        application.run_polling()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    logger.info("ЗАПУСК БОТ-ЛАУНЧЕРА")
    main()