#!/usr/bin/env python3
"""
Запуск бота через workflow run_bot.
Этот скрипт должен быть запущен из workflow run_bot.
Он предотвращает одновременный запуск множества ботов.
"""

import os
import sys
import subprocess
import logging
import time
import signal

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Имя lockfile для предотвращения одновременных запусков
LOCK_FILE = ".telegram_bot_lock"

# Функция для очистки lockfile при выходе
def cleanup_handler(sig, frame):
    """Обработчик сигналов для корректного завершения работы."""
    logger.info("Получен сигнал завершения, очищаем lockfile...")
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception as e:
        logger.error(f"Ошибка при удалении lockfile: {e}")
    sys.exit(0)

# Регистрируем обработчики сигналов
signal.signal(signal.SIGINT, cleanup_handler)
signal.signal(signal.SIGTERM, cleanup_handler)

def check_lock_file():
    """Проверяет наличие lockfile и его актуальность."""
    if os.path.exists(LOCK_FILE):
        try:
            # Проверяем возраст файла
            file_time = os.path.getmtime(LOCK_FILE)
            current_time = time.time()
            
            # Если файл создан меньше 5 минут назад, считаем его актуальным
            if current_time - file_time < 300:  # 5 минут
                # Читаем PID из файла
                try:
                    with open(LOCK_FILE, 'r') as f:
                        pid = int(f.read().strip())
                    
                    # Проверяем, запущен ли процесс с таким PID
                    try:
                        os.kill(pid, 0)  # Сигнал 0 только проверяет существование процесса
                        logger.warning(f"Бот уже запущен (PID: {pid}). Выходим.")
                        return True  # Процесс существует
                    except OSError:
                        logger.warning(f"Найден lockfile, но процесс {pid} не запущен. Удаляем lockfile.")
                        os.remove(LOCK_FILE)
                except Exception as e:
                    logger.error(f"Ошибка при чтении PID из lockfile: {e}")
                    os.remove(LOCK_FILE)  # Удаляем неверный lockfile
            else:
                logger.warning(f"Найден устаревший lockfile (возраст: {current_time - file_time:.1f} сек). Удаляем.")
                os.remove(LOCK_FILE)
        except Exception as e:
            logger.error(f"Ошибка при проверке lockfile: {e}")
            try:
                os.remove(LOCK_FILE)
            except:
                pass
    
    return False  # Можно запускать бота

def create_lock_file():
    """Создает lockfile с текущим PID."""
    try:
        with open(LOCK_FILE, 'w') as f:
            f.write(str(os.getpid()))
        logger.info(f"Создан lockfile с PID {os.getpid()}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при создании lockfile: {e}")
        return False

def main():
    """Основная функция запуска бота из workflow run_bot."""
    # Пометка, что бот запускается из workflow run_bot
    os.environ["REPLIT_WORKFLOW"] = "run_bot"
    
    logger.info("=== ЗАПУСК БОТА ИЗ WORKFLOW RUN_BOT ===")
    
    # Проверяем, не запущен ли уже бот
    if check_lock_file():
        logger.info("Бот уже запущен, выходим")
        sys.exit(0)
    
    # Создаем lockfile
    if not create_lock_file():
        logger.error("Не удалось создать lockfile, но продолжаем запуск")
    
    try:
        # Прямой запуск бота через import (наиболее надежный способ)
        logger.info("Запускаем бота напрямую через import zero_ads_bot...")
        import zero_ads_bot
        zero_ads_bot.main()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Ошибка при прямом запуске бота: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    # Если прямой запуск не сработал, пробуем через запуск скрипта
    scripts_to_try = [
        "zero_ads_bot.py",
        "bot_workflow.py",
        "bot_starter.py"
    ]
    
    for script in scripts_to_try:
        if os.path.exists(script):
            logger.info(f"Запускаем скрипт {script}...")
            try:
                # Делаем файл исполняемым
                os.chmod(script, 0o755)
                # Запускаем бота
                subprocess.run([sys.executable, script])
                sys.exit(0)
            except Exception as e:
                logger.error(f"Ошибка при запуске скрипта {script}: {e}")
                import traceback
                logger.error(traceback.format_exc())
    
    logger.error("Не удалось запустить бота ни одним из доступных способов")
    
    # Удаляем lockfile перед выходом
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception as e:
        logger.error(f"Ошибка при удалении lockfile: {e}")
    
    sys.exit(1)

if __name__ == "__main__":
    main()
