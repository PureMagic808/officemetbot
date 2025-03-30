#!/usr/bin/env python3
"""
Скрипт для прямого запуска Telegram-бота с нулевой толерантностью к рекламе.
Этот скрипт запускается напрямую как отдельный процесс, минуя проверки окружения.
"""
import os
import sys
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   stream=sys.stdout)

logger = logging.getLogger(__name__)
logger.info("=== ПРЯМОЙ ЗАПУСК TELEGRAM БОТА БЕЗ РЕКЛАМЫ ===")

if __name__ == "__main__":
    try:
        # Импортируем и запускаем бота напрямую
        from zero_ads_bot import main
        logger.info("Запуск zero_ads_bot.main()")
        main()
    except Exception as e:
        logger.error(f"Ошибка при запуске: {e}")
        import traceback
        logger.error(traceback.format_exc())