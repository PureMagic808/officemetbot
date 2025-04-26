#!/usr/bin/env python3
"""
Модуль аналитики популярности мемов и статистики взаимодействия пользователей.
Отслеживает популярные мемы, тенденции в оценках и предоставляет
инструменты для анализа эффективности рекомендательной системы.
"""

import os
import json
import time
import logging
from typing import Dict, List, Tuple, Optional, Any, Union, Set
from collections import Counter, defaultdict
import datetime

# Настройка логирования
logger = logging.getLogger(__name__)

# Константы для файлов аналитики
ANALYTICS_DIR = "analytics"
POPULAR_MEMES_FILE = os.path.join(ANALYTICS_DIR, "popular_memes.json")
TRENDING_MEMES_FILE = os.path.join(ANALYTICS_DIR, "trending_memes.json")
RATING_HISTORY_FILE = os.path.join(ANALYTICS_DIR, "rating_history.json")
USER_ACTIVITY_FILE = os.path.join(ANALYTICS_DIR, "user_activity.json")
SESSION_STATS_FILE = os.path.join(ANALYTICS_DIR, "session_stats.json")

# Убедимся, что директория для аналитики существует
if not os.path.exists(ANALYTICS_DIR):
    os.makedirs(ANALYTICS_DIR)

# Глобальные переменные для хранения аналитических данных
popular_memes = {}  # id мема: {показы, лайки, дизлайки, последнее_взаимодействие}
trending_memes = {}  # Trending score по дням
rating_history = []  # История оценок [{meme_id, user_id, rating, timestamp}]
user_activity = defaultdict(lambda: {"ratings": 0, "last_active": 0, "sessions": 0})
session_stats = {
    "total_sessions": 0,  # Общее количество сессий
    "active_users": 0,    # Активные пользователи за последние 24 часа
    "today_ratings": 0,   # Оценки за сегодня
    "total_ratings": 0,   # Общее количество оценок
    "last_update": 0      # Время последнего обновления
}

# Константы времени
DAY_SECONDS = 86400  # 24 часа в секундах
HOUR_SECONDS = 3600  # 1 час в секундах
WEEK_SECONDS = 604800  # 7 дней в секундах

def _load_analytics_files():
    """Загружает данные аналитики из файлов"""
    global popular_memes, trending_memes, rating_history, user_activity, session_stats
    
    try:
        # Загрузка популярных мемов
        if os.path.exists(POPULAR_MEMES_FILE):
            with open(POPULAR_MEMES_FILE, 'r', encoding='utf-8') as f:
                popular_memes = json.load(f)
        
        # Загрузка трендовых мемов
        if os.path.exists(TRENDING_MEMES_FILE):
            with open(TRENDING_MEMES_FILE, 'r', encoding='utf-8') as f:
                trending_memes = json.load(f)
        
        # Загрузка истории оценок
        if os.path.exists(RATING_HISTORY_FILE):
            with open(RATING_HISTORY_FILE, 'r', encoding='utf-8') as f:
                rating_history = json.load(f)
        
        # Загрузка активности пользователей
        if os.path.exists(USER_ACTIVITY_FILE):
            with open(USER_ACTIVITY_FILE, 'r', encoding='utf-8') as f:
                user_activity_data = json.load(f)
                # Конвертируем ключи обратно в int, так как JSON хранит ключи как строки
                user_activity = defaultdict(lambda: {"ratings": 0, "last_active": 0, "sessions": 0})
                for user_id, data in user_activity_data.items():
                    user_activity[int(user_id)] = data
        
        # Загрузка статистики сессий
        if os.path.exists(SESSION_STATS_FILE):
            with open(SESSION_STATS_FILE, 'r', encoding='utf-8') as f:
                session_stats = json.load(f)
        
        logger.info("Аналитические данные успешно загружены")
    except Exception as e:
        logger.error(f"Ошибка при загрузке аналитических данных: {e}")

def _save_analytics_files():
    """Сохраняет данные аналитики в файлы"""
    try:
        # Сохранение популярных мемов
        with open(POPULAR_MEMES_FILE, 'w', encoding='utf-8') as f:
            json.dump(popular_memes, f, ensure_ascii=False)
        
        # Сохранение трендовых мемов
        with open(TRENDING_MEMES_FILE, 'w', encoding='utf-8') as f:
            json.dump(trending_memes, f, ensure_ascii=False)
        
        # Сохранение истории оценок (ограничиваем до 1000 последних записей)
        with open(RATING_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(rating_history[-1000:], f, ensure_ascii=False)
        
        # Сохранение активности пользователей
        with open(USER_ACTIVITY_FILE, 'w', encoding='utf-8') as f:
            json.dump(dict(user_activity), f, ensure_ascii=False)
        
        # Сохранение статистики сессий
        with open(SESSION_STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(session_stats, f, ensure_ascii=False)
        
        logger.debug("Аналитические данные успешно сохранены")
    except Exception as e:
        logger.error(f"Ошибка при сохранении аналитических данных: {e}")

# Инициализация - загружаем существующие данные
_load_analytics_files()

def record_meme_view(meme_id: str, user_id: int):
    """
    Записывает просмотр мема пользователем
    
    Args:
        meme_id (str): Идентификатор мема
        user_id (int): Идентификатор пользователя
    """
    now = time.time()
    
    # Обновляем статистику популярных мемов
    if meme_id not in popular_memes:
        popular_memes[meme_id] = {
            "views": 0,
            "likes": 0,
            "dislikes": 0,
            "last_interaction": int(now)
        }
    
    popular_memes[meme_id]["views"] += 1
    popular_memes[meme_id]["last_interaction"] = int(now)
    
    # Обновляем активность пользователя
    user_activity[user_id]["last_active"] = int(now)
    
    # Обновляем статистику сессий
    _update_session_stats()
    
    # Периодически сохраняем данные
    if time.time() % 60 < 1:  # примерно раз в минуту
        _save_analytics_files()

def record_meme_rating(meme_id: str, user_id: int, rating: int):
    """
    Записывает оценку мема пользователем
    
    Args:
        meme_id (str): Идентификатор мема
        user_id (int): Идентификатор пользователя
        rating (int): Оценка (1 - положительная, -1 - отрицательная)
    """
    now = time.time()
    
    # Обновляем статистику популярных мемов
    if meme_id not in popular_memes:
        popular_memes[meme_id] = {
            "views": 1,  # Если ставит оценку, значит видел мем
            "likes": 0,
            "dislikes": 0,
            "last_interaction": int(now)
        }
    
    if rating == 1:
        popular_memes[meme_id]["likes"] += 1
    elif rating == -1:
        popular_memes[meme_id]["dislikes"] += 1
    
    popular_memes[meme_id]["last_interaction"] = int(now)
    
    # Добавляем запись в историю оценок
    rating_history.append({
        "meme_id": meme_id,
        "user_id": user_id,
        "rating": rating,
        "timestamp": int(now)
    })
    
    # Обновляем активность пользователя
    user_activity[user_id]["ratings"] += 1
    user_activity[user_id]["last_active"] = int(now)
    
    # Обновляем статистику сессий
    session_stats["total_ratings"] += 1
    session_stats["today_ratings"] += 1
    _update_session_stats()
    
    # Обновляем данные трендов
    _update_trending_memes(meme_id, rating)
    
    # Сохраняем данные после каждой оценки
    _save_analytics_files()

def record_user_session(user_id: int):
    """
    Записывает новую сессию пользователя
    
    Args:
        user_id (int): Идентификатор пользователя
    """
    now = time.time()
    
    # Проверяем, не была ли уже зарегистрирована сессия недавно
    last_active = user_activity[user_id].get("last_active", 0)
    if now - last_active > HOUR_SECONDS:  # Если прошло больше часа с момента последней активности
        user_activity[user_id]["sessions"] += 1
        session_stats["total_sessions"] += 1
    
    user_activity[user_id]["last_active"] = int(now)
    
    # Обновляем статистику сессий
    _update_session_stats()
    
    # Периодически сохраняем данные
    if time.time() % 60 < 1:  # примерно раз в минуту
        _save_analytics_files()

def _update_session_stats():
    """Обновляет общую статистику сессий"""
    now = time.time()
    
    # Обновляем счетчик активных пользователей
    active_users = 0
    for user_id, data in user_activity.items():
        if now - data["last_active"] < DAY_SECONDS:
            active_users += 1
    
    session_stats["active_users"] = active_users
    
    # Сбрасываем счетчик оценок за день, если прошло более 24 часов
    if now - session_stats.get("last_update", 0) > DAY_SECONDS:
        session_stats["today_ratings"] = 0
        session_stats["last_update"] = int(now)

def _update_trending_memes(meme_id: str, rating: int):
    """
    Обновляет трендовые мемы на основе новой оценки
    
    Args:
        meme_id (str): Идентификатор мема
        rating (int): Оценка (1 - положительная, -1 - отрицательная)
    """
    now = time.time()
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    if today not in trending_memes:
        trending_memes[today] = {}
    
    if meme_id not in trending_memes[today]:
        trending_memes[today][meme_id] = {
            "score": 0,
            "likes": 0,
            "dislikes": 0
        }
    
    # Обновляем счетчики для конкретного дня
    if rating == 1:
        trending_memes[today][meme_id]["likes"] += 1
    elif rating == -1:
        trending_memes[today][meme_id]["dislikes"] += 1
    
    # Вычисляем score (учитываем и положительные и отрицательные оценки)
    likes = trending_memes[today][meme_id]["likes"]
    dislikes = trending_memes[today][meme_id]["dislikes"]
    total = likes + dislikes
    
    # Формула для расчета тренда: (лайки - дизлайки) / (общее количество)
    # Это дает нам значение от -1 до 1, которое мы масштабируем до 0-100
    if total > 0:
        score = ((likes - dislikes) / total + 1) * 50
    else:
        score = 50  # Нейтральный скор, если нет оценок
    
    trending_memes[today][meme_id]["score"] = int(score)
    
    # Очищаем старые записи (старше недели)
    keys_to_remove = []
    for date_str in trending_memes.keys():
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        if (datetime.datetime.now() - date_obj).days > 7:
            keys_to_remove.append(date_str)
    
    for key in keys_to_remove:
        del trending_memes[key]

def get_popular_memes(limit: int = 10, period: str = "all") -> List[Dict]:
    """
    Возвращает список популярных мемов
    
    Args:
        limit (int): Максимальное количество мемов для возврата
        period (str): Период ('day', 'week', 'month', 'all')
    
    Returns:
        List[Dict]: Список словарей с данными популярных мемов
    """
    now = time.time()
    period_seconds = {
        "day": DAY_SECONDS,
        "week": WEEK_SECONDS,
        "month": DAY_SECONDS * 30,
        "all": float('inf')
    }.get(period, float('inf'))
    
    # Фильтруем мемы по времени последнего взаимодействия
    filtered_memes = {
        meme_id: data for meme_id, data in popular_memes.items()
        if now - data.get("last_interaction", 0) < period_seconds
    }
    
    # Сортируем по количеству взаимодействий и положительным оценкам
    sorted_memes = sorted(
        filtered_memes.items(), 
        key=lambda x: (x[1].get("likes", 0) - x[1].get("dislikes", 0), x[1].get("views", 0)),
        reverse=True
    )
    
    # Форматируем результат
    result = []
    for meme_id, data in sorted_memes[:limit]:
        result.append({
            "meme_id": meme_id,
            "likes": data.get("likes", 0),
            "dislikes": data.get("dislikes", 0),
            "views": data.get("views", 0),
            "popularity_score": _calculate_popularity_score(data),
            "last_interaction": data.get("last_interaction", 0)
        })
    
    return result

def get_trending_memes(limit: int = 10, days: int = 1) -> List[Dict]:
    """
    Возвращает список трендовых мемов за указанный период
    
    Args:
        limit (int): Максимальное количество мемов для возврата
        days (int): Количество дней для анализа (1-7)
    
    Returns:
        List[Dict]: Список словарей с данными трендовых мемов
    """
    days = min(max(days, 1), 7)  # Ограничиваем от 1 до 7 дней
    
    # Получаем даты для анализа
    dates = []
    for i in range(days):
        date = (datetime.datetime.now() - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        dates.append(date)
    
    # Собираем данные по мемам за указанные дни
    meme_trends = defaultdict(lambda: {"score": 0, "likes": 0, "dislikes": 0, "days": 0})
    
    for date in dates:
        if date in trending_memes:
            for meme_id, data in trending_memes[date].items():
                meme_trends[meme_id]["score"] += data.get("score", 0)
                meme_trends[meme_id]["likes"] += data.get("likes", 0)
                meme_trends[meme_id]["dislikes"] += data.get("dislikes", 0)
                meme_trends[meme_id]["days"] += 1
    
    # Вычисляем средний скор и сортируем
    for meme_id, data in meme_trends.items():
        if data["days"] > 0:
            data["score"] = int(data["score"] / data["days"])
    
    sorted_trends = sorted(
        meme_trends.items(),
        key=lambda x: x[1]["score"],
        reverse=True
    )
    
    # Форматируем результат
    result = []
    for meme_id, data in sorted_trends[:limit]:
        result.append({
            "meme_id": meme_id,
            "likes": data["likes"],
            "dislikes": data["dislikes"],
            "trend_score": data["score"],
            "days_in_trend": data["days"]
        })
    
    return result

def get_user_engagement_stats() -> Dict:
    """
    Возвращает статистику вовлеченности пользователей
    
    Returns:
        Dict: Словарь со статистикой вовлеченности
    """
    now = time.time()
    
    # Определяем периоды активности
    day_active = 0
    week_active = 0
    month_active = 0
    regular_users = 0  # Пользователи с >10 оценками
    
    for user_id, data in user_activity.items():
        last_active = data.get("last_active", 0)
        if now - last_active < DAY_SECONDS:
            day_active += 1
        if now - last_active < WEEK_SECONDS:
            week_active += 1
        if now - last_active < DAY_SECONDS * 30:
            month_active += 1
        if data.get("ratings", 0) > 10:
            regular_users += 1
    
    return {
        "active_today": day_active,
        "active_week": week_active,
        "active_month": month_active,
        "regular_users": regular_users,
        "total_users": len(user_activity),
        "total_ratings": session_stats.get("total_ratings", 0),
        "today_ratings": session_stats.get("today_ratings", 0),
        "total_sessions": session_stats.get("total_sessions", 0)
    }

def get_meme_stats(meme_id: str) -> Dict:
    """
    Возвращает подробную статистику по конкретному мему
    
    Args:
        meme_id (str): Идентификатор мема
    
    Returns:
        Dict: Словарь со статистикой мема
    """
    if meme_id not in popular_memes:
        return {
            "meme_id": meme_id,
            "views": 0,
            "likes": 0,
            "dislikes": 0,
            "popularity_score": 0,
            "last_interaction": 0,
            "rating_percentage": 0,
            "trend_position": None
        }
    
    data = popular_memes[meme_id]
    views = data.get("views", 0)
    likes = data.get("likes", 0)
    dislikes = data.get("dislikes", 0)
    
    # Рассчитываем процент положительных оценок
    total_ratings = likes + dislikes
    rating_percentage = (likes / total_ratings * 100) if total_ratings > 0 else 0
    
    # Определяем позицию в трендах
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    trend_position = None
    
    if today in trending_memes and meme_id in trending_memes[today]:
        # Получаем все мемы дня, сортированные по тренду
        sorted_trends = sorted(
            trending_memes[today].items(),
            key=lambda x: x[1]["score"],
            reverse=True
        )
        
        # Ищем позицию нашего мема
        for i, (id, _) in enumerate(sorted_trends):
            if id == meme_id:
                trend_position = i + 1  # позиция начиная с 1
                break
    
    return {
        "meme_id": meme_id,
        "views": views,
        "likes": likes,
        "dislikes": dislikes,
        "popularity_score": _calculate_popularity_score(data),
        "last_interaction": data.get("last_interaction", 0),
        "rating_percentage": rating_percentage,
        "trend_position": trend_position
    }

def _calculate_popularity_score(meme_data: Dict) -> float:
    """
    Вычисляет числовую оценку популярности мема от 0 до 100
    
    Args:
        meme_data (Dict): Данные о меме
    
    Returns:
        float: Числовая оценка популярности от 0 до 100
    """
    views = meme_data.get("views", 0)
    likes = meme_data.get("likes", 0)
    dislikes = meme_data.get("dislikes", 0)
    
    if views == 0:
        return 0
    
    # Базовая формула: (лайки - дизлайки) / просмотры + фактор для количества просмотров
    view_factor = min(1, views / 100)  # Достигает максимума при 100+ просмотрах
    
    raw_score = ((likes - dislikes) / views + 1) * 50  # от 0 до 100
    
    # Умножаем на фактор просмотров чтобы отдавать предпочтение мемам с большим количеством взаимодействий
    adjusted_score = raw_score * (0.5 + 0.5 * view_factor)
    
    return max(0, min(100, adjusted_score))  # Ограничиваем значениями от 0 до 100