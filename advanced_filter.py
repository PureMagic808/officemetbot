#!/usr/bin/env python3
"""
Улучшенный модуль фильтрации с агрессивным блокированием рекламы.
Предназначен для полного устранения любых рекламных материалов.
"""
import logging
import re
import os
import hashlib
from urllib.parse import urlparse
import json

# Настройка логирования
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Пути к файлам для хранения списков заблокированных элементов
BLOCKED_IMAGES_CACHE = "blocked_images.json"
AD_SIGNATURES_CACHE = "ad_signatures.json"

# Словарь для хранения хэшей заблокированных изображений
blocked_image_hashes = set()

# Категории рекламных фильтров
ADVERTISING_PATTERNS = {
    "shopping": [
        "купить", "магазин", "скидк", "закажи", "закажите", "заказать", 
        "акция", "распродажа", "бесплатн", "дешево", "выгодно", 
        "рассрочка", "руб", "₽", "$", "скидк", "sale", "shop", "подарок", "выгода",
        "бесплатно", "товар", "доставка", "купон", "пром", "промо", "promo",
        "дисконт", "покупк", "заказ", "card", "карта", "банк",
        "промокод", "только до", "успей"
    ],
    "fitness": [
        "тренер", "тренировк", "фитнес", "спортзал", "гантели", "gym", 
        "workout", "фитоняшка", "фитнес", "тренажер", "зал", "упражнен", "пресс", 
        "фигур", "тело", "похуде", "диета", "exercise", "fitness", 
        "мышцы", "тренировки", "тренируйся", "кардио", "бассейн", "аквааэробика",
        "йога", "растяжка", "кроссфит", "crossfit", "тренажер", "абонемент",
        "stretching"
    ],
    "beauty": [
        "маникюр", "ногти", "педикюр", "салон", "nail", "beauty", 
        "мастер", "парикмахер", "стрижк", "окрашивание", "волосы", "hair", "make up", 
        "makeup", "визаж", "косметолог", "мейкап", "lash", "lashes", "ресницы", 
        "прядь", "прическ", "стилист", "стрижк", "эпиляция", "массаж",
        "молодость", "anti-age", "омоложение", "spa", "спа",
        "esthetic", "эстетик"
    ],
    "food_delivery": [
        "доставка", "роллы", "суши", "пицца", "шеф", "повар", "ресторан", "меню", 
        "кухня", "кафе", "еда", "заказать еду", "блюдо", "готовка", "рецепт", 
        "taste", "вкус", "sushi", "pizza", "chef", "food", "meal", 
        "бизнес-ланч", "бургер", "фастфуд", "экспресс-доставка", 
        "японская кухня", "китайская кухня", "итальянская", "суши сет", "роллы сет",
        "угорь", "лосось", "деликатес", "гастроном", "вок", "wok"
    ],
    "clothing": [
        "одежда", "обувь", "платье", "футболка", "джинсы", "юбка", 
        "куртка", "пальто", "шуба", "сумка", "аксессуар", "fashion", "мода", 
        "бренд", "brand", "коллекция", "clothes", "wear", 
        "наряд", "образ", "лук", "look", "shopping", 
        "шоппинг", "тренд", "тренды", "аутлет", "outlet", "sale", "сезон"
    ],
    "real_estate": [
        "недвижимость", "квартира", "участок", "помещение", 
        "аренда", "сдам", "сдаю", "сниму", "продам", "продаю", "риэлтор", 
        "застройщик", "новостройка", "ремонт", "отделка", "ипотека", "кредит", 
        "рассрочка", "жилой комплекс", "жк", "апартаменты", "студия",
        "real estate", "property", "flat", "rent", "mortgage", "credit"
    ],
    "education": [
        "курсы", "обучение", "образование", "тренинг", "семинар", "вебинар", 
        "мастер-класс", "мк", "school", "институт", "университет", 
        "колледж", "академия", "набор", "препод", "учитель", "ученик", 
        "студент", "онлайн курс", "диплом", "сертификат"
    ],
    "travel": [
        "путешествие", "отдых", "отель", "гостиница", "билеты", "авиа", 
        "самолет", "поезд", "круиз", "экскурсия", "travel", "trip", "курорт", 
        "море", "горы", "пляж", "beach", "sea", "горящие туры", "last minute", 
        "виза", "бронирование", "booking", "all inclusive"
    ],
    "events": [
        "концерт", "фестиваль", "шоу", "выставка", "спектакль", "кино", "театр", 
        "билеты", "афиша", "event", "мероприятие", "вечеринка", "party", 
        "презентация", "премьера", "открытие", "гала", "церемония", "праздник"
    ]
}

# Объединяем все шаблоны в один список
ALL_BLOCKED_PATTERNS = []
for category, patterns in ADVERTISING_PATTERNS.items():
    ALL_BLOCKED_PATTERNS.extend(patterns)

# Удаляем дубликаты
ALL_BLOCKED_PATTERNS = list(set(ALL_BLOCKED_PATTERNS))

# Изображения на проверку 
SPECIFIC_BLOCKED_IMAGES = [
    # Рекламные изображения для гарантированной блокировки
    # Фитнес
    "тренируйся-вместе-с-нами", "train-with-us", "fitness-promo", "workout-ad",
    "фитнес-клуб", "тренировка", "гантели", "fitness", "dumbbells", "exercise",
    "new-year-fitness", "новогодний-фитнес", "pink-dumbbells", "розовые-гантели",
    # Маникюр 
    "irina-emelyanova", "emelyanova-nail", "nail-artist", "маникюр-мастер",
    "beauty-salon", "салон-красоты", "маникюр", "ногти", "nail-design", "nail-art",
    # Еда
    "доставка-роллов", "sushi-delivery", "чторру", "доставка-суши", "суши-доставка",
    "роллы-доставка", "доставка-пиццы", "доставка-еды", "еда-на-дом", 
    "рыба-повар", "рыба-шеф", "fish-chef", "chef-sushi",
    # Общее
    "reklama", "реклама", "ad-", "advert-"
]

# Расширенные маркеры по категориям для более точного определения контента
EXTENDED_MARKERS = {
    "fitness": [
        "розовые гантели", "новогодний", "фитнес", "спортзал", "тренировка",
        "тренажер", "тренажерный зал", "абонемент", "персональный тренер",
        "групповые тренировки", "кроссфит", "кардио", "силовые", "stretching"
    ],
    "nail_art": [
        "розовый фон", "емельянова", "маникюр", "nail artist", "irina",
        "дизайн ногтей", "nail master", "мастер ногтевого сервиса", "педикюр",
        "наращивание ногтей", "гель-лак", "shellac", "шеллак", "маникюрный салон"
    ],
    "food_delivery": [
        "рыба", "шеф", "повар", "роллы", "суши", "доставка", "угорь", "чторру",
        "пицца", "еда на дом", "скидка на доставку", "бесплатная доставка",
        "японская кухня", "китайская кухня", "европейская кухня", "итальянская"
    ],
    "clothing": [
        "новая коллекция", "скидки до", "распродажа", "sale", "модные тренды",
        "стильные", "бренд", "дизайнер", "одежда", "обувь", "аксессуары",
        "сумки", "платья", "костюмы", "premium", "люкс", "outlet"
    ],
    "real_estate": [
        "новый жилой комплекс", "квартиры от застройщика", "ипотека", "рассрочка",
        "первоначальный взнос", "новостройка", "жилой комплекс", "апартаменты",
        "коммерческая недвижимость", "офисы", "выгодные условия", "скидка"
    ]
}

def load_blocked_lists():
    """Загружает списки заблокированных элементов из файлов"""
    global blocked_image_hashes
    
    try:
        if os.path.exists(BLOCKED_IMAGES_CACHE):
            with open(BLOCKED_IMAGES_CACHE, 'r', encoding='utf-8') as f:
                loaded_hashes = json.load(f)
                if loaded_hashes and isinstance(loaded_hashes, list):
                    blocked_image_hashes = set(loaded_hashes)
                    logger.info(f"Загружено {len(blocked_image_hashes)} хэшей заблокированных изображений")
    except Exception as e:
        logger.error(f"Ошибка при загрузке списков заблокированных элементов: {e}")

def save_blocked_lists():
    """Сохраняет списки заблокированных элементов в файлы"""
    try:
        with open(BLOCKED_IMAGES_CACHE, 'w', encoding='utf-8') as f:
            json.dump(list(blocked_image_hashes), f, ensure_ascii=False, indent=2)
        logger.info(f"Сохранено {len(blocked_image_hashes)} хэшей заблокированных изображений")
    except Exception as e:
        logger.error(f"Ошибка при сохранении списков заблокированных элементов: {e}")

def compute_image_hash(image_url):
    """Вычисляет хэш изображения по URL"""
    return hashlib.md5(image_url.encode()).hexdigest()

def add_blocked_image(image_url):
    """Добавляет URL изображения в список заблокированных"""
    if not image_url:
        return
    
    image_hash = compute_image_hash(image_url)
    blocked_image_hashes.add(image_hash)
    save_blocked_lists()
    logger.info(f"Добавлено новое заблокированное изображение: {image_url[:50]}...")

def is_blocked_image(image_url):
    """Проверяет, заблокировано ли изображение по URL"""
    if not image_url:
        return False
    
    image_hash = compute_image_hash(image_url)
    return image_hash in blocked_image_hashes

def detect_advertisement_in_text(text):
    """
    Проверяет текст на наличие рекламных маркеров
    Возвращает (bool, str) - (найдена реклама?, причина)
    """
    if not text:
        return False, ""
    
    text = text.lower()
    
    # Проверка на ключевые фразы
    for pattern in ALL_BLOCKED_PATTERNS:
        if pattern.lower() in text:
            return True, f"найдено рекламное слово '{pattern}'"
    
    # Регулярные выражения для обнаружения рекламных шаблонов
    ad_regexes = [
        # Скидки, проценты
        r'\d+\s*%',  # 50%, 20 %, etc.
        r'скидк[аиу]?\s+до\s+\d+',  # скидка до 50
        r'до\s+-\d+\s*%',  # до -50%
        r'от\s+\d+\s*руб',  # от 100 руб
        r'всего\s+\d+\s*руб',  # всего 100 руб
        r'всего\s+за\s+\d+', # всего за 100
        r'цена\s*:?\s*\d+',  # цена: 100
        r'стоимость\s*:?\s*\d+',  # стоимость: 100
        r'руб\.|₽',  # руб. или символ рубля
        
        # Рекламные призывы
        r'звони[те]?',  # звони, звоните
        r'пиши[те]?',  # пиши, пишите
        r'заходи[те]?',  # заходи, заходите
        r'приходи[те]?',  # приходи, приходите
        r'спеши[те]?',  # спеши, спешите
        r'успей[те]?',  # успей, успейте
        r'закажи[те]?',  # закажи, закажите
        r'предлож[еи]ни[ея]',  # предложение, предложения
        r'выгодн[ыоеая]',  # выгодный, выгодно, выгодная
        r'подробн[ее]?',  # подробнее

        # Телефоны и контакты
        r'\+7\s*\(\d{3}\)\s*\d{3}[-\s]?\d{2}[-\s]?\d{2}',  # +7(123)456-78-90
        r'8\s*\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}',  # 8 123 456 78 90
        r'тел[\.\:]',  # тел. или тел:
        r'контакты\s*:',  # контакты:
        
        # Ссылки и онлайн-маркеры
        r'https?:\/\/',  # http:// или https://
        r'www\.',  # www.
        r'\.ru|\.com|\.net|\.org',  # .ru, .com, и т.д.
        r'онлайн',  # онлайн
        r'оф+ициальный сайт',  # официальный сайт
        r'подписыва[ея]тесь',  # подписывайтесь, подписывайтесь
        r'заказ[ат]ь\s+на\s+сайте',  # заказать на сайте
        
        # Маркетинговые фразы
        r'акци[яи]',  # акция, акции
        r'скидк[иа]',  # скидки, скидка
        r'распродаж[аи]',  # распродажа, распродажи
        r'спец\.?\s*предложени[ея]',  # спец.предложение, спец предложения
        r'количество ограничено',  # количество ограничено
        r'только\s+(сегодня|завтра|до\s+\d+)',  # только сегодня, только до 10
        r'дейтсву[еюя]т\s+до',  # действует до
        r'записыва[ей]тесь',  # записывайтесь, записывайтесь
        r'подробности\s+(по\s+телефону|на\s+сайте)',  # подробности по телефону, на сайте
        
        # Эмодзи, которые часто используются в рекламе
        r'💰|💲|💸|💵|💴|💶|💷',  # деньги
        r'🏷️|🏷|🔖|📝',  # ценники, бирки
        r'📲|📱|📞|☎️|📧|✉️',  # телефоны, контакты
        r'🛒|🛍️|🛍|🎁',  # покупки, подарки
    ]
    
    for regex in ad_regexes:
        match = re.search(regex, text, re.IGNORECASE)
        if match:
            return True, f"найден рекламный шаблон '{match.group(0)}'"
    
    return False, ""

def detect_advertisement_in_url(url):
    """
    Проверяет URL на наличие рекламных маркеров
    Возвращает (bool, str) - (найдена реклама?, причина)
    """
    if not url:
        return False, ""
    
    url = url.lower()
    
    # Проверка на конкретные заблокированные изображения
    for specific_image in SPECIFIC_BLOCKED_IMAGES:
        if specific_image.lower() in url:
            return True, f"URL содержит блокируемый паттерн: {specific_image}"
    
    # Проверка, находится ли URL в списке заблокированных
    if is_blocked_image(url):
        return True, "URL находится в списке заблокированных изображений"
    
    # Проверяем домен и путь на рекламные маркеры
    parsed_url = urlparse(url)
    domain_path = (parsed_url.netloc + parsed_url.path).lower()
    
    for pattern in ALL_BLOCKED_PATTERNS:
        if pattern.lower() in domain_path:
            return True, f"URL содержит рекламное слово: {pattern}"
    
    return False, ""

def detect_ad_category(item_data):
    """
    Определяет категорию рекламы, если контент похож на рекламу
    Возвращает (категория или None, уверенность 0-100)
    """
    if not item_data:
        return None, 0
    
    text = item_data.get("text", "").lower() if "text" in item_data else ""
    image_url = item_data.get("image_url", "").lower() if "image_url" in item_data else ""
    
    category_scores = {}
    
    # Проверяем текст по категориям
    for category, patterns in ADVERTISING_PATTERNS.items():
        score = 0
        for pattern in patterns:
            pattern_count = text.count(pattern)
            if pattern_count > 0:
                score += pattern_count * 10  # Базовый вес каждого совпадения
        
        # Дополнительные проверки на основе расширенных маркеров
        if category in EXTENDED_MARKERS:
            for marker in EXTENDED_MARKERS[category]:
                if marker in text:
                    score += 15  # Больший вес для специфичных маркеров категории
        
        # Проверка URL на маркеры категории
        for pattern in patterns:
            if pattern in image_url:
                score += 5  # Меньший вес для совпадений в URL
        
        category_scores[category] = score
    
    # Найти категорию с максимальным счетом
    max_category = max(category_scores.items(), key=lambda x: x[1]) if category_scores else (None, 0)
    
    # Вернуть категорию, только если счет превышает порог уверенности
    if max_category[1] >= 10:
        confidence = min(max_category[1], 100)  # Обрезаем до 100%
        return max_category[0], confidence
    
    return None, 0

def check_for_specific_ad_content(image_url, text=None):
    """
    Расширенная проверка на конкретные рекламные материалы
    Возвращает (bool, str) - (является рекламным?, причина)
    """
    if not image_url and not text:
        return False, ""
    
    url = image_url.lower() if image_url else ""
    text_content = text.lower() if text else ""
    
    # Проверка на рекламные изображения с тренировками и фитнесом
    for marker in EXTENDED_MARKERS["fitness"]:
        if marker in url or marker in text_content:
            return True, f"обнаружен маркер фитнес-рекламы: {marker}"
    
    # Проверка на рекламу маникюра и nail artist
    for marker in EXTENDED_MARKERS["nail_art"]:
        if marker in url or marker in text_content:
            return True, f"обнаружен маркер рекламы маникюра: {marker}"
    
    # Проверка на доставку еды
    for marker in EXTENDED_MARKERS["food_delivery"]:
        if marker in url or marker in text_content:
            return True, f"обнаружен маркер доставки еды: {marker}"
    
    # Проверка на одежду и магазины
    for marker in EXTENDED_MARKERS["clothing"]:
        if marker in url or marker in text_content:
            return True, f"обнаружен маркер магазина одежды: {marker}"
    
    # Проверка на недвижимость
    for marker in EXTENDED_MARKERS["real_estate"]:
        if marker in url or marker in text_content:
            return True, f"обнаружен маркер рекламы недвижимости: {marker}"
    
    return False, ""

def is_suitable_meme_advanced(meme):
    """
    Усовершенствованная проверка, подходит ли мем для показа пользователю.
    Отфильтровывает все виды рекламного контента агрессивным образом.
    
    Args:
        meme (dict): Словарь с информацией о меме (текст, изображение, теги и т.д.)
        
    Returns:
        bool: True если мем подходит для показа, False если нет
    """
    # Загружаем заблокированные списки, если они не загружены
    if not blocked_image_hashes:
        load_blocked_lists()
    
    try:
        # Получение основных данных мема
        image_url = meme.get("image_url", "").lower() if "image_url" in meme else ""
        text = meme.get("text", "").lower() if "text" in meme else ""
        
        # АГРЕССИВНАЯ ФИЛЬТРАЦИЯ: если текст отсутствует или слишком короткий
        if not text or len(text.split()) < 3:
            logger.info(f"Мем отфильтрован: отсутствует или слишком короткий текст (менее 3 слов)")
            return False
            
        # Проверка на религиозный контент (не связан с офисной тематикой)
        religious_keywords = [
            "христианск", "служени", "православ", "молитв", "церковь", "храм",
            "бог", "господ", "вера", "духовн", "религи", "святой", "священник",
            "проповед", "библи", "крещени", "грех", "исповед", "воскресени",
            "церемони", "ритуал", "поклонени", "патриарх", "монасты", "монах"
        ]
        
        # Если в тексте есть религиозные темы, это не офисный юмор
        for keyword in religious_keywords:
            if keyword in text:
                logger.info(f"Мем отфильтрован: содержит религиозную тематику ('{keyword}')")
                return False
                
        # Проверка на фото мужчин с татуировками (не подходит для темы)
        tattoo_keywords = ["тату", "татуировк", "татуха", "набит", "набивать"]
        for keyword in tattoo_keywords:
            if keyword in text:
                logger.info(f"Мем отфильтрован: содержит упоминание татуировок")
                return False
        
        # Первый уровень проверки: конкретные заблокированные изображения и текст
        is_ad, reason = check_for_specific_ad_content(image_url, text)
        if is_ad:
            logger.info(f"Мем отфильтрован: {reason}")
            return False
        
        # Второй уровень проверки: текст мема (более агрессивный)
        is_ad, reason = detect_advertisement_in_text(text)
        if is_ad:
            logger.info(f"Мем отфильтрован по тексту ({reason})")
            return False
            
        # Проверка на наличие ключевых слов в тексте мема
        # Расширенный список слов, связанных с офисным юмором и работой
        office_keywords = [
            "офис", "работа", "босс", "начальник", "коллега", "коллеги", 
            "сотрудник", "проект", "отпуск", "зарплата", "понедельник",
            "совещание", "собрание", "дедлайн", "срок", "пятница", "выходной",
            "чат", "корпоратив", "презентация", "отчет", "кофе", "перерыв",
            "кабинет", "стол", "компьютер", "документ", "программист",
            "менеджер", "отдел", "увольнение", "ставка", "резюме", "вакансия",
            "должность", "производительность", "эффективность", "будильник",
            "опоздание", "обед", "обеденный перерыв", "переработка", "команда",
            "бизнес", "клиент", "руководитель", "директор", "задача", "приказ",
            "финансы", "конкуренты", "расписание", "рабочий день", "смена", "бухгалтер"
        ]
        
        work_keywords = [
            "работать", "трудиться", "работаю", "работаем", "домой", "сижу", "сидим",
            "рабочий", "офисный", "устал", "не выспался", "компания", "корпорация",
            "фирма", "зарплату", "повышение", "аванс", "премия", "отгул", "выговор", 
            "переговоры", "бумаги", "придумать", "успеть", "отправить", "приём", 
            "посетитель", "командировка", "звонок", "график", "почта", "email",
            "выходные", "будни", "стресс", "профессия", "карьера"
        ]
        
        # Проверяем наличие ключевых слов офисной тематики
        def check_is_office_related(text):
            text_lower = text.lower()
            # Проверка на точное совпадение слов
            for keyword in office_keywords:
                if keyword in text_lower.split():
                    return True, keyword
                
            # Проверка на вхождение слов внутри текста
            for keyword in office_keywords:
                if keyword in text_lower:
                    return True, keyword
                    
            # Проверка на вхождение рабочих глаголов и прилагательных
            for keyword in work_keywords:
                if keyword in text_lower:
                    return True, keyword
            
            return False, ""
        
        # Проверяем, связан ли контент с офисной тематикой
        is_office_related, found_keyword = check_is_office_related(text)
        
        # Если это не офисный юмор, отклоняем мем
        if not is_office_related:
            logger.info(f"Мем отфильтрован: текст не содержит ключевых слов по тематике офиса/работы")
            return False
        
        # Третий уровень проверки: URL изображения
        if image_url:
            is_ad, reason = detect_advertisement_in_url(image_url)
            if is_ad:
                logger.info(f"Мем отфильтрован по URL ({reason})")
                return False
                
        # Проверка на наличие символов валют в тексте (₽, $, €, руб)
        currency_symbols = ["₽", "$", "€", "руб", "рубл", "dollar", "доллар", "евро"]
        if any(symbol in text for symbol in currency_symbols):
            logger.info(f"Мем отфильтрован: содержит символы валют/денег")
            return False
        
        # Четвертый уровень проверки: теги
        if "tags" in meme and isinstance(meme["tags"], list):
            # Список тегов, которые разрешены даже если они совпадают с рекламными
            allowed_tags = ["офис", "работа", "оффис", "босс", "начальник", "коллеги", "сотрудник"]
            
            # Дополнительная проверка: проверяем, есть ли хотя бы один тег из разрешенных
            has_allowed_tag = False
            for tag in meme["tags"]:
                if tag.lower() in allowed_tags:
                    has_allowed_tag = True
                    break
                    
            # Если нет ни одного разрешенного тега и при этом текст короткий - это подозрительно
            if not has_allowed_tag and text and len(text.split()) < 15:
                logger.info(f"Мем отфильтрован: не имеет тегов по тематике офиса")
                return False
            
            for tag in meme["tags"]:
                tag_text = tag.lower()
                
                # Если тег в списке разрешенных, пропускаем его
                if tag_text in allowed_tags:
                    continue
                
                # Проверка тегов на рекламные маркеры
                is_ad, reason = detect_advertisement_in_text(tag_text)
                if is_ad:
                    logger.info(f"Мем отфильтрован по тегу: {tag} ({reason})")
                    return False
        
        # Пятый уровень проверки: метаданные 
        if "metadata" in meme and isinstance(meme["metadata"], dict):
            metadata = meme["metadata"]
            
            # Проверка заголовка
            if "title" in metadata and metadata["title"]:
                is_ad, reason = detect_advertisement_in_text(metadata["title"])
                if is_ad:
                    logger.info(f"Мем отфильтрован по заголовку метаданных ({reason})")
                    return False
            
            # Проверка описания
            if "description" in metadata and metadata["description"]:
                is_ad, reason = detect_advertisement_in_text(metadata["description"])
                if is_ad:
                    logger.info(f"Мем отфильтрован по описанию метаданных ({reason})")
                    return False
        
        # Шестой уровень: категоризация рекламы (с более низким порогом)
        ad_category, confidence = detect_ad_category(meme)
        if ad_category and confidence > 20:  # Понизили порог с 30% до 20%
            logger.info(f"Мем отфильтрован: похож на рекламу категории '{ad_category}' с уверенностью {confidence}%")
            return False
            
        # Проверка на наличие слишком длинного текста без смысла
        if text and len(text.split()) > 50:
            # Длинные тексты часто бывают спамом или рекламой
            # Проверяем на повторение одинаковых слов или фраз
            words = text.split()
            word_count = {}
            for word in words:
                if len(word) > 3:  # Игнорируем короткие слова
                    word_count[word] = word_count.get(word, 0) + 1
                    
            # Если какое-то слово повторяется более 5 раз, это подозрительно
            for word, count in word_count.items():
                if count > 5:
                    logger.info(f"Мем отфильтрован: содержит повторяющееся слово '{word}' ({count} раз)")
                    return False
        
        # Если прошел все проверки, значит мем подходит
        return True
    
    except Exception as e:
        logger.error(f"Ошибка при фильтрации мема: {e}")
        # В случае ошибки лучше считать, что мем не подходит
        return False

# Инициализация модуля при импорте
load_blocked_lists()