#!/usr/bin/env python3
"""
Скрипт для прямого запуска Telegram-бота через workflow run_bot.
Этот скрипт запускает бота, минуя Flask-приложение.
"""
import sys
import os
import subprocess
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Ограничиваем переменные окружения для предотвращения конфликтов с Flask
logger.info("=== ЗАПУСК TELEGRAM-БОТА ЧЕРЕЗ WORKFLOW ===")

try:
    # Проверяем наличие токена бота
    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения!")
        logger.error("Бот не может быть запущен без токена.")
        sys.exit(1)
    
    # Используем прямой файл запуска бота, который не зависит от Flask
    bot_script = "direct_workflow_bot.py"
    
    # Делаем файл исполняемым
    os.chmod(bot_script, 0o755)
    
    # Запускаем бота напрямую
    logger.info(f"Запуск Telegram-бота через {bot_script}...")
    subprocess.run([sys.executable, bot_script])
    
except Exception as e:
    logger.error(f"Ошибка при запуске бота: {e}")
    import traceback
    logger.error(traceback.format_exc())
    sys.exit(1)