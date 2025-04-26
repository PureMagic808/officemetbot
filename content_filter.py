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
    "спорт",
    "реклама",
    "телефон",
    "объявление",
    "фитнес",
    "тренировка", 
    "тренер",
    "тренируйся",
    "тренируйся вместе с нами",
    "gym",
    "workout",
    "sale",
    "спортзал",
    "фитоняшка",
    "гантели",
    "тренажерный",
    "фитнес клуб",
    
    # Маникюр и бьюти-индустрия
    "nail",
    "nail artist",
    "маникюр",
    "ногти",
    "nail art",
    "beauty",
    "салон",
    "салон красоты",
    "мастер",
    "nail master",
    "irina",
    "emelyanova",
    "мастер маникюра",
    "дизайн ногтей",
    "nail design",
    
    # Доставка еды
    "доставка",
    "роллы",
    "суши",
    "доставка роллов",
    "доставка суши",
    "угорь",
    "пицца",
    "доставка пиццы",
    "доставка еды",
    "chef",
    "шеф",
    "повар",
    "ресторан",
    "меню",
    
    # Праздники и акции
    "новогодний",
    "новый год",
    "елка",
    "подарки", 
    "скидки",
    "студент",
    "student",
    "artist",
    "акция",
    "предложение",
    "sale",
    "скидка",
    "распродажа"
]

DEFAULT_ERROR_IMAGE = "https://i.imgur.com/8KBR1h3.jpg"  # Замените на URL картинки с надписью "Извините, произошла ошибка"
DEFAULT_ERROR_TEXT = "Извините, не удалось загрузить подходящий мем. Попробуем другой!"

# Список строк для проверки URL изображений на нежелательный контент
BLOCKED_URL_PATTERNS = [
    # Спорт и фитнес
    "тренируйся", 
    "фитнес", 
    "трен", 
    "fitness", 
    "gym", 
    "sport",
    "workout",
    "гантел",
    "dumbbells",
    "спортзал",
    "зал",
    "упражнен",
    "exercise",
    
    # Маникюр и бьюти
    "nail", 
    "маникюр",
    "ногти",
    "beauty",
    "салон",
    "artist",
    "emelyanova",
    "irina",
    "ирина",
    "емельянова",
    "мастер",
    "master",
    
    # Реклама и акции
    "sale",
    "акци",
    "скидк",
    "магаз",
    "цена",
    "купить",
    "купи",
    "закажи",
    "заказать",
    "promo",
    "промо",
    
    # Праздники
    "новый_год",
    "новогод",
    "елка",
    "подарк",
    "снежинк",
    "gift",
    "presents",
    
    # Доставка еды
    "доставка",
    "роллы",
    "суши",
    "sushi",
    "угорь",
    "пицца",
    "pizza",
    "chef",
    "повар",
    "ресторан",
    "меню"
]

# Список текстов, которые указывают на рекламный контент
BLOCKED_TEXT_PATTERNS = [
    # Спорт и фитнес
    "тренируйся вместе с нами",
    "тренируйся",
    "фитнес",
    "спортзал",
    "фитоняшка",
    "гантели",
    "тренажерный",
    "фитнес клуб",
    "упражнения",
    "зал",
    "тренер",
    "тренировки",
    
    # Маникюр и бьюти
    "nail artist",
    "маникюр",
    "ногти",
    "салон",
    "beauty",
    "красота",
    "irina emelyanova",
    "ирина емельянова",
    "дизайн ногтей",
    
    # Реклама и акции
    "купить",
    "акция",
    "скидк",
    "цена",
    "закажи",
    "закажите",
    "предложение",
    "закажи сейчас",
    "только сегодня",
    "только до",
    "магазин",
    "продажа",
    "узнай больше",
    "дешево",
    "выгодно",
    "рассрочка",
    
    # Доставка еды
    "доставка роллов",
    "доставка суши",
    "доставка пиццы",
    "доставка еды",
    "ресторан",
    "меню",
    "угорь чторру",
    "шеф"
]

# Специальные изображения, которые нужно отфильтровать
# Эти хэши или фрагменты URL изображений гарантированно блокируются
SPECIFIC_BLOCKED_IMAGES = [
    # Фитнес-реклама с тренировками
    "тренируйся-вместе-с-нами",
    "train-with-us",
    "fitness-promo",
    "workout-ad",
    "фитнес-клуб",
    "спортзал-реклама",
    "тренировка",
    "гантели",
    "fitness",
    "dumbbells",
    "exercise",
    "new-year-fitness",
    "новогодний-фитнес",
    "pink-dumbbells",
    "розовые-гантели",
    
    # Маникюр и красота
    "irina-emelyanova", 
    "emelyanova-nail",
    "nail-artist",
    "маникюр-мастер",
    "beauty-salon",
    "салон-красоты",
    "irina",
    "emelyanova",
    "ирина",
    "емельянова",
    "маникюр",
    "ногти",
    "nail-design",
    "nail-art",
    "мастер-маникюра",
    "pink-nail",
    "розовый-фон",
    "розовый-маникюр",
    
    # Доставка еды
    "доставка-роллов-угорь",
    "sushi-delivery",
    "чторру",
    "доставка-роллов",
    "доставка-суши",
    "суши-доставка",
    "роллы-доставка",
    "угорь",
    "суши",
    "роллы",
    "sushi",
    "доставка-пиццы",
    "пицца",
    "доставка-еды",
    "еда-на-дом",
    "рыба-повар",
    "рыба-шеф",
    "fish-chef",
    "chef-sushi"
]

# Характерные маркеры для конкретных рекламных изображений
FITNESS_AD_MARKERS = ["розовые гантели", "новогодний", "фитнес", "спортзал", "тренировка"]
NAIL_ART_MARKERS = ["розовый фон", "емельянова", "маникюр", "nail artist", "irina"]
SUSHI_DELIVERY_MARKERS = ["рыба", "шеф", "повар", "роллы", "суши", "доставка", "угорь", "чторру"]

def check_for_specific_ad_images(image_url, text=None):
    """
    Проверяет, является ли изображение одним из конкретных рекламных изображений,
    которые нужно блокировать (например, показанных пользователем)
    
    Args:
        image_url (str): URL изображения
        text (str, optional): Текст, связанный с изображением
    
    Returns:
        bool: True если изображение является рекламным, False если нет
    """
    url = image_url.lower() if image_url else ""
    text_content = text.lower() if text else ""
    
    # Проверка на рекламные изображения с тренировками и фитнесом
    fitness_markers = [
        "розовые гантели", "розовые-гантели", "гантели розовые", 
        "тренируйся вместе с нами", "тренируйся-вместе-с-нами",
        "новогод", "елка", "елочные", "фитнес", "спортзал", "тренировка"
    ]
    
    # Этот блок специально для первого изображения с розовыми гантелями и елкой
    if any(marker in url for marker in fitness_markers) or any(marker in text_content for marker in fitness_markers):
        # Дополнительная проверка на наличие новогодних элементов и гантелей
        if (("ганте" in url or "dumbbells" in url) and 
            ("новогод" in url or "елк" in url or "елоч" in url)):
            logger.info("Мем отфильтрован: содержит изображение гантелей с новогодним оформлением")
            return True
            
        # Проверка на фразу "тренируйся вместе с нами"
        if "тренируйся вместе с нами" in text_content or "тренируйся-вместе-с-нами" in url:
            logger.info("Мем отфильтрован: содержит текст 'тренируйся вместе с нами'")
            return True
    
    # Проверка на рекламу маникюра и nail artist
    nail_markers = [
        "irina", "emelyanova", "ирина", "емельянова", 
        "nail artist", "nail-artist", "маникюр", "ногти",
        "розовый фон", "розовый-фон", "nail design"
    ]
    
    # Этот блок специально для второго изображения с рекламой маникюра
    if any(marker in url for marker in nail_markers) or any(marker in text_content for marker in nail_markers):
        # Проверка на характерные элементы визитки мастера маникюра
        if (("irina" in url or "ирина" in url) and 
            ("emelyanova" in url or "емельянова" in url)):
            logger.info("Мем отфильтрован: содержит рекламу мастера маникюра Ирины Емельяновой")
            return True
            
        # Проверка на розовый фон с золотыми элементами
        if "розовый" in url and ("маникюр" in url or "nail" in url):
            logger.info("Мем отфильтрован: содержит рекламу маникюра на розовом фоне")
            return True
    
    # Проверка на доставку еды (суши, роллы, рыба-повар)
    food_markers = [
        "доставка роллов", "доставка-роллов", "суши", "роллы",
        "чторру", "угорь", "рыба", "повар", "шеф"
    ]
    
    # Этот блок специально для третьего изображения с доставкой еды
    if any(marker in url for marker in food_markers) or any(marker in text_content for marker in food_markers):
        # Проверка на характерные элементы логотипа доставки суши
        if (("рыба" in url or "fish" in url) and 
            ("повар" in url or "шеф" in url or "chef" in url)):
            logger.info("Мем отфильтрован: содержит логотип доставки суши с рыбой-поваром")
            return True
            
        if "доставка" in text_content and ("ролл" in text_content or "суши" in text_content):
            logger.info("Мем отфильтрован: содержит текст о доставке суши или роллов")
            return True
    
    return False

def is_suitable_meme(meme):
    """
    Проверяет, подходит ли мем для показа пользователю
    Отфильтровывает рекламные, спортивные мемы и другой нежелательный контент
    
    Args:
        meme (dict): Словарь с информацией о меме (текст, изображение, теги и т.д.)
        
    Returns:
        bool: True если мем подходит для показа, False если нет
    """
    try:
        # Получение основных данных мема
        image_url = meme.get("image_url", "").lower() if "image_url" in meme else ""
        text = meme.get("text", "").lower() if "text" in meme else ""
        
        # Проверка на конкретные примеры рекламных изображений
        if image_url:
            # Первая специальная проверка на конкретные рекламные изображения
            if check_for_specific_ad_images(image_url, text):
                return False
        
        # Проверка на совпадение с запрещенными тегами
        if "tags" in meme and isinstance(meme["tags"], list):
            for tag in meme["tags"]:
                if any(blocked_tag.lower() in tag.lower() for blocked_tag in BLOCKED_CONTENT_TAGS):
                    logger.info(f"Мем отфильтрован по тегу: {tag}")
                    return False
        
        # Стандартная проверка URL изображения
        if image_url:
            # Проверка на конкретные рекламные изображения, которые нужно блокировать
            for specific_image in SPECIFIC_BLOCKED_IMAGES:
                if specific_image.lower() in image_url:
                    logger.info(f"Мем отфильтрован по совпадению с конкретным рекламным изображением: {specific_image}")
                    return False
            
            # Общая проверка по заблокированным паттернам URL
            for pattern in BLOCKED_URL_PATTERNS:
                if pattern.lower() in image_url:
                    logger.info(f"Мем отфильтрован по URL изображения (найдено '{pattern}')")
                    return False
        
        # Проверка текста мема
        if text:
            # Блокировка по ключевым фразам из конкретных примеров
            if "тренируйся вместе с нами" in text:
                logger.info("Мем отфильтрован: содержит текст 'тренируйся вместе с нами'")
                return False
                
            if "nail artist" in text or "ирина емельянова" in text or "irina emelyanova" in text:
                logger.info("Мем отфильтрован: содержит текст о nail artist")
                return False
                
            if "доставка роллов угорь чторру" in text:
                logger.info("Мем отфильтрован: содержит текст о доставке еды")
                return False
            
            # Проверка на точные совпадения с запрещенными паттернами
            for pattern in BLOCKED_TEXT_PATTERNS:
                if pattern.lower() in text:
                    logger.info(f"Мем отфильтрован по тексту (найдено '{pattern}')")
                    return False
            
            # Дополнительная проверка на рекламные фразы с использованием регулярных выражений
            ad_patterns = [
                # Покупка
                r'купи[т][ье]?\b',  # Купи, купите и т.д.
                r'закажи[т][ье]?\b',  # Закажи, закажите и т.д.
                r'\bцена\b',  # Цена
                r'руб\.?',  # Рубли (любая форма)
                r'\d+%\s+скидка',  # Проценты скидки
                r'акци[яи]',  # Акция, акции
                r'только\s+(сегодня|до\s+\d+)',  # "Только сегодня", "только до ..."
                
                # Спорт и фитнес
                r'спортзал',  # Спортзал
                r'тренировк[аи]',  # Тренировка, тренировки
                r'трениру[ей]',  # Тренируй, тренируем и т.д.
                r'фитнес',  # Фитнес
                r'гантел[иь]',  # Гантели
                r'зал[еа]?',  # Зал
                
                # Маникюр и красота
                r'маникюр',  # Маникюр
                r'ногт[ие]',  # Ногти
                r'дизайн\s+ногт',  # Дизайн ногтей
                r'салон',  # Салон
                r'красот[аы]',  # Красота
                r'nail\s+art',  # Nail art
                
                # Доставка еды
                r'доставк[аи]',  # Доставка
                r'ролл[ыов]',  # Роллы
                r'суши',  # Суши
                r'пицц[аы]',  # Пицца
                r'ресторан',  # Ресторан
                r'угорь',  # Угорь
                r'меню'  # Меню
            ]
            
            for pattern in ad_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    logger.info(f"Мем отфильтрован по регулярному выражению в тексте: {pattern}")
                    return False
        
        # Проверка метаданных изображения (если они есть)
        if "metadata" in meme and isinstance(meme["metadata"], dict):
            metadata = meme["metadata"]
            
            # Проверка заголовка
            if "title" in metadata and metadata["title"]:
                title = metadata["title"].lower()
                for pattern in BLOCKED_TEXT_PATTERNS:
                    if pattern.lower() in title:
                        logger.info(f"Мем отфильтрован по заголовку метаданных (найдено '{pattern}')")
                        return False
            
            # Проверка описания
            if "description" in metadata and metadata["description"]:
                description = metadata["description"].lower()
                for pattern in BLOCKED_TEXT_PATTERNS:
                    if pattern.lower() in description:
                        logger.info(f"Мем отфильтрован по описанию метаданных (найдено '{pattern}')")
                        return False
        
        # Если прошел все проверки, значит мем подходит
        return True
    
    except Exception as e:
        logger.error(f"Ошибка при фильтрации мема: {e}")
        # В случае ошибки лучше считать, что мем не подходит
        return False