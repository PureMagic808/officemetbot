import os
import sys
import subprocess
import time
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stdout)

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logger.info('Запуск Telegram-бота...')
    
    # Запускаем бота напрямую с помощью subprocess
    subprocess.run([sys.executable, 'telegram_bot_runner.py'])

