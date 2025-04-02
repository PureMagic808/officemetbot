#!/usr/bin/env python3
"""
Модуль рекомендательной системы для персонализированной подборки мемов.
Анализирует оценки пользователя и рекомендует мемы на основе его предпочтений.
"""
import logging
import random
import json
import os
from collections import defaultdict
import re
from typing import Dict, List, Set, Tuple, Optional, Any

# Настройка логирования
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Константы для рекомендательной системы
MIN_RATINGS_FOR_RECOMMENDATIONS = 5  # Минимальное количество оценок для начала рекомендаций
MAX_KEYWORDS_PER_MEME = 15          # Максимальное количество ключевых слов для извлечения из мема
RECOMMENDATION_BOOST = 0.5          # Коэффициент усиления рекомендаций
SIMILARITY_THRESHOLD = 0.2          # Порог схожести для рекомендаций
USER_PREFERENCES_FILE = "user_preferences.json"  # Файл для сохранения предпочтений пользователей

# Словарь для хранения предпочтений пользователей
user_preferences = {}

# Словарь для кэширования извлеченных ключевых слов мемов
meme_keywords_cache = {}

# Стоп-слова для фильтрации при извлечении ключевых слов (русские и английские)
STOP_WORDS = {
    "и", "в", "на", "с", "по", "у", "к", "от", "за", "из", "о", "же", "ну", "а", "но", "да", "не", 
    "то", "что", "как", "так", "для", "или", "это", "вот", "ты", "он", "она", "оно", "они", "мы", 
    "вы", "я", "его", "её", "их", "наш", "ваш", "мой", "свой", "этот", "тот", "там", "тут", "здесь",
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with", "by", "of", "from", 
    "about", "as", "it", "its", "this", "that", "these", "those", "is", "are", "was", "were", "be", 
    "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "shall", "should",
    "can", "could", "may", "might", "must", "ought", "i", "you", "he", "she", "they", "we", "me", 
    "him", "her", "them", "us", "my", "your", "his", "their", "our", "mine", "yours", "hers", "theirs", 
    "ours"
}

def load_preferences():
    """Загружает предпочтения пользователей из файла"""
    global user_preferences
    try:
        if os.path.exists(USER_PREFERENCES_FILE):
            with open(USER_PREFERENCES_FILE, 'r', encoding='utf-8') as f:
                user_preferences = json.load(f)
                logger.info(f"Загружены предпочтения для {len(user_preferences)} пользователей")
    except Exception as e:
        logger.error(f"Ошибка при загрузке предпочтений пользователей: {e}")

def save_preferences():
    """Сохраняет предпочтения пользователей в файл"""
    try:
        with open(USER_PREFERENCES_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_preferences, f, ensure_ascii=False, indent=2)
        logger.info(f"Сохранены предпочтения для {len(user_preferences)} пользователей")
    except Exception as e:
        logger.error(f"Ошибка при сохранении предпочтений пользователей: {e}")

def extract_keywords(text: str) -> List[str]:
    """Извлекает ключевые слова из текста, удаляя стоп-слова и знаки препинания"""
    if not text:
        return []
    
    # Приводим к нижнему регистру и удаляем лишние символы
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # Разбиваем на слова и удаляем стоп-слова
    words = text.split()
    keywords = [word for word in words if word not in STOP_WORDS and len(word) > 2]
    
    # Ограничиваем количество ключевых слов
    return keywords[:MAX_KEYWORDS_PER_MEME]

def get_meme_keywords(meme: Dict) -> List[str]:
    """
    Получает ключевые слова для мема, используя текст и теги.
    Кэширует результаты для улучшения производительности.
    """
    # Создаем уникальный идентификатор мема для кэширования
    meme_id = meme.get('id', '')
    if not meme_id and 'image_url' in meme:
        meme_id = str(hash(meme['image_url']))
    
    # Если ключевые слова уже в кэше, возвращаем их
    if meme_id in meme_keywords_cache:
        return meme_keywords_cache[meme_id]
    
    keywords = []
    
    # Извлекаем ключевые слова из текста
    if 'text' in meme and meme['text']:
        text_keywords = extract_keywords(meme['text'])
        keywords.extend(text_keywords)
    
    # Добавляем теги как ключевые слова
    if 'tags' in meme and isinstance(meme['tags'], list):
        for tag in meme['tags']:
            tag_keywords = extract_keywords(tag)
            keywords.extend(tag_keywords)
            # Также добавляем сам тег, если он не в стоп-словах
            if tag.lower() not in STOP_WORDS and len(tag) > 2:
                keywords.append(tag.lower())
    
    # Удаляем дубликаты
    unique_keywords = list(set(keywords))
    
    # Кэшируем результат
    meme_keywords_cache[meme_id] = unique_keywords
    
    return unique_keywords

def calculate_meme_similarity(meme1: Dict, meme2: Dict) -> float:
    """
    Рассчитывает коэффициент сходства между двумя мемами на основе ключевых слов.
    Возвращает значение от 0.0 до 1.0, где 1.0 - полное совпадение.
    """
    keywords1 = set(get_meme_keywords(meme1))
    keywords2 = set(get_meme_keywords(meme2))
    
    if not keywords1 or not keywords2:
        return 0.0
    
    # Подсчитываем количество общих ключевых слов
    common_keywords = keywords1.intersection(keywords2)
    
    # Используем коэффициент Жаккара для определения сходства
    similarity = len(common_keywords) / len(keywords1.union(keywords2))
    
    return similarity

def update_user_preferences(user_id: int, meme: Dict, rating: int):
    """
    Обновляет предпочтения пользователя на основе оцененного мема.
    
    Args:
        user_id (int): ID пользователя
        meme (Dict): Данные мема
        rating (int): Оценка (1 - положительная, -1 - отрицательная)
    """
    # Преобразуем ID пользователя в строку для JSON
    user_id_str = str(user_id)
    
    # Инициализируем предпочтения пользователя, если их еще нет
    if user_id_str not in user_preferences:
        user_preferences[user_id_str] = {
            "liked_keywords": defaultdict(float),
            "disliked_keywords": defaultdict(float),
            "rated_memes": {},
            "total_ratings": 0
        }
    
    # Добавляем мем в историю оцененных
    meme_id = meme.get('id', '')
    if not meme_id and 'image_url' in meme:
        meme_id = str(hash(meme['image_url']))
    
    user_preferences[user_id_str]["rated_memes"][meme_id] = rating
    user_preferences[user_id_str]["total_ratings"] += 1
    
    # Получаем ключевые слова мема
    keywords = get_meme_keywords(meme)
    
    # Обновляем статистику ключевых слов
    weight = 1.0 / max(1, len(keywords))  # Вес, зависящий от количества ключевых слов
    
    if rating > 0:
        # Положительная оценка
        for keyword in keywords:
            user_preferences[user_id_str]["liked_keywords"][keyword] += weight
    else:
        # Отрицательная оценка
        for keyword in keywords:
            user_preferences[user_id_str]["disliked_keywords"][keyword] += weight
    
    # Сохраняем обновленные предпочтения
    save_preferences()

def get_recommendation_score(user_id: int, meme: Dict) -> float:
    """
    Рассчитывает рекомендательный рейтинг мема для конкретного пользователя.
    Высокий рейтинг означает, что мем с большей вероятностью понравится пользователю.
    
    Args:
        user_id (int): ID пользователя
        meme (Dict): Данные мема
    
    Returns:
        float: Рейтинг рекомендации (чем выше, тем лучше)
    """
    user_id_str = str(user_id)
    
    # Если нет предпочтений пользователя или недостаточно оценок, возвращаем нейтральный рейтинг
    if (user_id_str not in user_preferences or 
        user_preferences[user_id_str]["total_ratings"] < MIN_RATINGS_FOR_RECOMMENDATIONS):
        return 0.5  # Нейтральный рейтинг
    
    # Проверяем, не оценил ли пользователь этот мем ранее
    meme_id = meme.get('id', '')
    if not meme_id and 'image_url' in meme:
        meme_id = str(hash(meme['image_url']))
    
    rated_memes = user_preferences[user_id_str]["rated_memes"]
    if meme_id in rated_memes:
        # Если мем был оценен положительно, даем высокий рейтинг для повторного показа
        # Если отрицательно - низкий рейтинг
        return 0.9 if rated_memes[meme_id] > 0 else 0.1
    
    # Получаем ключевые слова мема
    keywords = get_meme_keywords(meme)
    
    # Если нет ключевых слов, возвращаем нейтральный рейтинг
    if not keywords:
        return 0.5
    
    # Получаем данные пользовательских предпочтений
    liked_keywords = user_preferences[user_id_str]["liked_keywords"]
    disliked_keywords = user_preferences[user_id_str]["disliked_keywords"]
    
    # Рассчитываем рейтинги на основе ключевых слов
    like_score = sum(liked_keywords.get(keyword, 0) for keyword in keywords)
    dislike_score = sum(disliked_keywords.get(keyword, 0) for keyword in keywords)
    
    # Нормализуем и комбинируем рейтинги
    total_score = like_score - dislike_score
    
    # Проверяем схожесть с ранее понравившимися мемами
    similarity_boost = 0
    
    # Перебираем ранее оцененные мемы пользователя
    for rated_meme_id, rating in rated_memes.items():
        # Рассматриваем только положительно оцененные мемы
        if rating <= 0:
            continue
        
        # Находим мем в коллекции по ID
        # Если мема нет в коллекции, пропускаем
        # В реальной системе здесь нужно будет доработать поиск мема по ID
        try:
            # Здесь предполагается, что можно получить мем по ID из какой-то коллекции
            # Так как у нас нет прямого доступа к коллекции здесь, данный блок будет реализован позже
            # rated_meme = get_meme_by_id(rated_meme_id)
            # similarity = calculate_meme_similarity(meme, rated_meme)
            # if similarity > SIMILARITY_THRESHOLD:
            #     similarity_boost += similarity * RECOMMENDATION_BOOST
            pass
        except:
            continue
    
    # Преобразуем итоговый рейтинг в диапазон [0,1]
    final_score = 0.5 + (total_score + similarity_boost) * 0.1
    final_score = max(0, min(1, final_score))  # Ограничиваем диапазоном [0,1]
    
    return final_score

def recommend_memes(user_id: int, memes_collection: Dict[str, Dict], count: int = 5) -> List[str]:
    """
    Рекомендует мемы для пользователя на основе его предпочтений.
    
    Args:
        user_id (int): ID пользователя
        memes_collection (Dict): Коллекция доступных мемов
        count (int): Количество мемов для рекомендации
    
    Returns:
        List[str]: Список ID рекомендованных мемов
    """
    user_id_str = str(user_id)
    
    # Если у пользователя недостаточно оценок, возвращаем случайные мемы
    if (user_id_str not in user_preferences or 
        user_preferences[user_id_str]["total_ratings"] < MIN_RATINGS_FOR_RECOMMENDATIONS):
        logger.info(f"Недостаточно оценок для персонализированных рекомендаций пользователю {user_id}")
        return random.sample(list(memes_collection.keys()), min(count, len(memes_collection)))
    
    # Вычисляем рейтинги рекомендаций для всех мемов
    recommendation_scores = {}
    
    for meme_id, meme in memes_collection.items():
        score = get_recommendation_score(user_id, meme)
        recommendation_scores[meme_id] = score
    
    # Сортируем мемы по рейтингу (от высокого к низкому)
    sorted_memes = sorted(recommendation_scores.items(), key=lambda x: x[1], reverse=True)
    
    # Выбираем топ-N мемов
    recommended_meme_ids = [meme_id for meme_id, score in sorted_memes[:count]]
    
    logger.info(f"Сгенерированы персонализированные рекомендации для пользователя {user_id}")
    return recommended_meme_ids

def get_user_preferences_stats(user_id: int) -> Dict:
    """
    Возвращает статистику предпочтений пользователя.
    
    Args:
        user_id (int): ID пользователя
    
    Returns:
        Dict: Статистика предпочтений
    """
    user_id_str = str(user_id)
    
    if user_id_str not in user_preferences:
        return {
            "total_ratings": 0,
            "liked_memes": 0,
            "disliked_memes": 0,
            "top_keywords": [],
            "has_recommendations": False
        }
    
    # Собираем статистику
    user_data = user_preferences[user_id_str]
    rated_memes = user_data["rated_memes"]
    liked_memes = sum(1 for rating in rated_memes.values() if rating > 0)
    disliked_memes = sum(1 for rating in rated_memes.values() if rating < 0)
    
    # Топ ключевых слов, которые нравятся пользователю
    liked_keywords = user_data["liked_keywords"]
    top_keywords = sorted(liked_keywords.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        "total_ratings": user_data["total_ratings"],
        "liked_memes": liked_memes,
        "disliked_memes": disliked_memes,
        "top_keywords": [keyword for keyword, _ in top_keywords],
        "has_recommendations": user_data["total_ratings"] >= MIN_RATINGS_FOR_RECOMMENDATIONS
    }

def analyze_user_history(user_id: int, memes_collection: Dict[str, Dict]) -> Dict:
    """
    Анализирует историю оценок пользователя и выявляет паттерны предпочтений.
    
    Args:
        user_id (int): ID пользователя
        memes_collection (Dict): Коллекция мемов
    
    Returns:
        Dict: Результаты анализа
    """
    user_id_str = str(user_id)
    
    if user_id_str not in user_preferences:
        return {
            "message": "Недостаточно данных для анализа",
            "recommendations": []
        }
    
    user_data = user_preferences[user_id_str]
    
    # Если недостаточно оценок, возвращаем базовое сообщение
    if user_data["total_ratings"] < MIN_RATINGS_FOR_RECOMMENDATIONS:
        return {
            "message": f"Для анализа нужно оценить как минимум {MIN_RATINGS_FOR_RECOMMENDATIONS} мемов",
            "recommendations": []
        }
    
    # Анализируем предпочитаемые категории мемов
    liked_keywords = user_data["liked_keywords"]
    top_keywords = sorted(liked_keywords.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Формируем рекомендательное сообщение
    keywords_text = ", ".join([keyword for keyword, _ in top_keywords])
    message = f"На основе ваших {user_data['total_ratings']} оценок, вам нравятся мемы со следующими темами: {keywords_text}."
    
    # Генерируем персонализированные рекомендации
    recommendations = recommend_memes(user_id, memes_collection, 5)
    
    return {
        "message": message,
        "top_keywords": [keyword for keyword, _ in top_keywords],
        "recommendations": recommendations
    }

# Инициализация модуля при импорте
load_preferences()