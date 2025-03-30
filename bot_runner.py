#!/usr/bin/env python3
"""
Прямой запуск бота для workflow run_bot.
"""
import os
import sys
import logging
import traceback

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   stream=sys.stdout)

logger = logging.getLogger(__name__)
logger.info("=== Запуск бота через bot_runner.py ===")

def main():
    """Основная функция для запуска бота."""
    # Проверяем наличие TELEGRAM_BOT_TOKEN
    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения!")
        sys.exit(1)
    
    # Импортируем и запускаем бота напрямую
    try:
        from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
        
        # Импортируем данные для мемов
        from meme_data import MEMES, is_suitable_meme, MEME_SOURCES
        
        # Если импорт прошел успешно, инициализируем бота
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        
        # Словарь для хранения информации о пользователях
        user_states = {}
        
        # Определяем обработчики команд
        async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Обработчик команды /start."""
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
        
        # Функция для отправки случайного мема
        async def send_random_meme(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Отправляет случайный мем пользователю."""
            if update.effective_user is None or update.effective_chat is None:
                logger.error("Не удалось получить информацию о пользователе или чате!")
                return
                
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
            
            # Для простоты тестирования просто отправим фиксированный текст
            keyboard = [
                [
                    InlineKeyboardButton("👍", callback_data="like_1"),
                    InlineKeyboardButton("👎", callback_data="dislike_1")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=chat_id,
                text="Тестовый мем для проверки работы бота",
                reply_markup=reply_markup
            )
        
        # Обработчик нажатий на кнопки
        async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Обработчик нажатий на кнопки рейтинга."""
            if update.callback_query is None:
                logger.error("callback_query is None")
                return
                
            query = update.callback_query
            await query.answer()
            
            if update.effective_user is None:
                logger.error("effective_user is None")
                return
                
            user_id = update.effective_user.id
            
            # Получаем информацию о кнопке
            data = query.data
            if data is None or "_" not in data:
                logger.error(f"Некорректный формат callback_data: {data}")
                return
                
            action, meme_id = data.split("_", 1)
            
            logger.info(f"Пользователь {user_id} поставил {'лайк' if action == 'like' else 'дизлайк'}")
            
            # Отправляем следующий мем
            await send_random_meme(update, context)
        
        # Запускаем бота
        logger.info("Инициализация бота...")
        application = Application.builder().token(token).build()
        
        # Регистрируем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_callback))
        
        # Запускаем бота
        logger.info("Бот запущен и готов к работе.")
        application.run_polling()
        
    except ImportError as e:
        logger.error(f"Ошибка импорта библиотек: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()