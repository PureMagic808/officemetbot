import os
import sys

# Установим переменную окружения для запуска бота
os.environ["COMPONENT"] = "bot"

# Запустим main.py, который проверит переменную окружения и запустит бота
import main

