#!/usr/bin/env python3
"""
Модуль для фильтрации рекламного и нежелательного контента в мемах
"""
import logging
import re

# Настройка логирования
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Список тегов, которые должны отсутствовать в меме, чтобы его показывать
BLOCKED_CONTENT_TAGS = [
    # Спорт и фитнес
    "реклама", "телефон", "объявление", "sale", "спортзал", "фитоняшка",
    
    # Маникюр и бьюти
    "nail", "маникюр", "ногти", "nail art",
    
    # Доставка еды
    "доставка", "роллы", "суши", "пицца", "ресторан",
    
    # Праздники и акции
    "новый год", "подарки", "скидки", "акция", "sale",
    
    # Новости и политика
    "новости", "политика", "события", "происшествия", "news", "politics",
    "event", "incident", "журналист", "репортаж",
]

# Список строк для проверки URL изображений на нежелательный контент
BLOCKED_URL_PATTERNS = [
    "новости", "news", "politics", "event", "incident", "sale", "акци", "скидк"
]

# Список текстов, которые указывают на рекламный или новостной контент
BLOCKED_TEXT_PATTERNS = [
    "последние новости", "срочные новости", "новости дня", "политические события",
    "происшествие", "события в мире", "новостной канал", "репортаж", "журналист",
    "доставка", "купить", "акция", "скидка", "цена", "закажи"
]

# Специальные изображения, которые нужно отфильтровать
SPECIFIC_BLOCKED_IMAGES = [
    "news", "новости", "breaking-news", "sponsor", "реклама", "promo"
]

def check_for_specific_ad_images(image_url, text=None):
    """
    Проверяет, является ли изображение одним из конкретных рекламных или новостных изображений
    """
    url = image_url.lower() if image_url else ""
    text_content = text.lower() if text else ""
    
    news_markers = ["новости", "news", "breaking-news"]
    if any(marker in url for marker in news_markers) or any(marker in text_content for marker in news_markers):
        logger.info(f"Мем отфильтрован: содержит новостной контент (URL: {url}, Text: {text_content[:50]})")
        return True
    
    return False

def is_suitable_meme(meme):
    """
    Проверяет, подходит ли мем для показа пользователю
    """
    try:
        image_url = meme.get("image_url", "").lower() if "image_url" in meme else ""
        text = meme.get("text", "").lower() if "text" in meme else ""
        
        # Проверяем, что мем связан с офисной тематикой или юморным контентом
        office_keywords = [
            "офис", "работа", "коллеги", "работяги", "будни", "корпоратив",
            "начальник", "собеседование", "зарплата", "переговорка", "планёрка",
            "документы", "отчёты", "соцпакет", "перерыв", "кофе", "принтер",
            "email", "собрание", "deadline", "отпуск", "тайм-менеджмент",
            "монтаж", "монтировщик", "шутка", "юмор", "смешно", "с 1 мая"
        ]
        is_office_related = any(keyword in text for keyword in office_keywords) or not any(pattern in text for pattern in BLOCKED_TEXT_PATTERNS)
        if not is_office_related:
            logger.info(f"Мем отфильтрован: не связан с офисной тематикой (Text: {text[:50]})")
            return False
        
        if image_url and check_for_specific_ad_images(image_url, text):
            return False
        
        if "tags" in meme and isinstance(meme["tags"], list):
            for tag in meme["tags"]:
                if any(blocked_tag.lower() in tag.lower() for blocked_tag in BLOCKED_CONTENT_TAGS):
                    logger.info(f"Мем отфильтрован по тегу: {tag}")
                    return False
        
        if image_url:
            for pattern in BLOCKED_URL_PATTERNS:
                if pattern.lower() in image_url:
                    logger.info(f"Мем отфильтрован по URL изображения (найдено '{pattern}')")
                    return False
        
        if text:
            for pattern in BLOCKED_TEXT_PATTERNS:
                if pattern.lower() in text:
                    logger.info(f"Мем отфильтрован по тексту (найдено '{pattern}')")
                    return False
            
            ad_patterns = [
                r'новост[иь]', r'политик[аи]', r'событи[яй]', r'происшестви[яе]',
                r'доставк[аи]', r'куп[иь]\b', r'акци[яи]', r'скидк[аи]'
            ]
            for pattern in ad_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    logger.info(f"Мем отфильтрован по регулярному выражению в тексте: {pattern}")
                    return False
        
        return True
    
    except Exception as e:
        logger.error(f"Ошибка при фильтрации мема: {e}")
        return False
