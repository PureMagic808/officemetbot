#!/usr/bin/env python3
"""
Скрипт для запуска основного бота через workflow run_bot.
Этот файл запускается из workflow run_bot.
"""
import os
import sys
import logging

# Настраиваем логирование
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   stream=sys.stdout)

logger = logging.getLogger(__name__)
logger.info("=== ЗАПУСК ОСНОВНОГО БОТА ЧЕРЕЗ WORKFLOW ===")

# Используем скрипт main_workflow_bot.py для запуска бота
script_path = "main_workflow_bot.py"
if os.path.exists(script_path):
    logger.info(f"Запускаем основной скрипт бота {script_path}...")
    try:
        # Делаем файл исполняемым
        os.chmod(script_path, 0o755)
        # Импортируем и запускаем
        from main_workflow_bot import main
        main()
    except Exception as e:
        logger.error(f"Ошибка при запуске основного скрипта бота: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
else:
    logger.error(f"Не найден скрипт {script_path}")
    sys.exit(1)