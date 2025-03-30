
#!/usr/bin/env python
import os
import sys
import logging
import random

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from vk_utils import VKMemesFetcher

# Список администраторов (их Telegram ID)
ADMIN_IDS = [
    "imksm_d",  # Первый админ
    "@imksm_d"  # Второй админ (с @ если это username)
]

def is_admin(user_id_or_username):
    """Проверяет, является ли пользователь администратором"""
    return str(user_id_or_username) in ADMIN_IDS or f"@{user_id_or_username}" in ADMIN_IDS

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   stream=sys.stdout)

logger = logging.getLogger(__name__)

# VK группы с мемами (ID групп)
MEME_GROUPS = [
    169229890,  # MDK
    460389,  # Смешные картинки
    217424576  # Новый паблик
]

# Инициализация VK API
vk_fetcher = VKMemesFetcher(os.environ.get("VK_TOKEN"))

# Словарь для хранения информации о пользователях
user_states = {}

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /admin"""
    user = update.effective_user
    if not is_admin(user.username) and not is_admin(user.id):
        await update.message.reply_text("У вас нет прав администратора.")
        return
        
    await update.message.reply_text(
        "Панель администратора:\n"
        "Текущие администраторы: " + ", ".join(ADMIN_IDS)
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "Anonymous"
    
    logger.info(f"Пользователь {username} (ID: {user_id}) запустил бота")
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Привет! Хочешь повеселиться? \nЖми /start и я отправлю тебе мем"
    )
    
    await send_random_meme(update, context)

async def send_random_meme(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет случайный мем из ВК"""
    image_url, caption = vk_fetcher.get_random_meme(MEME_GROUPS)
    
    if not image_url:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Извините, не удалось загрузить мем. Попробуйте позже."
        )
        return

    keyboard = [[
        InlineKeyboardButton("👍", callback_data="like"),
        InlineKeyboardButton("👎", callback_data="dislike"),
        InlineKeyboardButton("Следующий ➡️", callback_data="next")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=image_url,
        caption=caption[:1024] if caption else None,
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "next":
        await send_random_meme(update, context)
    else:
        # Обработка лайка/дизлайка
        reaction = "👍" if query.data == "like" else "👎"
        
        if query.data == "dislike":
            image_url = None
            # Получаем URL картинки из предыдущего сообщения
            if update.callback_query.message.photo:
                image_url = update.callback_query.message.photo[-1].file_id
            
            if image_url:
                if image_url not in vk_fetcher.meme_dislikes:
                    vk_fetcher.meme_dislikes[image_url] = 0
                vk_fetcher.meme_dislikes[image_url] += 1
                
                # Если мем набрал много дизлайков, добавляем его в черный список
                if vk_fetcher.meme_dislikes[image_url] >= vk_fetcher.max_dislikes:
                    vk_fetcher.sent_memes.add(image_url)
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Спасибо за оценку {reaction}! Вот следующий мем:"
        )
        await send_random_meme(update, context)

def run_bot():
    """Запускает бота"""
    logger.info("Запуск Telegram-бота...")

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения!")
        return False

    try:
        application = Application.builder().token(token).build()

        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("admin", admin_command))
        application.add_handler(CallbackQueryHandler(button_callback))

        logger.info("Telegram-бот запущен!")
        application.run_polling()
        return True

    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    run_bot()
