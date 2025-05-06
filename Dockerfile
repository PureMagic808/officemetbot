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

# Установка зависимостей
RUN pip install --no-cache-dir -r requirements.txt --index-url https://pypi.org/simple

# Команда запуска
CMD ["python", "bot_railway.py"]
