from flask import Flask, render_template, jsonify
import logging
import os
import sys

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stdout)

logger = logging.getLogger(__name__)

# Импортируем данные для мемов
from meme_data import MEMES

# Словарь для хранения состояния бота в случае, если бот не запущен
# В нормальных условиях это будет заменено данными из запущенного бота
user_states = {}

# Пытаемся импортировать состояние бота
try:
    from bot import user_states
    logger.info(f"Импортировано состояние бота, пользователей: {len(user_states)}")
except ImportError as e:
    logger.warning(f"Не удалось импортировать состояние бота: {e}")

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

if __name__ == "__main__":
    logger.info("Запуск веб-приложения для администрирования бота")
    app.run(host='0.0.0.0', port=5000, debug=True)