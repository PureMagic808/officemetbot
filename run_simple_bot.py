#!/usr/bin/env python3
"""
Скрипт для запуска простого телеграм-бота через workflow.
Не конфликтует с веб-сервером.
"""
import logging
import os
import sys
import subprocess

# Настройка логирования
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stdout)
logger = logging.getLogger(__name__)

def main():
    """Функция для прямого запуска телеграм-бота"""
    logger.info("=== ЗАПУСК TELEGRAM-БОТА ИЗ WORKFLOW ===")
    
    # Проверяем наличие токена
    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        logger.error("Ошибка: не задан токен в переменной TELEGRAM_BOT_TOKEN")
        sys.exit(1)
    
    # Используем простой запуск бота из отдельного файла
    bot_script = "simple_workflow_bot.py"
    
    if os.path.exists(bot_script):
        logger.info(f"Запускаем бота из файла {bot_script}...")
        try:
            # Делаем файл исполняемым
            os.chmod(bot_script, 0o755)
            
            # Запускаем бота
            subprocess.run([sys.executable, bot_script])
        except Exception as e:
            logger.error(f"Ошибка при запуске бота: {e}")
            import traceback
            logger.error(traceback.format_exc())
            sys.exit(1)
    else:
        logger.error(f"Не найден файл {bot_script}")
        sys.exit(1)

if __name__ == "__main__":
    main()