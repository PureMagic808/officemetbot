# Базовый образ
FROM python:3.9-slim

# Установка рабочей директории
WORKDIR /app

# Установка системных зависимостей для Pillow
RUN apt-get update && apt-get install -y \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Копирование только необходимых файлов
COPY bot_railway.py meme_data.py vk_utils.py recommendation_engine.py meme_analytics.py requirements.txt ./

# Отладка: проверим, что requirements.txt скопирован
RUN ls -la && cat requirements.txt

# Обновляем pip до последней версии
RUN pip install --no-cache-dir --upgrade pip

# Установка зависимостей по одной для отладки
RUN pip install --no-cache-dir Pillow==10.4.0 --index-url https://pypi.org/simple
RUN pip install --no-cache-dir python-telegram-bot==20.7 --index-url https://pypi.org/simple
RUN pip install --no-cache-dir requests==2.32.3 --index-url https://pypi.org/simple
RUN pip install --no-cache-dir vk-api==12.0.0 --index-url https://pypi.org/simple

# Команда запуска
CMD ["python", "bot_railway.py"]
