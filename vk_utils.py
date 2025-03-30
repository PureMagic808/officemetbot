
import vk_api
import random
import requests
from io import BytesIO
from PIL import Image
import logging
import os

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
    
    def get_random_meme(self, group_ids):
        try:
            group_id = random.choice(group_ids)
            posts = self.vk.wall.get(owner_id=-group_id, count=100)
            
            # Фильтруем посты
            posts_with_photos = []
            for post in posts['items']:
                # Проверяем базовые условия
                if not ('attachments' in post and any(att['type'] == 'photo' for att in post['attachments'])):
                    continue
                    
                # Проверяем рекламные метки
                if post.get('marked_as_ads', 0) or post.get('is_pinned', 0):
                    continue
                    
                # Проверяем текст на рекламные слова
                text = post.get('text', '').lower()
                ad_words = ['реклама', 'ads', 'купить', 'продажа', 'магазин', 'заказать', 
                          'акция', 'скидка', 'распродажа', 'товар', 'цена', 'sale', 'shop',
                          'доставка', 'заказ', 'бесплатно', 'руб', '₽', '$', 'подпишись']
                if any(word in text for word in ad_words):
                    continue
                    
                # Проверяем ссылки
                if 'attachments' in post and any(att.get('type') == 'link' for att in post['attachments']):
                    continue
                    
                posts_with_photos.append(post)
            
            if not posts_with_photos:
                return self.DEFAULT_ERROR_IMAGE, self.DEFAULT_ERROR_TEXT
                
            post = random.choice(posts_with_photos)
            photo = next(att for att in post['attachments'] if att['type'] == 'photo')
            
            # Get the largest photo size
            sizes = photo['photo']['sizes']
            max_size = max(sizes, key=lambda x: x['width'] * x['height'])
            
            url = max_size['url']
            
            # Создаем уникальный хеш на основе нескольких параметров
            photo_id = str(photo['photo'].get('id', ''))
            owner_id = str(photo['photo'].get('owner_id', ''))
            access_key = str(photo['photo'].get('access_key', ''))
            image_hash = hash(url + photo_id + owner_id + access_key)
            
            # Проверяем, не был ли этот мем уже отправлен
            if image_hash in self.sent_memes:
                return self.get_random_meme(group_ids)  # Рекурсивно пробуем получить другой мем
                
            self.sent_memes.add(image_hash)  # Добавляем хеш в кэш
            
            # Если кэш слишком большой, очищаем его
            if len(self.sent_memes) > 1000:
                self.sent_memes.clear()
                
            return url, post.get('text', '')
            
        except Exception as e:
            logger.error(f"Error fetching meme: {e}")
            return None, str(e)
