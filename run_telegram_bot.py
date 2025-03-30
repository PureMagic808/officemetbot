"""
Специальный скрипт для запуска только Telegram-бота без веб-интерфейса.
Этот скрипт предназначен для использования в workflow run_bot.
"""
import os
import sys
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   stream=sys.stdout)

logger = logging.getLogger(__name__)

logger.info("Запуск Telegram-бота через run_telegram_bot.py...")

# Проверяем наличие токена
token = os.environ.get("TELEGRAM_BOT_TOKEN")
if not token:
    logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения!")
    logger.error("Пожалуйста, добавьте переменную окружения TELEGRAM_BOT_TOKEN с токеном вашего бота")
    sys.exit(1)

try:
    # Запускаем telebot.py напрямую
    logger.info("Запускаем telebot.py...")
    import telebot
    telebot.main()
except Exception as e:
    logger.error(f"Ошибка при запуске бота: {e}")
    import traceback
    logger.error(traceback.format_exc())