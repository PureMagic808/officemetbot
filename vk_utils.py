import logging
import vk_api
from typing import List, Dict
import time
import random

logger = logging.getLogger(__name__)

VK_GROUP_IDS = [29534144, 60102821]  # Добавьте другие группы с мемами для 18+

def fetch_vk_memes(group_id: int, count: int, vk_session: vk_api.VkApi) -> List[Dict]:
    """
    Получает мемы из указанной VK группы.
    """
    try:
        vk = vk_session.get_api()
        memes = []
        offset = 0
        max_attempts = 5
        attempt = 0

        while len(memes) < count and attempt < max_attempts:
            response = vk.wall.get(
                owner_id=-group_id,
                count=min(100, count - len(memes)),  # Максимум 100 постов за запрос
                offset=offset,
                filter="owner"
            )
            items = response.get("items", [])
            if not items:
                logger.info(f"Больше постов не найдено в группе {group_id}")
                break

            for item in items:
                if "attachments" in item:
                    for attachment in item["attachments"]:
                        if attachment["type"] == "photo":
                            photo = attachment["photo"]
                            sizes = photo.get("sizes", [])
                            if sizes:
                                image_url = max(sizes, key=lambda x: x.get("width", 0)).get("url", "")
                                text = item.get("text", "").strip()
                                if image_url and text:
                                    memes.append({"image_url": image_url, "text": text, "tags": []})
                                    if len(memes) >= count:
                                        break
                if len(memes) >= count:
                    break
            offset += len(items)
            attempt += 1
            if attempt < max_attempts:
                time.sleep(random.uniform(0.5, 1.5))  # Задержка для соблюдения лимитов API

        logger.info(f"Получено {len(memes)} мемов из группы {group_id}")
        return memes

    except vk_api.exceptions.ApiError as e:
        logger.error(f"Ошибка VK API при загрузке мемов из группы {group_id}: {e}")
        return []
    except Exception as e:
        logger.error(f"Неожиданная ошибка при загрузке мемов из группы {group_id}: {e}")
        return []
    memes = fetch_memes_from_all_groups(20)
    for meme in memes:
        logger.info(f"Мем: Text={meme['text'][:50]}, URL={meme['image_url']}")
