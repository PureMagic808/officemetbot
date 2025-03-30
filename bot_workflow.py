#!/usr/bin/env python3
"""
Прямой запуск бота через workflow run_bot.
Этот файл выполняется только для workflow run_bot.
"""
import os
import sys
import logging
import traceback
import signal

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stdout)

logger = logging.getLogger(__name__)

def signal_handler(sig, frame):
    logger.info("Получен сигнал остановки, завершаем работу бота")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def main():
    """Основная функция для запуска бота."""
    # Проверяем, запущены ли мы из workflow run_bot
    workflow_info = os.environ.get("REPLIT_WORKFLOW", "")
    logger.info(f"REPLIT_WORKFLOW: {workflow_info}")
    
    if workflow_info != "run_bot":
        logger.warning("Этот скрипт должен запускаться только из workflow run_bot")
        return
        
    # Проверяем наличие TELEGRAM_BOT_TOKEN
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения!")
        return
    
    # Импортируем библиотеки для бота
    try:
        from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
        
        # Импортируем данные для мемов
        from meme_data import MEMES, is_suitable_meme
        
        # Готовим словарь для хранения состояния пользователей
        user_states = {}
        
        # Обработчик команды /start
        async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Обработчик команды /start. Отправляет первый мем пользователю."""
            if update.effective_user is None:
                logger.error("effective_user is None")
                return
                
            user_id = update.effective_user.id
            username = update.effective_user.username or "Анонимный пользователь"
            
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
            
            # Добавим фиксированный тестовый мем для проверки работы бота
            meme_id = "test_meme_1"
            
            # Готовим кнопки для оценки мема
            keyboard = [
                [
                    InlineKeyboardButton("👍", callback_data=f"like_{meme_id}"),
                    InlineKeyboardButton("👎", callback_data=f"dislike_{meme_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем мем
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
            
            # Сохраняем оценку пользователя
            if user_id in user_states:
                if "ratings" not in user_states[user_id]:
                    user_states[user_id]["ratings"] = {}
                
                # Устанавливаем оценку: 1 для лайка, -1 для дизлайка
                user_states[user_id]["ratings"][meme_id] = 1 if action == "like" else -1
                
                logger.info(f"Пользователь {user_id} поставил {'лайк' if action == 'like' else 'дизлайк'} для мема {meme_id}")
            
            # Отправляем следующий мем
            await send_random_meme(update, context)
        
        # Запускаем бота
        logger.info(f"Инициализация бота...")
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
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()