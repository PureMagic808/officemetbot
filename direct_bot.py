#!/usr/bin/env python3
"""
Телеграм-бот для отправки мемов.
Этот файл можно запустить напрямую, независимо от workflow.
"""
import os
import sys
import logging
import traceback
import signal
import random

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
    # Проверяем наличие TELEGRAM_BOT_TOKEN
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения!")
        return
    
    # Импортируем библиотеки для бота
    try:
        from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
        
        # Импортируем данные для мемов, если есть
        try:
            from meme_data import MEMES, is_suitable_meme
        except ImportError:
            # Если модуль meme_data.py не найден, создаем тестовые данные
            logger.warning("Модуль meme_data.py не найден, используем тестовые данные")
            MEMES = {
                "test_meme_1": {
                    "title": "Тестовый мем 1",
                    "text": "Это тестовый мем для проверки работы бота"
                },
                "test_meme_2": {
                    "title": "Тестовый мем 2",
                    "text": "Еще один тестовый мем для проверки работы бота"
                }
            }
            
            def is_suitable_meme(meme):
                return True
        
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
            
            # Выбираем случайный мем
            meme_ids = list(MEMES.keys())
            if not meme_ids:
                logger.error("Нет доступных мемов!")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="К сожалению, мемы временно недоступны. Попробуйте позже."
                )
                return
            
            # Выбираем случайный мем из списка
            meme_id = random.choice(meme_ids)
            meme = MEMES.get(meme_id, {"text": "Тестовый мем", "title": "Тест"})
            
            logger.info(f"Отправляем мем {meme_id} пользователю {user_id}")
            
            # Готовим кнопки для оценки мема
            keyboard = [
                [
                    InlineKeyboardButton("👍", callback_data=f"like_{meme_id}"),
                    InlineKeyboardButton("👎", callback_data=f"dislike_{meme_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем мем
            meme_text = meme.get("text", "Тестовый мем")
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=meme_text,
                reply_markup=reply_markup
            )
            
            # Обновляем список просмотренных мемов
            if user_id in user_states and "seen_memes" in user_states[user_id]:
                user_states[user_id]["seen_memes"].add(meme_id)
        
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