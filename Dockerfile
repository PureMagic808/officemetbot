# Используем легковесный базовый образ Python
FROM python:3.9-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем только необходимые файлы
COPY bot_railway.py meme_data.py vk_utils.py recommendation_engine.py meme_analytics.py requirements.txt ./

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Указываем точку входа
CMD ["python", "bot_railway.py"]
