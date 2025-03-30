#!/usr/bin/env python3
"""
Стартовый скрипт для автоопределения режима запуска.
"""
import os
import sys
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stdout)

logger = logging.getLogger(__name__)

def main():
    """
    Основная функция для определения режима запуска.
    Эта функция вызывается из main.py.
    """
    # Определяем источник запуска по переменным окружения
    workflow_info = os.environ.get("REPLIT_WORKFLOW", "")
    logger.info(f"Обнаружен REPLIT_WORKFLOW: {workflow_info}")

    # Если это workflow run_bot, запускаем бота
    if "run_bot" in workflow_info:
        logger.info("Запуск в режиме только бота...")
        try:
            import bot_only
            bot_only.main()
        except Exception as e:
            logger.error(f"Ошибка при запуске bot_only: {e}")
            import traceback
            logger.error(traceback.format_exc())
            sys.exit(1)
    # Иначе запускаем веб-приложение
    else:
        logger.info("Запуск в режиме веб-приложения...")
        try:
            import main
            # main уже содержит код запуска Flask приложения в блоке if __name__ == "__main__"
        except Exception as e:
            logger.error(f"Ошибка при запуске main: {e}")
            import traceback
            logger.error(traceback.format_exc())
            sys.exit(1)

# Если запущен напрямую, а не импортирован
if __name__ == "__main__":
    main()