import vk_api
import random
import requests
from io import BytesIO
from PIL import Image
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class VKMemesFetcher:
    def __init__(self, vk_token):
        self.vk_session = vk_api.VkApi(token=vk_token)
        self.vk = self.vk_session.get_api()
        self.sent_memes = set()  # Кэш для хранения отправленных мемов
        self.meme_dislikes = {}  # Словарь для хранения дизлайков
        self.max_dislikes = 15  # Максимальное количество дизлайков
        
    # Константы для обработки ошибок
    DEFAULT_ERROR_IMAGE = "https://i.imgur.com/dNKhgfT.png"
    DEFAULT_ERROR_TEXT = "Не удалось загрузить мем. Попробуйте еще раз."
    
    def get_random_meme(self, group_ids, try_office_group=True):
        """
        Получает один случайный мем из указанных групп VK.
        Args:
            group_ids (list): Список ID групп VK.
            try_office_group (bool): Если True, отдаёт предпочтение офисным группам.
        Returns:
            tuple: (url, text, tags, source, timestamp) или (None, str) в случае ошибки.
        """
        try:
            # Расширенный список групп с мемами про офис
            office_group_ids = [
                29534144,   # Офисный планктон
                57846937,   # Мемы для офиса
                209220261,  # HR-мемы
                134304772,  # Суровый менеджмент
                85585215,   # Офисный юмор
                111463603,  # Работа в офисе
                162742070,  # Офис на минималках
                160951472   # Офисные приключения
            ]
            
            # Используем преимущественно группы про офис
            if try_office_group and random.random() < 0.8 and office_group_ids:
                group_id = random.choice(office_group_ids)
                source = f"vk_group_{group_id}_office"
            else:
                group_id = random.choice(group_ids)
                source = f"vk_group_{group_id}"
                
            posts = self.vk.wall.get(owner_id=-group_id, count=150)
            
            # Фильтруем посты
            posts_with_photos = []
            for post in posts['items']:
                # Проверяем базовые условия
                if not ('attachments' in post and any(att['type'] == 'photo' for att in post['attachments'])):
                    continue
                    
                # Проверяем рекламные метки
                if post.get('marked_as_ads', 0) or post.get('is_pinned', 0):
                    continue
                
                # Проверка текста на рекламные слова (минимальная фильтрация)
                text = post.get('text', '').lower()
                ad_words = [
                    'реклама', 'ads', 'купить', 'продажа', 'магазин', 'заказать', 
                    'акция', 'скидка', 'распродажа', 'товар', 'цена', 'sale', 'shop',
                    'доставка', 'заказ', 'бесплатно', 'руб', '₽', '$', 'подпишись',
                    'подписывайтесь', 'заходите', 'вступайте', 'промо', 'промокод'
                ]
                if any(word in text for word in ad_words):
                    continue
                
                # Проверка на религиозный контент
                religious_words = [
                    'храм', 'церковь', 'бог', 'господ', 'молитв', 'православ',
                    'христиан', 'вера', 'служение', 'духовн', 'священник', 'библи'
                ]
                if any(word in text for word in religious_words):
                    continue
                    
                # Проверяем ссылки и внешние сервисы
                if ('attachments' in post and 
                    any(att.get('type') in ['link', 'market', 'app', 'poll'] for att in post['attachments'])):
                    continue
                    
                # Формируем теги
                tags = ['мем', 'юмор']
                if try_office_group:
                    tags.append('офис')
                    office_words = [
                        'офис', 'работа', 'босс', 'начальник', 'коллега', 'сотрудник',
                        'зарплата', 'проект', 'отпуск', 'отдел', 'компания', 'корпоратив'
                    ]
                    if any(word in text for word in office_words):
                        posts_with_photos.append(post)
                else:
                    posts_with_photos.append(post)
            
            if not posts_with_photos:
                return None, self.DEFAULT_ERROR_TEXT
                
            post = random.choice(posts_with_photos)
            photo = next(att for att in post['attachments'] if att['type'] == 'photo')
            
            # Получаем самое большое изображение
            sizes = photo['photo']['sizes']
            max_size = max(sizes, key=lambda x: x['width'] * x['height'])
            url = max_size['url']
            
            # Проверяем доступность URL
            try:
                response = requests.get(url, timeout=5, stream=True)
                if response.status_code != 200:
                    logger.warning(f"URL изображения недоступен: {url}, статус: {response.status_code}")
                    return None, self.DEFAULT_ERROR_TEXT
                
                # Проверяем, что это действительно изображение
                try:
                    img_data = BytesIO(response.content)
                    img = Image.open(img_data)
                    img.verify()
                except Exception as img_error:
                    logger.error(f"Получен неверный формат изображения: {img_error}")
                    return None, self.DEFAULT_ERROR_TEXT
                    
            except Exception as request_error:
                logger.error(f"Ошибка при проверке URL изображения: {request_error}")
                return None, self.DEFAULT_ERROR_TEXT
            
            # Создаём уникальный хеш
            photo_id = str(photo['photo'].get('id', ''))
            owner_id = str(photo['photo'].get('owner_id', ''))
            access_key = str(photo['photo'].get('access_key', ''))
            image_hash = hash(url + photo_id + owner_id + access_key)
            
            # Проверяем, не был ли мем отправлен
            if image_hash in self.sent_memes:
                return self.get_random_meme(group_ids, try_office_group)
                
            self.sent_memes.add(image_hash)
            if len(self.sent_memes) > 1000:
                self.sent_memes.clear()
            
            # Формируем временную метку
            timestamp = datetime.fromtimestamp(post.get('date', int(time.time()))).isoformat()
            
            return url, post.get('text', ''), tags, source, timestamp
            
        except Exception as e:
            logger.error(f"Ошибка при получении мема: {e}")
            return None, str(e)

def fetch_vk_memes(group_id, count=10, vk_token=None):
    """
    Получает указанное количество мемов из группы VK.
    Args:
        group_id (int): ID группы VK (без минуса).
        count (int): Количество мемов для получения.
        vk_token (str): Токен VK API (если не передан, берётся из переменной окружения).
    Returns:
        list: Список словарей [{image_url, text, tags, source, timestamp}, ...].
    """
    if vk_token is None:
        vk_token = os.getenv("VK_TOKEN")
        if not vk_token:
            logger.error("VK_TOKEN не задан в переменных окружения")
            return []
    
    fetcher = VKMemesFetcher(vk_token)
    memes = []
    attempts = 0
    max_attempts = count * 3  # Ограничение попыток
    
    while len(memes) < count and attempts < max_attempts:
        result = fetcher.get_random_meme([group_id], try_office_group=True)
        if result[0] is None:
            attempts += 1
            continue
            
        url, text, tags, source, timestamp = result
        meme = {
            "image_url": url,
            "text": text,
            "tags": tags,
            "source": source,
            "timestamp": timestamp
        }
        memes.append(meme)
        attempts += 1
    
    logger.info(f"Получено {len(memes)} мемов из группы {group_id} за {attempts} попыток")
    return memes
