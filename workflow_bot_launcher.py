#!/usr/bin/env python3
"""
Запускающий скрипт для Telegram-бота с рекомендациями.
Этот файл специально предназначен для запуска через workflow run_bot.
"""
import os
import logging
import sys
import signal
import time
import json
from typing import Dict, List, Optional, Set, Tuple, Union
from threading import Thread

# Настраиваем логирование
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   stream=sys.stdout)

logger = logging.getLogger(__name__)
logger.info("=== ЗАПУСК TELEGRAM БОТА С РЕКОМЕНДАЦИЯМИ ===")

try:
    # Проверяем наличие токена для Telegram-бота
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.error("Не найден токен для Telegram бота!")
        sys.exit(1)
    
    # Попытка импорта необходимых модулей
    try:
        import telegram
        from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
        import advanced_filter
        from recommendation_engine import (
            update_user_preferences, 
            get_recommendation_score,
            recommend_memes,
            get_user_preferences_stats
        )
        logger.info("Все необходимые модули успешно импортированы")
    except ImportError as e:
        logger.error(f"Ошибка импорта модулей: {e}")
        sys.exit(1)
    
    # Запускаем бота из zero_ads_bot.py
    logger.info("Запускаем бота с рекомендациями...")
    try:
        from zero_ads_bot import main
        main()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота с рекомендациями: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Пробуем запустить обычного бота с нулевой толерантностью к рекламе
        try:
            logger.info("Пробуем запустить обычного бота...")
            from direct_workflow_bot import main as direct_main
            direct_main()
        except Exception as e2:
            logger.error(f"Ошибка при запуске обычного бота: {e2}")
            logger.error(traceback.format_exc())
            sys.exit(1)
except Exception as e:
    logger.error(f"Необработанное исключение: {e}")
    import traceback
    logger.error(traceback.format_exc())
    sys.exit(1)