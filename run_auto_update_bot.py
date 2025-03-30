#!/usr/bin/env python3
"""
Скрипт для запуска бота с автоматическим обновлением мемов через workflow run_bot.
"""
import logging
import os
import sys

# Настройка логирования
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stdout)
logger = logging.getLogger(__name__)

def main():
    """Основная функция для запуска бота с автообновлением"""
    logger.info("=== ЗАПУСК БОТА С АВТООБНОВЛЕНИЕМ ЧЕРЕЗ WORKFLOW ===")
    
    # Проверка наличия токена
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("Не указан токен бота в переменной окружения TELEGRAM_BOT_TOKEN")
        sys.exit(1)
    
    try:
        # Импортируем и запускаем бот с автообновлением
        from auto_update_bot import main as run_bot
        run_bot()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()