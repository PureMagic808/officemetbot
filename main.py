#!/usr/bin/env python3
"""
Основной входной файл для Flask-приложения и Telegram-бота.
"""

# Для исправления ошибки "Import "flask" could not be resolved"
import flask
import logging
import os
import sys
import subprocess
import time

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stdout)

logger = logging.getLogger(__name__)
logger.info("Запуск main.py")

# Устанавливаем специальный флаг для определения запуска в workflow run_bot
# Если этот файл запускается напрямую из workflow run_bot, то создаем маркерный файл
if len(sys.argv) == 1:
    workflow_marker_file = ".workflow_run_bot_running"
    with open(workflow_marker_file, "w") as f:
        f.write(str(time.time()))
    logger.info(f"Создан маркерный файл {workflow_marker_file} для workflow run_bot")

# Проверяем аргументы командной строки и окружение
if len(sys.argv) > 1 and sys.argv[1] == "--bot":
    # Явный запуск бота через аргумент командной строки
    logger.info("Запуск бота через аргумент командной строки --bot")
    bot_script = "auto_update_bot.py"  # Используем новый бот с автообновлением
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
        logger.error(f"Не найден скрипт {bot_script}")
        sys.exit(1)

# Определяем, запускаемся ли из workflow или из оболочки командной строки
is_workflow = False
workflow_name = os.environ.get("REPLIT_WORKFLOW", "")
# Проверка наличия маркерного файла
workflow_marker_file = ".workflow_run_bot_running"
if os.path.exists(workflow_marker_file):
    with open(workflow_marker_file, "r") as f:
        marker_time = float(f.read().strip())
        # Проверяем, что маркер создан не более 10 секунд назад
        if time.time() - marker_time < 20:
            is_workflow = True
            workflow_name = "run_bot"
            logger.info("Обнаружен запуск из workflow run_bot по маркерному файлу")
        else:
            # Удаляем устаревший маркер
            os.remove(workflow_marker_file)
            logger.info("Обнаружен устаревший маркерный файл, удален")

# Проверка на запуск из workflow через логи процессов
if not is_workflow:
    workflow_log_pattern = "workflow.run"
    log_cmd = "ps aux | grep -v grep | grep python | grep -E 'workflow.*run_bot'"
    try:
        process_info = subprocess.check_output(log_cmd, shell=True, stderr=subprocess.STDOUT).decode('utf-8')
        if process_info and workflow_log_pattern in process_info:
            is_workflow = True
            workflow_name = "run_bot"
            logger.info("Обнаружен запуск из workflow run_bot через логи процессов")
    except Exception as e:
        logger.info(f"Ошибка при проверке логов процессов: {e}")

# Если запущен из workflow run_bot, НЕ запускаем бота - он запускается отдельно
if is_workflow and workflow_name == "run_bot":
    logger.info("Обнаружен запуск из workflow run_bot - пропускаем запуск бота")
    logger.info("Бот будет запущен отдельно из workflow run_bot")

# Проверяем наличие определенных переменных окружения, которые могут указывать на workflow
if "REPLIT_WORKFLOW" in os.environ or is_workflow:
    logger.info(f"REPLIT_WORKFLOW: {workflow_name}")
    
    # Если запущено из workflow run_bot, не запускаем бота в main.py
    # Бот должен быть запущен отдельным процессом из workflow
    if workflow_name == "run_bot" or is_workflow:
        logger.info("Обнаружен workflow run_bot - пропускаем запуск бота внутри main.py")
        logger.info("Переходим к запуску только веб-приложения")
    else:
        # Запуск из workflow run_bot
        logger.info("Запуск Telegram-бота (workflow или прямой запуск)")
        
        # Попробуем запустить через новый рабочий процесс
        workflow_main_bot = "run_workflow_main_bot.py"
        if os.path.exists(workflow_main_bot):
            logger.info(f"Запускаем бота через рабочий процесс {workflow_main_bot}...")
            try:
                # Делаем файл исполняемым
                os.chmod(workflow_main_bot, 0o755)
                # Запускаем бота через рабочий процесс
                subprocess.run([sys.executable, workflow_main_bot])
                sys.exit(0)
            except Exception as e:
                logger.error(f"Ошибка при запуске бота через рабочий процесс: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        # Первоначально пробуем запустить бота с нулевой толерантностью к рекламе и рекомендациями
        recommendation_bot_script = "run_bot_with_recommendations.py"
        if os.path.exists(recommendation_bot_script):
            logger.info(f"Запускаем бота с рекомендациями и нулевой толерантностью к рекламе {recommendation_bot_script}...")
            try:
                # Делаем файл исполняемым
                os.chmod(recommendation_bot_script, 0o755)
                # Запускаем бота с рекомендациями
                subprocess.run([sys.executable, recommendation_bot_script])
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
                # Запускаем бота с нулевой толерантностью к рекламе
                subprocess.run([sys.executable, zero_ads_bot_script])
                sys.exit(0)
            except Exception as e:
                logger.error(f"Ошибка при запуске бота с нулевой толерантностью к рекламе: {e}")
                import traceback
                logger.error(traceback.format_exc())
                
        # Пробуем запустить бота с автоматическим обновлением контента
        auto_bot_script = "run_auto_update_bot.py"
        if os.path.exists(auto_bot_script):
            logger.info(f"Запускаем бота с автообновлением {auto_bot_script}...")
            try:
                # Делаем файл исполняемым
                os.chmod(auto_bot_script, 0o755)
                # Запускаем бота с автообновлением контента
                subprocess.run([sys.executable, auto_bot_script])
                sys.exit(0)
            except Exception as e:
                logger.error(f"Ошибка при запуске бота с автообновлением: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        # Если бот с автообновлением не запустился, используем упрощенный запуск
        simple_bot_script = "simple_workflow_bot.py"
        if os.path.exists(simple_bot_script):
            logger.info(f"Запускаем {simple_bot_script} для запуска бота...")
            try:
                # Делаем файл исполняемым
                os.chmod(simple_bot_script, 0o755)
                # Запускаем бота напрямую через упрощенный скрипт
                subprocess.run([sys.executable, simple_bot_script])
                sys.exit(0)
            except Exception as e:
                logger.error(f"Ошибка при запуске бота через упрощенный скрипт: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        # Если упрощенный скрипт не сработал, пробуем прямой запуск
        direct_bot_script = "direct_workflow_bot.py"
        if os.path.exists(direct_bot_script):
            logger.info(f"Запускаем {direct_bot_script} для прямого запуска бота...")
            try:
                # Делаем файл исполняемым
                os.chmod(direct_bot_script, 0o755)
                # Запускаем бота напрямую
                subprocess.run([sys.executable, direct_bot_script])
                sys.exit(0)
            except Exception as e:
                logger.error(f"Ошибка при прямом запуске бота: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        # Запасной вариант, если прямой запуск не сработал
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
            logger.error(f"Не найден скрипт {bot_script}")
            sys.exit(1)
else:
    logger.info("Запуск не из workflow run_bot - запускаем веб-приложение")

# Импортируем и запускаем веб-приложение
logger.info("Запускаем веб-приложение...")
try:
    from flask import Flask, render_template, jsonify
    
    # Импортируем данные для мемов и фильтрацию контента
    from meme_data import MEMES
    import content_filter
    
    # Словарь для хранения состояния бота
    user_states = {}
    
    # Пытаемся импортировать состояние бота
    try:
        from bot import user_states
        logger.info(f"Импортировано состояние бота, пользователей: {len(user_states)}")
    except ImportError as e:
        logger.warning(f"Не удалось импортировать состояние бота: {e}")
    
    logger.info("Веб-приложение готово к запуску")
    
    # Создаем Flask приложение
    app = Flask(__name__)
    app.secret_key = os.environ.get("SESSION_SECRET", "temp_secret_key")
    
    @app.route('/')
    def home():
        # Подготовка данных для шаблона
        meme_stats = {}
        filtered_memes_count = 0
        total_ratings = 0
        
        # Подсчет статистики для мемов и учет фильтрации
        for meme_id, meme_data in MEMES.items():
            # Проверяем, подходит ли мем для показа (не реклама, не спорт и т.д.)
            is_suitable = content_filter.is_suitable_meme(meme_data)
            
            meme_stats[meme_id] = {
                'positive': 0,
                'negative': 0,
                'total': 0,
                'text': meme_data.get('text', ''),
                'image_url': meme_data.get('image_url', ''),
                'source': meme_data.get('source', 'Неизвестно'),
                'filtered': not is_suitable
            }
            
            # Подсчитываем количество отфильтрованных мемов
            if not is_suitable:
                filtered_memes_count += 1
        
        # Добавляем статистику оценок, если есть данные
        for user_id, user_data in user_states.items():
            for meme_id, rating in user_data.get("ratings", {}).items():
                if meme_id in meme_stats:
                    if rating == 1:
                        meme_stats[meme_id]["positive"] += 1
                    elif rating == -1:
                        meme_stats[meme_id]["negative"] += 1
                    
                    # Обновляем общий рейтинг
                    meme_stats[meme_id]["total"] += rating
                    total_ratings += 1
        
        # Сортируем мемы по рейтингу (популярные в начале)
        sorted_memes = sorted(
            meme_stats.items(), 
            key=lambda x: (not x[1]['filtered'], x[1]['total']), 
            reverse=True
        )
        
        return render_template('index.html', 
                             memes=sorted_memes,
                             total_users=len(user_states),
                             total_ratings=total_ratings,
                             total_available=len(MEMES) - filtered_memes_count,
                             total_filtered=filtered_memes_count)
    
    @app.route('/api/stats')
    def stats():
        # Подсчет статистики для мемов
        meme_stats = {}
        filtered_memes_count = 0
        
        for user_id, user_data in user_states.items():
            for meme_id, rating in user_data.get("ratings", {}).items():
                if meme_id not in meme_stats:
                    meme_stats[meme_id] = {"likes": 0, "dislikes": 0}
                
                if rating == 1:
                    meme_stats[meme_id]["likes"] += 1
                elif rating == -1:
                    meme_stats[meme_id]["dislikes"] += 1
        
        # Добавляем информацию о мемах, у которых еще нет оценок
        # и фильтруем рекламный контент
        for meme_id, meme_data in MEMES.items():
            # Проверяем, подходит ли мем для показа (не реклама, не спорт и т.д.)
            is_suitable = content_filter.is_suitable_meme(meme_data)
            
            if meme_id not in meme_stats:
                meme_stats[meme_id] = {
                    "likes": 0, 
                    "dislikes": 0, 
                    "filtered": not is_suitable
                }
            else:
                # Добавляем информацию о фильтрации к уже существующей статистике
                meme_stats[meme_id]["filtered"] = not is_suitable
            
            # Подсчитываем количество отфильтрованных мемов
            if not is_suitable:
                filtered_memes_count += 1
        
        return jsonify({
            "user_count": len(user_states),
            "meme_stats": meme_stats,
            "total_memes": len(MEMES),
            "filtered_memes": filtered_memes_count,
            "available_memes": len(MEMES) - filtered_memes_count
        })
    
    # Запускаем Flask-приложение
    if __name__ == "__main__":
        logger.info("Запуск веб-приложения")
        app.run(host='0.0.0.0', port=5000, debug=True)
        
except Exception as e:
    logger.error(f"Произошла ошибка при запуске: {e}")
    import traceback
    logger.error(traceback.format_exc())
