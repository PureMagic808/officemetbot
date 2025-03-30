#!/usr/bin/env python3
"""
Запускающий скрипт для Telegram-бота через workflow run_bot.
"""
import sys
import os
import subprocess
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stdout)

logger = logging.getLogger(__name__)
logger.info("=== ЗАПУСК БОТА ЧЕРЕЗ WORKFLOW ===")

# Устанавливаем переменную окружения для main.py
os.environ["REPLIT_WORKFLOW"] = "run_bot"

# Прямой запуск bot_starter.py
bot_script = "bot_starter.py"
if os.path.exists(bot_script):
    logger.info(f"Запускаем {bot_script}...")
    try:
        # Делаем файл исполняемым
        os.chmod(bot_script, 0o755)
        # Запускаем бота
        subprocess.run([sys.executable, bot_script])
        sys.exit(0)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
else:
    # Альтернативный вариант: запуск main.py с параметром --bot
    logger.info(f"Скрипт {bot_script} не найден, запускаем main.py --bot")
    try:
        subprocess.run([sys.executable, "main.py", "--bot"])
        sys.exit(0)
    except Exception as e:
        logger.error(f"Ошибка при запуске main.py --bot: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)