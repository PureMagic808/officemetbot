#!/usr/bin/env python3
"""
Скрипт для запуска только Telegram-бота в режиме командной строки и через workflow.
"""
import logging
import os
import sys
import subprocess
import time

# Настройка логирования
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])

logger = logging.getLogger(__name__)

def main():
    """Основная функция запуска бота."""
    logger.info("Запуск бота через run_bot_standalone.py")
    
    # Проверяем существование файла bot_starter.py
    bot_script = "bot_starter.py"
    if os.path.exists(bot_script):
        logger.info(f"Найден скрипт бота: {bot_script}")
        try:
            # Делаем скрипт исполняемым
            os.chmod(bot_script, 0o755)
            
            # Запускаем бота
            logger.info(f"Запускаем {bot_script}...")
            subprocess.run([sys.executable, bot_script])
            return True
        except Exception as e:
            logger.error(f"Ошибка при запуске бота: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    else:
        logger.error(f"Не найден скрипт {bot_script}")
        return False

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            logger.warning("Не удалось запустить бота. Попытка запустить альтернативным способом...")
            
            # Пробуем запустить main.py с аргументом --bot
            if os.path.exists("main.py"):
                logger.info("Найден main.py, запускаем с аргументом --bot")
                subprocess.run([sys.executable, "main.py", "--bot"])
            else:
                logger.error("Ни один из скриптов запуска не найден")
                sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)