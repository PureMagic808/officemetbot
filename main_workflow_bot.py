#!/usr/bin/env python3
"""
Главный запускающий файл для бота с автообновлением в workflow run_bot.
Этот файл не выполняет проверку окружения, а просто запускает бота.
"""
import logging
import sys
import os

def main():
    """Основная функция прямого запуска бота"""
    # Настраиваем логирование
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                       stream=sys.stdout)
    
    logger = logging.getLogger(__name__)
    logger.info("=== ЗАПУСК TELEGRAM БОТА ИЗ WORKFLOW ===")
    
    # Первоначально пробуем запустить бота с нулевой толерантностью к рекламе и рекомендациями
    recommendation_bot_script = "run_bot_with_recommendations.py"
    if os.path.exists(recommendation_bot_script):
        logger.info(f"Запускаем бота с рекомендациями и нулевой толерантностью к рекламе {recommendation_bot_script}...")
        try:
            # Делаем файл исполняемым
            os.chmod(recommendation_bot_script, 0o755)
            # Импортируем модуль и запускаем основную функцию
            from zero_ads_bot import main as bot_main
            bot_main()
            sys.exit(0)
        except Exception as e:
            logger.error(f"Ошибка при запуске бота с рекомендациями: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    # Запасной вариант - бот с нулевой толерантностью к рекламе без рекомендаций
    zero_ads_bot_script = "run_zero_ads_bot.py"
    if os.path.exists(zero_ads_bot_script):
        logger.info(f"Запускаем бота с нулевой толерантностью к рекламе {zero_ads_bot_script}...")
        try:
            # Делаем файл исполняемым
            os.chmod(zero_ads_bot_script, 0o755)
            # Импортируем модуль и запускаем основную функцию
            from zero_ads_bot import main as bot_main
            bot_main()
            sys.exit(0)
        except Exception as e:
            logger.error(f"Ошибка при запуске бота с нулевой толерантностью к рекламе: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
    # Если ни один из вариантов не сработал, пробуем запустить обычного бота
    logger.info("Запускаем обычного бота...")
    try:
        # Импортируем и запускаем бота
        from bot import run_bot
        run_bot()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()