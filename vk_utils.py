import logging
import vk_api
from typing import List, Dict
import time
import random

logger = logging.getLogger(__name__)

# Список групп VK (ID публичных групп с мемами)
VK_GROUP_IDS = [
    29534144,  # Оставляем старую группу
    27532693,  # MDK
    35208724,   # Pikabu
    61478497,
    34246602,
    38764982,
    52837491,
    74918234,
    89123456,
    45678901,

]

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

        logger.info(f"Начало загрузки мемов из группы {group_id}, count={count}")
        while len(memes) < count and attempt < max_attempts:
            response = vk.wall.get(
                owner_id=-group_id,
                count=min(100, count - len(memes)),  # Максимум 100 постов за запрос
                offset=offset,
                filter="owner"
            )
            items = response.get("items", [])
            if not items:
                logger.info(f"Больше постов не найдено в группе {group_id} на offset={offset}")
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
                time.sleep(random.uniform(1.0, 2.0))  # Увеличена задержка

        logger.info(f"Получено {len(memes)} мемов из группы {group_id}")
        return memes

    except vk_api.exceptions.ApiError as e:
        logger.error(f"Ошибка VK API при загрузке мемов из группы {group_id}: {e}")
        return []
    except Exception as e:
        logger.error(f"Неожиданная ошибка при загрузке мемов из группы {group_id}: {e}")
        return []
