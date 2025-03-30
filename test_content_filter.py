#!/usr/bin/env python3
"""
Тестирует фильтрацию рекламного контента, особенно
обработку конкретных рекламных изображений.
"""
import logging
import sys
from content_filter import is_suitable_meme, check_for_specific_ad_images

# Настройка логирования
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stdout)
logger = logging.getLogger(__name__)

def test_fitness_ad_filtering():
    """Проверяет фильтрацию рекламы фитнеса."""
    print("=== ТЕСТИРОВАНИЕ ФИЛЬТРАЦИИ ФИТНЕС-РЕКЛАМЫ ===")
    
    # Тест 1: Розовые гантели из первого изображения
    test_meme1 = {
        "image_url": "https://example.com/fitness/pink-dumbbells-christmas.jpg",
        "text": "Тренируйся вместе с нами! Специальное новогоднее предложение.",
        "tags": ["фитнес", "тренировка", "новогодний"]
    }
    
    # Тест 2: Гантели в другом контексте
    test_meme2 = {
        "image_url": "https://example.com/workout/dumbbells-exercise.jpg",
        "text": "Как правильно поднимать гантели",
        "tags": ["спорт", "тренировка"]
    }
    
    # Тест 3: Новогодняя реклама спортзала
    test_meme3 = {
        "image_url": "https://example.com/gym/christmas-fitness-offer.jpg",
        "text": "Скидка 50% на абонемент в спортзал! Только до 10 января.",
        "tags": ["фитнес", "новый год", "скидка"]
    }
    
    # Проверяем, что все они отфильтрованы
    for i, meme in enumerate([test_meme1, test_meme2, test_meme3], 1):
        result = is_suitable_meme(meme)
        print(f"Тест {i}: Мем {'ПОДХОДИТ' if result else 'ОТФИЛЬТРОВАН'}")
        print(f"   URL: {meme['image_url']}")
        print(f"   Текст: {meme['text']}")
        print(f"   Теги: {meme['tags']}")
        print()

def test_nail_artist_filtering():
    """Проверяет фильтрацию рекламы маникюра."""
    print("=== ТЕСТИРОВАНИЕ ФИЛЬТРАЦИИ РЕКЛАМЫ МАНИКЮРА ===")
    
    # Тест 1: Реклама маникюра от Ирины Емельяновой
    test_meme1 = {
        "image_url": "https://example.com/beauty/irina-emelyanova-nail-art.jpg",
        "text": "Ирина Емельянова - nail artist. Запись на маникюр по телефону.",
        "tags": ["маникюр", "ногти", "красота"]
    }
    
    # Тест 2: Розовый фон и маникюр
    test_meme2 = {
        "image_url": "https://example.com/beauty/pink-background-nail-design.jpg",
        "text": "Стильный маникюр на розовом фоне",
        "tags": ["дизайн ногтей", "красота"]
    }
    
    # Тест 3: Общая реклама салона красоты
    test_meme3 = {
        "image_url": "https://example.com/beauty/salon-services.jpg",
        "text": "Салон красоты предлагает услуги маникюра, педикюра и наращивания ресниц",
        "tags": ["красота", "салон", "маникюр"]
    }
    
    # Проверяем, что все они отфильтрованы
    for i, meme in enumerate([test_meme1, test_meme2, test_meme3], 1):
        result = is_suitable_meme(meme)
        print(f"Тест {i}: Мем {'ПОДХОДИТ' if result else 'ОТФИЛЬТРОВАН'}")
        print(f"   URL: {meme['image_url']}")
        print(f"   Текст: {meme['text']}")
        print(f"   Теги: {meme['tags']}")
        print()

def test_food_delivery_filtering():
    """Проверяет фильтрацию рекламы доставки еды."""
    print("=== ТЕСТИРОВАНИЕ ФИЛЬТРАЦИИ РЕКЛАМЫ ДОСТАВКИ ЕДЫ ===")
    
    # Тест 1: Доставка роллов с рыбой-поваром
    test_meme1 = {
        "image_url": "https://example.com/food/fish-chef-sushi-delivery.jpg",
        "text": "Доставка роллов угорь чторру. Закажи сейчас!",
        "tags": ["еда", "доставка", "суши"]
    }
    
    # Тест 2: Доставка пиццы
    test_meme2 = {
        "image_url": "https://example.com/food/pizza-delivery.jpg",
        "text": "Закажи пиццу с доставкой на дом",
        "tags": ["пицца", "доставка", "еда"]
    }
    
    # Тест 3: Ресторан суши
    test_meme3 = {
        "image_url": "https://example.com/food/sushi-restaurant-menu.jpg",
        "text": "Попробуй наше новое меню суши и роллов",
        "tags": ["суши", "роллы", "ресторан"]
    }
    
    # Проверяем, что все они отфильтрованы
    for i, meme in enumerate([test_meme1, test_meme2, test_meme3], 1):
        result = is_suitable_meme(meme)
        print(f"Тест {i}: Мем {'ПОДХОДИТ' if result else 'ОТФИЛЬТРОВАН'}")
        print(f"   URL: {meme['image_url']}")
        print(f"   Текст: {meme['text']}")
        print(f"   Теги: {meme['tags']}")
        print()

def test_specific_ad_images():
    """Проверяет функцию для обнаружения конкретных рекламных изображений."""
    print("=== ТЕСТИРОВАНИЕ ОБНАРУЖЕНИЯ КОНКРЕТНЫХ РЕКЛАМНЫХ ИЗОБРАЖЕНИЙ ===")
    
    # Тест 1: Изображение с розовыми гантелями и новогодними украшениями
    image_url1 = "https://example.com/fitness/pink-dumbbells-christmas-tree.jpg"
    text1 = "Тренируйся вместе с нами! Новогодняя акция"
    result1 = check_for_specific_ad_images(image_url1, text1)
    
    # Тест 2: Визитка мастера маникюра на розовом фоне
    image_url2 = "https://example.com/nail/irina-emelyanova-pink-background.jpg"
    text2 = "Ирина Емельянова - nail artist"
    result2 = check_for_specific_ad_images(image_url2, text2)
    
    # Тест 3: Логотип доставки суши с рыбой в поварском колпаке
    image_url3 = "https://example.com/food/fish-chef-delivery.jpg"
    text3 = "Доставка роллов и суши"
    result3 = check_for_specific_ad_images(image_url3, text3)
    
    print(f"Розовые гантели: {'ОБНАРУЖЕНО' if result1 else 'НЕ ОБНАРУЖЕНО'}")
    print(f"Маникюр: {'ОБНАРУЖЕНО' if result2 else 'НЕ ОБНАРУЖЕНО'}")
    print(f"Доставка еды: {'ОБНАРУЖЕНО' if result3 else 'НЕ ОБНАРУЖЕНО'}")

if __name__ == "__main__":
    print("Запуск тестов фильтрации рекламного контента...")
    test_fitness_ad_filtering()
    test_nail_artist_filtering()
    test_food_delivery_filtering()
    test_specific_ad_images()
    print("Тестирование завершено.")