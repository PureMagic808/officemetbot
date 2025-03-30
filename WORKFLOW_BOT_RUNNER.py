#!/usr/bin/env python3
"""
Этот файл специально создан как точка входа для запуска бота через workflow run_bot.
"""
import os
import sys
import logging
import subprocess

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Устанавливаем переменную окружения REPLIT_WORKFLOW для запуска бота
os.environ["REPLIT_WORKFLOW"] = "run_bot"

def try_run_bot():
    """
    Пытается запустить бота через различные скрипты в порядке приоритета.
    """
    scripts = [
        "bot_starter.py",
        "run_bot.py",
        "main.py --bot"
    ]
    
    for script in scripts:
        logger.info(f"Пробуем запустить через скрипт: {script}")
        
        if " " in script:  # Это команда с аргументами
            cmd = script.split()
            cmd[0] = sys.executable if not cmd[0].endswith(".py") else cmd[0]
        else:  # Это просто имя файла
            if not os.path.exists(script):
                logger.warning(f"Скрипт {script} не найден, пропускаем...")
                continue
            cmd = [sys.executable, script]
        
        try:
            # Выполняем скрипт
            logger.info(f"Запускаем команду: {' '.join(cmd)}")
            result = subprocess.run(cmd)
            
            if result.returncode == 0:
                logger.info(f"Скрипт {script} успешно выполнен!")
                return True
            else:
                logger.warning(f"Скрипт {script} завершился с ошибкой (код {result.returncode}), пробуем следующий...")
        except Exception as e:
            logger.error(f"Ошибка при запуске скрипта {script}: {e}")
            continue
    
    logger.error("Не удалось запустить бота ни через один из доступных скриптов!")
    return False

if __name__ == "__main__":
    logger.info("=== ЗАПУСК БОТА ЧЕРЕЗ WORKFLOW RUN_BOT ===")
    success = try_run_bot()
    sys.exit(0 if success else 1)