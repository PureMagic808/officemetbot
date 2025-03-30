#!/usr/bin/env python3
"""
Единая точка входа для всех видов запуска.
Этот файл определяет, как запускать приложение в зависимости от режима.
"""
import os
import sys
import logging
import traceback

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stdout)

logger = logging.getLogger(__name__)

def main():
    """Основная функция для определения режима запуска"""
    # Определяем workflow, из которого запущен скрипт
    workflow_info = os.environ.get("REPLIT_WORKFLOW", "")
    logger.info(f"REPLIT_WORKFLOW: {workflow_info}")
    
    # Если запуск из workflow run_bot, запускаем бота
    if workflow_info == "run_bot":
        logger.info("Обнаружен workflow run_bot - запускаем бота")
        run_bot()
    else:
        logger.info("Запуск не из workflow run_bot - запускаем веб-приложение")
        run_webapp()

def run_bot():
    """Функция для запуска Telegram бота"""
    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения!")
        sys.exit(1)
    
    # Запускаем бота через direct_bot.py
    bot_script = "direct_bot.py"
    
    if os.path.exists(bot_script):
        logger.info(f"Запускаем бота напрямую через {bot_script}...")
        try:
            import direct_bot
            direct_bot.main()
            # Эта точка не должна быть достигнута, так как бот блокирует выполнение
            logger.error("Бот неожиданно завершился")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Ошибка при запуске {bot_script}: {e}")
            logger.error(traceback.format_exc())
            sys.exit(1)
    else:
        logger.error(f"Файл {bot_script} не найден")
        sys.exit(1)

def run_webapp():
    """Функция для запуска веб-приложения"""
    try:
        logger.info("Запускаем веб-приложение...")
        # Импортируем Flask только если нужно запустить веб-приложение
        from flask import Flask, render_template, jsonify
        
        # Импортируем данные для мемов
        from meme_data import MEMES
        
        # Словарь для хранения состояния бота
        user_states = {}
        
        # Пытаемся импортировать состояние бота
        try:
            from bot import user_states
            logger.info(f"Импортировано состояние бота, пользователей: {len(user_states)}")
        except ImportError as e:
            logger.warning(f"Не удалось импортировать состояние бота: {e}")
        
        # Создаем Flask приложение
        app = Flask(__name__)
        app.secret_key = os.environ.get("SESSION_SECRET", "temp_secret_key")
        
        @app.route('/')
        def home():
            return render_template('index.html')
        
        @app.route('/api/stats')
        def stats():
            # Подсчет статистики для мемов
            meme_stats = {}
            
            for user_id, user_data in user_states.items():
                for meme_id, rating in user_data.get("ratings", {}).items():
                    if meme_id not in meme_stats:
                        meme_stats[meme_id] = {"likes": 0, "dislikes": 0}
                    
                    if rating == 1:
                        meme_stats[meme_id]["likes"] += 1
                    elif rating == -1:
                        meme_stats[meme_id]["dislikes"] += 1
            
            # Добавляем информацию о мемах, у которых еще нет оценок
            for meme_id in MEMES:
                if meme_id not in meme_stats:
                    meme_stats[meme_id] = {"likes": 0, "dislikes": 0}
            
            return jsonify({
                "user_count": len(user_states),
                "meme_stats": meme_stats
            })
        
        # Запускаем Flask-приложение
        logger.info("Веб-приложение готово к запуску")
        app.run(host='0.0.0.0', port=5000, debug=True)
        
    except Exception as e:
        logger.error(f"Ошибка при запуске веб-приложения: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()