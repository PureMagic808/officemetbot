#!/usr/bin/env python3
"""
Прямой запуск Telegram-бота без дополнительных обёрток.
Этот файл вызывается из main.py при обнаружении запуска из workflow run_bot.
"""
import os
import sys
import logging
import subprocess

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   stream=sys.stdout)

logger = logging.getLogger(__name__)
logger.info("Прямой запуск Telegram-бота...")

try:
    # Проверяем наличие необходимых библиотек
    import telegram
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler
    
    # Если импорт прошел успешно, запускаем бота
    from run_bot_direct import main
    
    logger.info("Запуск бота через run_bot_direct...")
    main()
    
except ImportError as e:
    logger.error(f"Ошибка импорта библиотек: {e}")
    
    # Пытаемся установить python-telegram-bot напрямую
    try:
        logger.info("Пытаемся установить python-telegram-bot...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "python-telegram-bot==20.7"])
        
        logger.info("Библиотека установлена, перезапускаем...")
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        logger.error(f"Не удалось установить библиотеку: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
except Exception as e:
    logger.error(f"Ошибка при запуске бота: {e}")
    import traceback
    logger.error(traceback.format_exc())