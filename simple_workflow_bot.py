#!/usr/bin/env python3
"""
Простой запуск Telegram-бота непосредственно для workflow run_bot.
Этот файл специально создан для запуска бота без конфликтов с другими скриптами.
"""
import logging
import os
import signal
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from meme_data import MEMES
from content_filter import is_suitable_meme

# Настройка логирования
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stdout)
logger = logging.getLogger(__name__)

# Словарь для хранения состояния пользователей
user_states = {}

# Кэш для хранения отфильтрованных мемов
filtered_memes = None

def signal_handler(sig, frame):
    """Обработчик сигнала для корректного завершения работы бота"""
    logger.info("Получен сигнал завершения. Завершаем работу бота...")
    sys.exit(0)

def main():
    """Основная функция для запуска бота."""
    # Регистрируем обработчик сигнала
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Получаем токен бота из переменных окружения
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("Ошибка: не указан токен бота в переменной окружения TELEGRAM_BOT_TOKEN")
        sys.exit(1)
    
    logger.info("=== ЗАПУСК TELEGRAM-БОТА ДЛЯ WORKFLOW ===")
    
    # Фильтруем мемы перед запуском, чтобы иметь кэш подходящих мемов
    global filtered_memes
    if filtered_memes is None:
        logger.info("Фильтрация мемов...")
        filtered_memes = {}
        filtered_count = 0
        
        for meme_id, meme_data in MEMES.items():
            if is_suitable_meme(meme_data):
                filtered_memes[meme_id] = meme_data
            else:
                filtered_count += 1
        
        logger.info(f"Доступно {len(filtered_memes)} мемов из {len(MEMES)} после фильтрации")
    
    # Создаем приложение бота
    logger.info("Инициализация приложения бота...")
    application = Application.builder().token(token).build()
    
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /start. Отправляет первый мем пользователю."""
        user = update.effective_user
        user_id = user.id
        username = user.username
        
        logger.info(f"Команда /start от пользователя {username} (ID: {user_id})")
        
        # Инициализируем состояние пользователя, если его еще нет
        if user_id not in user_states:
            user_states[user_id] = {
                "username": username,
                "current_meme": None,
                "viewed_memes": [],
                "ratings": {}
            }
        
        # Отправляем первый мем
        await send_random_meme(update, context)
    
    async def send_random_meme(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Отправляет случайный мем пользователю."""
        import random
        
        user = update.effective_user
        user_id = user.id
        
        # Получаем все доступные мемы, которые пользователь еще не видел
        if user_id in user_states:
            viewed_memes = user_states[user_id].get("viewed_memes", [])
            
            # Проверка, что filtered_memes не None
            if filtered_memes is None:
                logger.error("Критическая ошибка: filtered_memes равен None")
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Произошла ошибка при загрузке мемов. Пожалуйста, попробуйте позже."
                )
                return
                
            available_memes = [meme_id for meme_id in filtered_memes if meme_id not in viewed_memes]
            
            # Если все мемы просмотрены, начинаем сначала
            if not available_memes:
                logger.info(f"Пользователь {user_id} просмотрел все мемы, сбрасываем историю")
                user_states[user_id]["viewed_memes"] = []
                available_memes = list(filtered_memes.keys())
            
            # Выбираем случайный мем
            meme_id = random.choice(available_memes)
            meme = filtered_memes[meme_id]
            
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
        else:
            # Если состояние пользователя не найдено (это не должно происходить)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Произошла ошибка. Пожалуйста, используйте /start для начала."
            )
    
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
                    meme = filtered_memes.get(meme_id, MEMES.get(meme_id))
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
                "/help - Показать эту справку\n\n"
                "Просто нажимайте 👍 или 👎, чтобы оценить мем, и я автоматически отправлю следующий."
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
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("next", next_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Запускаем бота
    logger.info("Запуск бота в режиме polling...")
    application.run_polling()

if __name__ == "__main__":
    main()