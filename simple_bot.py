#!/usr/bin/env python3
"""
Простейший бот-лаунчер для проверки workflow.
"""
import os
import sys
import logging
import time

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   stream=sys.stdout)

logger = logging.getLogger(__name__)

def main():
    """Основная функция для запуска бота."""
    logger.info("=== ЗАПУСК САМОГО ПРОСТОГО БОТА ===")
    logger.info(f"REPLIT_WORKFLOW: {os.environ.get('REPLIT_WORKFLOW', '')}")
    
    # Проверяем наличие TELEGRAM_BOT_TOKEN
    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения!")
        return
    
    # В этом скрипте не делаем ничего сложного, просто логируемся
    logger.info("Токен Telegram найден, все хорошо")
    logger.info("Не пытаемся запустить Flask-приложение")
    
    # Для того чтобы скрипт не завершался сразу
    logger.info("Бот запущен и работает...")
    while True:
        time.sleep(10)
        logger.info("Бот по-прежнему работает...")

if __name__ == "__main__":
    main()