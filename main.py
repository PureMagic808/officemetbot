#!/usr/bin/env python3
"""
Точка входа для запуска бота офисных мемов.
Позволяет запускать либо веб-приложение, либо самого бота в зависимости от конфигурации.
"""
import os
import logging
import sys
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# Импортируем приложение Flask для Gunicorn
from app import app

# Режим запуска: "bot" или "web"
RUN_MODE = os.environ.get("RUN_MODE", "web").lower()

# Запуск программы напрямую (не через Gunicorn)
if __name__ == "__main__":
    if RUN_MODE == "bot":
        # Запуск Telegram-бота
        logger.info("Запуск в режиме бота")
        try:
            import bot_railway
            bot_railway.main()
        except ImportError as e:
            logger.error(f"Не удалось импортировать модуль bot_railway: {e}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Ошибка при запуске бота: {e}")
            sys.exit(1)
    else:
        # Запуск веб-приложения напрямую
        logger.info("Запуск в режиме веб-приложения")
        try:
            app.run(host='0.0.0.0', port=5000, debug=True)
        except Exception as e:
            logger.error(f"Ошибка при запуске веб-приложения: {e}")
            sys.exit(1)