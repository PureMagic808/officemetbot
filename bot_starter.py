#!/usr/bin/env python3
"""
Специальный запускающий скрипт для Telegram-бота.
Этот файл выполняется через workflow run_bot.
"""
import os
import sys
import signal
import logging
import requests
from typing import Dict, Any, Set
import json
import random

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
except ImportError:
    logger.error("Не удалось импортировать нужные модули!")
    MEMES = {}
    BLOCKED_URL_PATTERNS = ["тренируйся", "фитнес", "nail"]
    def is_suitable_meme(meme):
        return True

# Глобальное состояние бота для хранения данных пользователей
user_states = {}

def main():
    """Основная функция для запуска бота."""
    # Получаем токен бота из переменных окружения
    BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    
    if not BOT_TOKEN:
        logger.error("Токен бота не найден! Установите переменную окружения TELEGRAM_BOT_TOKEN")
        sys.exit(1)
    
    logger.info("Инициализация бота...")
    
    try:
        # Создаем фильтр для мемов (исключаем рекламу и спорт)
        filtered_memes = {k: v for k, v in MEMES.items() if is_suitable_meme(v)}
        
        if not filtered_memes:
            logger.warning("Список мемов пуст после фильтрации! Проверьте meme_data.py")
            filtered_memes = MEMES
        
        logger.info(f"Загружено {len(filtered_memes)} мемов для отправки")
        
        # Создаем приложение Telegram бота
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Определяем обработчики команд и колбэков
        async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Обработчик команды /start. Отправляет первый мем пользователю."""
            user_id = update.effective_user.id
            logger.info(f"Пользователь {user_id} запустил бота")
            
            # Инициализируем состояние пользователя, если его нет
            if user_id not in user_states:
                user_states[user_id] = {
                    "ratings": {},
                    "sent_memes": set(),
                    "current_meme_id": None,
                }
            
            # Приветствуем пользователя
            await update.message.reply_text(
                "Привет! Я бот для оценки мемов.\n"
                "Я буду отправлять тебе мемы, а ты можешь оценивать их 👍 или 👎\n"
                "Сейчас я отправлю тебе первый мем:"
            )
            
            # Отправляем первый мем
            await send_random_meme(update, context)
        
        async def send_random_meme(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Отправляет случайный мем пользователю."""
            user_id = update.effective_user.id
            logger.info(f"Отправка случайного мема пользователю {user_id}")
            
            # Получаем список идентификаторов мемов, отфильтрованных по критериям
            meme_ids = list(filtered_memes.keys())
            
            # Если нет отфильтрованных мемов, логируем ошибку и используем все мемы
            if not meme_ids:
                logger.warning("Нет подходящих мемов после фильтрации! Используем оригинальный набор")
                meme_ids = list(MEMES.keys())
            
            # Получаем список уже отправленных мемов для этого пользователя
            if user_id not in user_states:
                user_states[user_id] = {
                    "ratings": {},
                    "sent_memes": set(),
                    "current_meme_id": None,
                }
            
            sent_memes = user_states[user_id].get("sent_memes", set())
            
            # Если пользователь уже видел 70% всех мемов, сбрасываем историю
            # Это обеспечивает постоянную ротацию мемов и их повторение через некоторое время
            if len(sent_memes) >= int(len(meme_ids) * 0.7):
                logger.info(f"Пользователь {user_id} уже видел много мемов, сбрасываем часть истории")
                # Оставляем только 5 последних мемов в истории, чтобы избежать повторений подряд
                if len(sent_memes) > 5:
                    # Конвертируем в список, берём последние 5 элементов, и обратно в set
                    sent_memes_list = list(sent_memes)
                    sent_memes = set(sent_memes_list[-5:])
                    user_states[user_id]["sent_memes"] = sent_memes
            
            # Выбираем мемы, которые еще не были отправлены недавно
            available_memes = [m_id for m_id in meme_ids if m_id not in sent_memes]
            
            # Если все мемы уже были показаны (маловероятно при текущей логике),
            # выбираем случайный из всех
            if not available_memes:
                logger.info(f"Пользователь {user_id} уже видел все доступные мемы недавно, выбираем случайный")
                meme_id = random.choice(meme_ids)
            else:
                # Выбираем случайный из непросмотренных
                meme_id = random.choice(available_memes)
            
            # Берем сам мем из коллекции
            meme = filtered_memes.get(meme_id)
            
            # Проверка на случай, если мем по какой-то причине не найден
            if not meme:
                logger.warning(f"Мем с ID {meme_id} не найден в отфильтрованных, берем из оригинального набора")
                meme = MEMES.get(meme_id, {"text": "Упс, этот мем потерялся!"})
            
            # Сохраняем текущий мем в состоянии пользователя
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
            
            # Пробуем отправить мем с картинкой, если есть URL изображения
            if "image_url" in meme and meme["image_url"]:
                try:
                    # Дополнительная проверка URL на рекламу и нежелательный контент
                    image_url = meme["image_url"]
                    # Используем расширенный список из модуля content_filter
                    if any(term in image_url.lower() for term in BLOCKED_URL_PATTERNS):
                        # Если URL содержит нежелательные слова, отправляем только текст
                        await update.effective_chat.send_message(
                            text=meme.get("text", "Мем без текста"),
                            reply_markup=reply_markup
                        )
                        logger.info(f"Отправлен текстовый мем {meme_id} пользователю {user_id} (URL был отфильтрован)")
                    else:
                        # Отправляем мем с картинкой и текстом
                        await update.effective_chat.send_photo(
                            photo=image_url,
                            caption=meme.get("text", ""),
                            reply_markup=reply_markup
                        )
                        logger.info(f"Отправлен мем с картинкой {meme_id} пользователю {user_id}")
                except Exception as e:
                    logger.error(f"Ошибка при отправке мема с картинкой: {e}")
                    # Если не удалось отправить картинку, отправляем только текст
                    await update.effective_chat.send_message(
                        text=f"{meme.get('text', 'Мем без текста')}",
                        reply_markup=reply_markup
                    )
                    logger.info(f"Отправлен текстовый мем {meme_id} пользователю {user_id} (после ошибки)")
            else:
                # Отправляем только текст, если нет URL изображения
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
                    # Сохраняем оценку пользователя
                    user_states[user_id].setdefault("ratings", {})[current_meme_id] = rating
                    logger.info(f"Пользователь {user_id} оценил мем {current_meme_id} с рейтингом {rating}")
                    
                    # Благодарим за оценку и сразу убираем кнопки оценки
                    await query.edit_message_reply_markup(reply_markup=None)
                    
                    # Сохраняем статистику в файл
                    try:
                        import json
                        with open('bot_state.json', 'w') as f:
                            json.dump(user_states, f)
                    except Exception as e:
                        logger.warning(f"Не удалось сохранить состояние бота: {e}")
                    
                    # Отправляем сообщение с благодарностью в зависимости от оценки
                    if rating > 0:
                        await update.effective_chat.send_message("👍 Спасибо за положительную оценку! Вот следующий мем:")
                    else:
                        await update.effective_chat.send_message("👎 Понял, этот мем не понравился. Вот следующий:")
                    
                    # Отправляем следующий мем
                    await send_random_meme(update, context)
                else:
                    logger.warning(f"Не найден текущий мем для пользователя {user_id}")
                    await update.effective_chat.send_message("Произошла ошибка. Попробуйте ввести /start для перезапуска.")
        
        # Регистрируем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_callback))
        
        # Запуск бота
        logger.info("Запуск бота в режиме polling...")
        application.run_polling(poll_interval=1.0, timeout=30)
        
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()