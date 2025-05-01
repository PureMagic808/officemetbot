FROM python:3.10-slim

WORKDIR /app

# Копируем только файлы зависимостей для использования кэширования слоев Docker
COPY requirements.txt

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

# Запускаем бота
CMD ["python", "bot_railway.py"]
