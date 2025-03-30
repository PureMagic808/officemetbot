#!/usr/bin/env python3
"""
Специальный файл для запуска Telegram-бота через workflow.
Этот файл напрямую запускает бота без дополнительной проверки окружения.
"""
import logging
import sys
from zero_ads_bot import main

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                      stream=sys.stdout)
    logger = logging.getLogger(__name__)
    
    logger.info("Запуск Telegram-бота с персональными рекомендациями через workflow...")
    main()