#!/usr/bin/env python3
"""
Скрипт для запуска Telegram-бота с нулевой толерантностью к рекламе и системой рекомендаций.
Запускает zero_ads_bot.py напрямую, минуя проверки окружения.
"""
import logging
import sys
from zero_ads_bot import main

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                       stream=sys.stdout)
    
    logger = logging.getLogger(__name__)
    logger.info("=== ЗАПУСК TELEGRAM БОТА С РЕКОМЕНДАЦИЯМИ ===")
    
    # Прямой запуск бота
    main()