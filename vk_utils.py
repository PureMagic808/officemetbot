#!/usr/bin/env python3
"""
Модуль для взаимодействия с VK API и получения мемов из публичных групп.
"""
import logging
import time
import random
import vk_api
from vk_api.utils import get_random_id

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fetch_vk_memes(group_id, count=10, vk_session=None):
    """
    Получает мемы из указанной группы ВКонтакте через VK API.
    
    Args:
        group_id (int): ID группы ВКонтакте
        count (int): Количество постов для обработки
        vk_session (vk_api.VkApi, optional): Сессия VK API
    
    Returns:
        list: Список словарей с данными мемов
    """
    memes = []
    try:
        if vk_session is None:
            raise ValueError("vk_session не предоставлен")
        
        vk = vk_session.get_api()
        
        # Получение постов со стены группы
        posts = vk.wall.get(owner_id=-group_id, count=count, filter='owner')
        
        for post in posts.get('items', []):
            try:
                # Пропускаем закреплённые посты
                if post.get('is_pinned'):
                    continue
                
                meme_data = {
                    'text': post.get('text', ''),
                    'image_url': '',
                    'tags': [],
                    'source': f'vk.com/wall-{group_id}_{post["id"]}',
                    'timestamp': post.get('date', '')
                }
                
                # Извлечение тегов из текста
                text = meme_data['text'].lower()
                if 'офис' in text or 'работа' in text:
                    meme_data['tags'].append('офис')
                if 'it' in text or 'программист' in text:
                    meme_data['tags'].append('IT')
                
                # Извлечение изображения из вложений
                attachments = post.get('attachments', [])
                for attachment in attachments:
                    if attachment['type'] == 'photo':
                        sizes = attachment['photo'].get('sizes', [])
                        # Выбираем изображение с максимальным разрешением
                        if sizes:
                            image_url = max(sizes, key=lambda x: x['width'] * x['height'])['url']
                            meme_data['image_url'] = image_url
                            break
                
                # Добавляем мем, только если есть изображение
                if meme_data['image_url']:
                    memes.append(meme_data)
                
            except Exception as e:
                logger.error(f"Ошибка при получении мема: {e}")
                continue
            time.sleep(random.uniform(0.3, 0.7))  # Задержка для соблюдения лимитов
            
        logger.info(f"Получено {len(memes)} мемов из группы {group_id} за {count} попыток")
        
    except Exception as e:
        logger.error(f"Ошибка при получении мемов из группы {group_id}: {e}")
    
    return memes
