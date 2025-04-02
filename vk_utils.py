#!/usr/bin/env python3
"""
Утилиты для взаимодействия с VK API для получения мемов.
Исправленная версия с улучшенной обработкой ошибок доступа к закрытым группам.
"""
import random
import logging
import time
import requests
from typing import Tuple, List, Optional

# Настройка логирования
logger = logging.getLogger(__name__)

class VKMemesFetcher:
    """Класс для получения мемов из VK"""
    
    def __init__(self, token: str):
        """
        Инициализация клиента VK API.
        
        Args:
            token (str): API ключ для доступа к VK API
        """
        self.token = token
        self.api_version = "5.131"
        self.base_url = "https://api.vk.com/method/"
        # Список публичных групп с мемами про офис, которые точно доступны без членства
        self.default_group_ids = [88523457, 63997621, 161266689, 149279263, 185954822]
        # Кэш для хранения доступных групп
        self.accessible_groups = {}
        # Проверяем доступные группы
        self._initialize_accessible_groups()
    
    def _initialize_accessible_groups(self):
        """Выполняет начальную проверку доступности групп"""
        logger.info("Инициализация доступных групп VK...")
        
        # Проверяем дефолтные группы
        for group_id in self.default_group_ids:
            self._check_group_access(group_id)
        
        if not self.accessible_groups:
            logger.warning("Не найдено доступных групп VK для получения мемов!")
            # Добавляем стандартные публичные группы с мемами, которые гарантированно доступны
            self.accessible_groups = {
                88523457: True,  # Мемы: паблик с мемами
                63997621: True,  # Лепра: публичная группа с мемами
                161266689: True  # Мемы для офисного планктона
            }
        else:
            logger.info(f"Доступные группы VK: {list(self.accessible_groups.keys())}")
    
    def _check_group_access(self, group_id: int) -> bool:
        """
        Проверяет доступность группы VK.
        
        Args:
            group_id (int): ID группы VK
            
        Returns:
            bool: True если группа доступна, False если нет
        """
        # Если группа уже проверена, возвращаем кэшированный результат
        if group_id in self.accessible_groups:
            return self.accessible_groups[group_id]
        
        # Параметры запроса
        params = {
            "access_token": self.token,
            "v": self.api_version,
            "owner_id": -group_id,  # Минус перед ID для обозначения группы
            "count": 1  # Запрашиваем только 1 пост для проверки
        }
        
        try:
            # Делаем запрос к API
            response = requests.get(f"{self.base_url}wall.get", params=params)
            data = response.json()
            
            if "error" in data:
                error_code = data["error"]["error_code"]
                error_msg = data["error"]["error_msg"]
                logger.warning(f"Группа {group_id} недоступна: [{error_code}] {error_msg}")
                self.accessible_groups[group_id] = False
                return False
            
            # Если дошли сюда, значит группа доступна
            self.accessible_groups[group_id] = True
            return True
        except Exception as e:
            logger.error(f"Ошибка при проверке доступа к группе {group_id}: {e}")
            self.accessible_groups[group_id] = False
            return False
    
    def get_random_meme(self, group_ids: Optional[List[int]] = None) -> Tuple[str, str]:
        """
        Получает случайный мем из указанных групп VK.
        
        Args:
            group_ids (List[int], optional): Список ID групп VK для поиска мемов
            
        Returns:
            Tuple[str, str]: (URL изображения, текст)
        """
        # Если не указаны группы, используем дефолтные
        if not group_ids:
            group_ids = self.default_group_ids
        
        # Фильтруем только доступные группы
        available_groups = []
        for group_id in group_ids:
            if self._check_group_access(group_id):
                available_groups.append(group_id)
        
        # Если нет доступных групп, используем резервные
        if not available_groups:
            logger.warning("Все указанные группы недоступны! Используем резервные группы.")
            available_groups = [gid for gid, accessible in self.accessible_groups.items() if accessible]
            
            # Если все еще нет доступных групп, используем дефолтные
            if not available_groups:
                available_groups = self.default_group_ids
        
        # Выбираем случайную группу
        group_id = random.choice(available_groups)
        
        # Получаем случайный пост со стены группы
        return self._get_random_post_with_photo(group_id)
    
    def _get_random_post_with_photo(self, group_id: int) -> Tuple[str, str]:
        """
        Получает случайный пост с фото со стены группы.
        
        Args:
            group_id (int): ID группы VK
            
        Returns:
            Tuple[str, str]: (URL изображения, текст)
        """
        # Проверяем доступность группы
        if not self._check_group_access(group_id):
            logger.warning(f"Группа {group_id} недоступна, пропускаем")
            return "", ""
        
        # Параметры запроса
        params = {
            "access_token": self.token,
            "v": self.api_version,
            "owner_id": -group_id,  # Минус перед ID для обозначения группы
            "count": 50,  # Получаем 50 последних постов
            "filter": "owner"  # Только посты от группы
        }
        
        try:
            # Делаем запрос к API
            response = requests.get(f"{self.base_url}wall.get", params=params)
            data = response.json()
            
            if "error" in data:
                error_code = data["error"]["error_code"]
                error_msg = data["error"]["error_msg"]
                logger.error(f"Error fetching meme: [{error_code}] {error_msg}")
                
                # Если ошибка доступа, помечаем группу как недоступную
                if error_code in [15, 30]:
                    self.accessible_groups[group_id] = False
                
                return "", ""
            
            # Получаем список постов
            posts = data.get("response", {}).get("items", [])
            
            # Фильтруем только посты с фото
            posts_with_photos = []
            for post in posts:
                # Проверяем наличие вложений
                if "attachments" in post:
                    # Проверяем наличие фото во вложениях
                    has_photo = any(att.get("type") == "photo" for att in post["attachments"])
                    if has_photo:
                        posts_with_photos.append(post)
            
            # Если есть посты с фото, выбираем случайный
            if posts_with_photos:
                post = random.choice(posts_with_photos)
                
                # Получаем текст поста
                text = post.get("text", "")
                
                # Получаем URL фото
                photo_url = ""
                for attachment in post.get("attachments", []):
                    if attachment.get("type") == "photo":
                        photo = attachment.get("photo", {})
                        # Получаем максимальное доступное разрешение
                        sizes = photo.get("sizes", [])
                        if sizes:
                            # Сортируем размеры по убыванию площади
                            sizes.sort(key=lambda s: s.get("width", 0) * s.get("height", 0), reverse=True)
                            photo_url = sizes[0].get("url", "")
                            break
                
                return photo_url, text
            else:
                logger.warning(f"Нет постов с фото в группе {group_id}")
                return "", ""
        except Exception as e:
            logger.error(f"Ошибка при получении мема из группы {group_id}: {e}")
            return "", ""
    
    def get_memes_from_group(self, group_id: int, count: int = 10) -> List[Tuple[str, str]]:
        """
        Получает несколько мемов из указанной группы.
        
        Args:
            group_id (int): ID группы VK
            count (int): Количество мемов для получения
            
        Returns:
            List[Tuple[str, str]]: Список кортежей (URL изображения, текст)
        """
        # Проверяем доступность группы
        if not self._check_group_access(group_id):
            logger.warning(f"Группа {group_id} недоступна, пропускаем")
            return []
        
        # Параметры запроса
        params = {
            "access_token": self.token,
            "v": self.api_version,
            "owner_id": -group_id,  # Минус перед ID для обозначения группы
            "count": 100,  # Получаем 100 последних постов
            "filter": "owner"  # Только посты от группы
        }
        
        try:
            # Делаем запрос к API
            response = requests.get(f"{self.base_url}wall.get", params=params)
            data = response.json()
            
            if "error" in data:
                error_code = data["error"]["error_code"]
                error_msg = data["error"]["error_msg"]
                logger.error(f"Ошибка при получении мемов из группы {group_id}: [{error_code}] {error_msg}")
                
                # Если ошибка доступа, помечаем группу как недоступную
                if error_code in [15, 30]:
                    self.accessible_groups[group_id] = False
                
                return []
            
            # Получаем список постов
            posts = data.get("response", {}).get("items", [])
            
            # Фильтруем только посты с фото
            posts_with_photos = []
            for post in posts:
                # Проверяем наличие вложений
                if "attachments" in post:
                    # Проверяем наличие фото во вложениях
                    has_photo = any(att.get("type") == "photo" for att in post["attachments"])
                    if has_photo:
                        posts_with_photos.append(post)
            
            # Если есть посты с фото, выбираем случайные
            if posts_with_photos:
                # Если постов меньше, чем запрошено, берем все
                if len(posts_with_photos) <= count:
                    selected_posts = posts_with_photos
                else:
                    # Иначе выбираем случайные
                    selected_posts = random.sample(posts_with_photos, count)
                
                # Формируем результат
                result = []
                for post in selected_posts:
                    # Получаем текст поста
                    text = post.get("text", "")
                    
                    # Получаем URL фото
                    photo_url = ""
                    for attachment in post.get("attachments", []):
                        if attachment.get("type") == "photo":
                            photo = attachment.get("photo", {})
                            # Получаем максимальное доступное разрешение
                            sizes = photo.get("sizes", [])
                            if sizes:
                                # Сортируем размеры по убыванию площади
                                sizes.sort(key=lambda s: s.get("width", 0) * s.get("height", 0), reverse=True)
                                photo_url = sizes[0].get("url", "")
                                break
                    
                    # Добавляем в результат, если есть URL фото
                    if photo_url:
                        result.append((photo_url, text))
                
                return result
            else:
                logger.warning(f"Нет постов с фото в группе {group_id}")
                return []
        except Exception as e:
            logger.error(f"Ошибка при получении мемов из группы {group_id}: {e}")
            return []