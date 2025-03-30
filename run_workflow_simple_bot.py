#!/usr/bin/env python3
"""
Специальный скрипт для запуска бота через workflow run_bot.
Этот скрипт запускает workflow_simple_bot.py и игнорирует все проверки.
"""
import os
import subprocess
import sys
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stdout)
logger = logging.getLogger(__name__)

def main():
    """Основная функция для запуска бота через workflow"""
    logger.info("=== ЗАПУСК TELEGRAM-БОТА ЧЕРЕЗ WORKFLOW ===")
    
    # Проверяем наличие токена
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("Не указан токен бота в переменной окружения TELEGRAM_BOT_TOKEN")
        sys.exit(1)
    
    # Запускаем простой бот для workflow
    bot_script = "workflow_simple_bot.py"
    if os.path.exists(bot_script):
        logger.info(f"Запускаем {bot_script}...")
        
        # Делаем файл исполняемым
        os.chmod(bot_script, 0o755)
        
        # Запускаем бота через отдельный процесс
        subprocess.run([sys.executable, bot_script])
    else:
        logger.error(f"Скрипт {bot_script} не найден!")
        sys.exit(1)

if __name__ == "__main__":
    main()