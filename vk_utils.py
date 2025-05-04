import logging
import random
import time
import vk_api
from vk_api.exceptions import ApiError

# Настройка логирования
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_vk_memes(group_id, count=20, vk_session=None):
    """
    Получает мемы из указанной VK-группы
    """
    if not vk_session:
        logger.error("vk_session не предоставлен")
        return []
    
    vk = vk_session.get_api()
    memes = []
    seen_memes = set()  # Для исключения дубликатов
    attempts = 0
    max_attempts = 10
    
    while len(memes) < count and attempts < max_attempts:
        try:
            # Получаем посты из группы (wall.get)
            posts = vk.wall.get(owner_id=-group_id, count=min(100, count - len(memes)), offset=len(memes))
            if not posts.get('items'):
                logger.warning(f"Нет постов в группе {group_id} или достигнут лимит")
                break
            
            for post in posts['items']:
                if 'attachments' in post:
                    for attachment in post['attachments']:
                        if attachment['type'] == 'photo':
                            image_url = max(attachment['photo']['sizes'], key=lambda x: x['width'])['url']
                            text = post.get('text', '')[:200]  # Ограничиваем текст
                            meme_key = f"{text}|{image_url}"  # Ключ для проверки дубликатов
                            if meme_key in seen_memes:
                                continue  # Пропускаем дубликат
                            seen_memes.add(meme_key)
                            meme = {
                                'text': text,
                                'image_url': image_url,
                                'tags': [tag.strip() for tag in post.get('text', '').split() if tag.startswith('#')],
                                'source': f'vk_group_{group_id}'
                            }
                            memes.append(meme)
                if len(memes) >= count:
                    break
            if len(memes) < count:
                logger.info(f"Получено {len(memes)} мемов из группы {group_id}, продолжаем...")
            else:
                logger.info(f"Получено {len(memes)} мемов из группы {group_id}")
                break
            time.sleep(random.uniform(0.5, 1))  # Задержка для соблюдения лимитов API
        except ApiError as e:
            logger.error(f"Ошибка API при загрузке мемов из группы {group_id}: {e}")
            break
        except Exception as e:
            logger.error(f"Неизвестная ошибка при загрузке мемов из группы {group_id}: {e}")
            break
        attempts += 1
    
    return memes[:count]

# Список групп с офисной тематикой и новыми группами
VK_GROUP_IDS = [
    29534144,   # Офисный планктон
    60102821,   # Офисный юмор и мемы
    162150316,  # 4chnn (интернет-культура и мемы)
    45045130,   # public45045130 (возможно, мемы про животных)
    211664614   # zoopack (мемы про животных)
]

def fetch_memes_from_all_groups(count=20):
    """
    Получает мемы из всех указанных групп
    """
    all_memes = []
    vk_session = vk_api.VkApi(token='YOUR_VK_TOKEN')  # Замените на реальный токен
    for group_id in VK_GROUP_IDS:
        group_memes = fetch_vk_memes(group_id, count // len(VK_GROUP_IDS), vk_session)
        all_memes.extend(group_memes)
        if len(all_memes) >= count:
            break
        time.sleep(random.uniform(1, 2))  # Задержка между группами
    logger.info(f"Всего получено {len(all_memes)} мемов из {len(VK_GROUP_IDS)} групп")
    return all_memes[:count]

if __name__ == "__main__":
    # Пример использования
    memes = fetch_memes_from_all_groups(20)
    for meme in memes:
        logger.info(f"Мем: Text={meme['text'][:50]}, URL={meme['image_url']}")
