#!/usr/bin/env python3
"""
Улучшенный модуль фильтрации с агрессивным блокированием рекламы.
Оптимизирован для работы с реальным временем и сохранения юмористических мемов.
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
        "рассрочка", "руб", "₽", "$", "sale", "shop", "подарок", "выгода",
        "бесплатно", "товар", "доставка", "купон", "пром", "промо", "promo",
        "дисконт", "покупк", "заказ", "card", "карта", "банк",
        "промокод", "только до", "успей"
    ],
    "fitness": [
        "тренер", "тренировк", "фитнес", "спортзал", "гантели", "gym", 
        "workout", "фитоняшка", "тренажер", "зал", "упражнен", "пресс", 
        "фигур", "тело", "похуде", "диета", "exercise", "fitness", 
        "мышцы", "тренировки", "тренируйся", "кардио", "бассейн", "аквааэробика",
        "йога", "растяжка", "кроссфит", "crossfit", "абонемент", "stretching"
    ],
    "beauty": [
        "маникюр", "ногти", "педикюр", "салон", "nail", "beauty", 
        "мастер", "парикмахер", "стрижк", "окрашивание", "волосы", "hair", "make up", 
        "makeup", "визаж", "косметолог", "мейкап", "lash", "lashes", "ресницы", 
        "прядь", "прическ", "стилист", "эпиляция", "массаж",
        "молодость", "anti-age", "омоложение", "spa", "эстетик"
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
ALL_BLOCKED_PATTERNS = list(set(ALL_BLOCKED_PATTERNS))

# Изображения на проверку
SPECIFIC_BLOCKED_IMAGES = [
    "тренируйся-вместе-с-нами", "train-with-us", "fitness-promo", "workout-ad",
    "фитнес-клуб", "тренировка", "гантели", "fitness", "dumbbells", "exercise",
    "new-year-fitness", "новогодний-фитнес", "pink-dumbbells", "розовые-гантели",
    "irina-emelyanova", "emelyanova-nail", "nail-artist", "маникюр-мастер",
    "beauty-salon", "салон-красоты", "маникюр", "ногти", "nail-design", "nail-art",
    "доставка-роллов", "sushi-delivery", "чторру", "доставка-суши", "суши-доставка",
    "роллы-доставка", "доставка-пиццы", "доставка-еды", "еда-на-дом", 
    "рыба-повар", "рыба-шеф", "fish-chef", "chef-sushi",
    "reklama", "реклама", "ad-", "advert-"
]

# Расширенные маркеры по категориям
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
    for pattern in ALL_BLOCKED_PATTERNS:
        if pattern in text:
            return True, f"найдено рекламное слово '{pattern}'"
    
    ad_regexes = [
        r'\d+\s*%', r'скидк[аиу]?\s+до\s+\d+', r'до\s+-\d+\s*%',
        r'от\s+\d+\s*руб', r'всего\s+\d+\s*руб', r'всего\s+за\s+\d+',
        r'цена\s*:?\s*\d+', r'стоимость\s*:?\s*\d+', r'руб\.|₽',
        r'звони[те]?', r'пиши[те]?', r'заходи[те]?', r'приходи[те]?',
        r'спеши[те]?', r'успей[те]?', r'закажи[те]?', r'предлож[еи]ни[ея]',
        r'выгодн[ыоеая]', r'подробн[ее]?',
        r'\+7\s*\(\d{3}\)\s*\d{3}[-\s]?\d{2}[-\s]?\d{2}',
        r'8\s*\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}',
        r'тел[\.\:]', r'контакты\s*:',
        r'https?:\/\/', r'www\.', r'\.ru|\.com|\.net|\.org',
        r'онлайн', r'оф+ициальный сайт', r'подписыва[ея]тесь',
        r'заказ[ат]ь\s+на\s+сайте', r'акци[яи]', r'скидк[иа]',
        r'распродаж[аи]', r'спец\.?\s*предложени[ея]',
        r'количество ограничено', r'только\s+(сегодня|завтра|до\s+\d+)',
        r'дейтсву[еюя]т\s+до', r'записыва[ей]тесь',
        r'подробности\s+(по\s+телефону|на\s+сайте)',
        r'💰|💲|💸|💵|💴|💶|💷|🏷️|🏷|🔖|📝|📲|📱|📞|☎️|📧|✉️|🛒|🛍️|🛍|🎁'
    ]
    
    for regex in ad_regexes:
        if re.search(regex, text, re.IGNORECASE):
            return True, f"найден рекламный шаблон '{regex}'"
    
    return False, ""

def detect_advertisement_in_url(url):
    """
    Проверяет URL на наличие рекламных маркеров
    Возвращает (bool, str) - (найдена реклама?, причина)
    """
    if not url:
        return False, ""
    
    url = url.lower()
    for specific_image in SPECIFIC_BLOCKED_IMAGES:
        if specific_image in url:
            return True, f"URL содержит блокируемый паттерн: {specific_image}"
    
    if is_blocked_image(url):
        return True, "URL находится в списке заблокированных изображений"
    
    parsed_url = urlparse(url)
    domain_path = (parsed_url.netloc + parsed_url.path).lower()
    for pattern in ALL_BLOCKED_PATTERNS:
        if pattern in domain_path:
            return True, f"URL содержит рекламное слово: {pattern}"
    
    return False, ""

def detect_ad_category(item_data):
    """
    Определяет категорию рекламы
    Возвращает (категория или None, уверенность 0-100)
    """
    if not item_data:
        return None, 0
    
    text = item_data.get("text", "").lower()
    image_url = item_data.get("image_url", "").lower()
    category_scores = {}
    
    for category, patterns in ADVERTISING_PATTERNS.items():
        score = 0
        for pattern in patterns:
            if pattern in text:
                score += 10
            if pattern in image_url:
                score += 5
        if category in EXTENDED_MARKERS:
            for marker in EXTENDED_MARKERS[category]:
                if marker in text:
                    score += 15
                if marker in image_url:
                    score += 5
        category_scores[category] = score
    
    max_category = max(category_scores.items(), key=lambda x: x[1], default=(None, 0))
    if max_category[1] >= 10:
        return max_category[0], min(max_category[1], 100)
    return None, 0

def check_for_specific_ad_content(image_url, text=None):
    """
    Проверяет на конкретные рекламные материалы
    Возвращает (bool, str) - (является рекламным?, причина)
    """
    if not image_url and not text:
        return False, ""
    
    url = image_url.lower() if image_url else ""
    text = text.lower() if text else ""
    
    for category, markers in EXTENDED_MARKERS.items():
        for marker in markers:
            if marker in url or marker in text:
                return True, f"обнаружен маркер рекламы категории '{category}': {marker}"
    
    return False, ""

def is_suitable_meme_advanced(meme, strict_mode=True):
    """
    Проверяет, подходит ли мем для показа. Отфильтровывает рекламу, но допускает мемы без строгой офисной тематики.
    
    Args:
        meme (dict): Словарь с информацией о меме (image_url, text, tags, source, timestamp)
        strict_mode (bool): Если True, применяет строгую фильтрацию по офисной тематике
    
    Returns:
        bool: True если мем подходит, False если нет
    """
    if not blocked_image_hashes:
        load_blocked_lists()
    
    try:
        image_url = meme.get("image_url", "").lower()
        text = meme.get("text", "").lower()
        tags = meme.get("tags", []) if isinstance(meme.get("tags"), list) else []
        source = meme.get("source", "").lower()

        # Проверка на минимальную валидность мема
        if not image_url and not text:
            logger.info("Мем отфильтрован: отсутствуют изображение и текст")
            return False

        # Проверка на религиозный контент
        religious_keywords = [
            "христианск", "служени", "православ", "молитв", "церковь", "храм",
            "бог", "господ", "вера", "духовн", "религи", "святой", "священник",
            "проповед", "библи", "крещени", "грех", "исповед", "воскресени",
            "церемони", "ритуал", "поклонени", "патриарх", "монасты", "монах"
        ]
        for keyword in religious_keywords:
            if keyword in text:
                logger.info(f"Мем отфильтрован: содержит религиозную тематику ('{keyword}')")
                return False

        # Проверка на татуировки
        tattoo_keywords = ["тату", "татуировк", "татуха", "набит", "набивать"]
        for keyword in tattoo_keywords:
            if keyword in text:
                logger.info(f"Мем отфильтрован: содержит упоминание татуировок")
                return False

        # Проверка на конкретные рекламные маркеры
        is_ad, reason = check_for_specific_ad_content(image_url, text)
        if is_ad:
            logger.info(f"Мем отфильтрован: {reason}")
            add_blocked_image(image_url)
            return False

        # Проверка текста на рекламу
        is_ad, reason = detect_advertisement_in_text(text)
        if is_ad:
            logger.info(f"Мем отфильтрован по тексту: {reason}")
            add_blocked_image(image_url)
            return False

        # Проверка URL на рекламу
        if image_url:
            is_ad, reason = detect_advertisement_in_url(image_url)
            if is_ad:
                logger.info(f"Мем отфильтрован по URL: {reason}")
                add_blocked_image(image_url)
                return False

        # Проверка валютных символов
        currency_symbols = ["₽", "$", "€", "руб", "рубл", "dollar", "доллар", "евро"]
        if any(symbol in text for symbol in currency_symbols):
            logger.info(f"Мем отфильтрован: содержит символы валют/денег")
            add_blocked_image(image_url)
            return False

        # Проверка тегов
        allowed_tags = ["мем", "юмор", "офис", "работа", "босс", "начальник", "коллеги", "сотрудник"]
        for tag in tags:
            tag_text = tag.lower()
            if tag_text in allowed_tags:
                continue
            is_ad, reason = detect_advertisement_in_text(tag_text)
            if is_ad:
                logger.info(f"Мем отфильтрован по тегу: {tag} ({reason})")
                add_blocked_image(image_url)
                return False

        # Проверка метаданных
        if "metadata" in meme and isinstance(meme["metadata"], dict):
            metadata = meme["metadata"]
            for field in ["title", "description"]:
                if field in metadata and metadata[field]:
                    is_ad, reason = detect_advertisement_in_text(metadata[field].lower())
                    if is_ad:
                        logger.info(f"Мем отфильтрован по {field} метаданных: {reason}")
                        add_blocked_image(image_url)
                        return False

        # Проверка категории рекламы
        ad_category, confidence = detect_ad_category(meme)
        if ad_category and confidence > 20:
            logger.info(f"Мем отфильтрован: похож на рекламу категории '{ad_category}' с уверенностью {confidence}%")
            add_blocked_image(image_url)
            return False

        # Проверка на длинный текст с повторяющимися словами
        if text and len(text.split()) > 50:
            words = text.split()
            word_count = {}
            for word in words:
                if len(word) > 3:
                    word_count[word] = word_count.get(word, 0) + 1
            for word, count in word_count.items():
                if count > 3:  # Снизили порог с 5 до 3
                    logger.info(f"Мем отфильтрован: содержит повторяющееся слово '{word}' ({count} раз)")
                    add_blocked_image(image_url)
                    return False

        # Проверка на офисную тематику (только в строгом режиме)
        if strict_mode:
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
            is_office_related = any(keyword in text for keyword in office_keywords + work_keywords)
            if not is_office_related and text and len(text.split()) > 5:
                logger.info("Мем отфильтрован: не содержит офисной тематики в строгом режиме")
                return False

        return True
    
    except Exception as e:
        logger.error(f"Ошибка при фильтрации мема: {e}")
        return False

# Инициализация модуля
load_blocked_lists()
