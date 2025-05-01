FROM python:3.10-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем переменную окружения для UTF-8
ENV PYTHONUTF8=1

# Копируем только файлы зависимостей для использования кэширования слоев Docker
COPY requirements.txt .

# Устанавливаем зависимости и очищаем кэш
RUN pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove gcc libffi-dev

# Копируем код приложения
COPY . .

# Запускаем бота
CMD ["python", "bot_railway.py"]
