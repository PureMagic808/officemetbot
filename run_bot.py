#!/usr/bin/env python3
"""
Запускающий скрипт для Telegram-бота через workflow run_bot.
Этот файл напрямую запускает рекомендательного бота.
"""
import sys
import os
import subprocess
import logging
import signal

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stdout)

logger = logging.getLogger(__name__)
logger.info("=== ЗАПУСК TELEGRAM БОТА С РЕКОМЕНДАЦИЯМИ ===")

# Обработчик сигналов для корректного завершения
def signal_handler(sig, frame):
    logger.info("Получен сигнал завершения, закрываем бота")
    sys.exit(0)

# Регистрируем обработчик сигналов
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Прямой запуск бота с рекомендациями и нулевой рекламой
bot_script = "run_zero_ads_bot.py"
if os.path.exists(bot_script):
    logger.info(f"Запускаем бота с нулевой толерантностью к рекламе {bot_script}...")
    try:
        # Делаем файл исполняемым
        os.chmod(bot_script, 0o755)
        # Прямой запуск бота для телеграма
        import zero_ads_bot
        zero_ads_bot.main()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Ошибка при прямом запуске бота: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Пробуем через subprocess как запасной вариант
        try:
            # Запускаем бота с нулевой толерантностью к рекламе
            subprocess.run([sys.executable, bot_script])
            sys.exit(0)
        except Exception as e2:
            logger.error(f"Ошибка при запуске бота через subprocess: {e2}")
            logger.error(traceback.format_exc())
else:
    # Если скрипт не найден, пробуем альтернативные варианты
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
    
    # Последний вариант - прямой запуск
    logger.info("Пробуем запустить напрямую через import")
    try:
        import bot
        bot.run_bot()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Ошибка при прямом импорте бота: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
