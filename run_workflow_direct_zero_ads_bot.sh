#!/bin/bash
# Прямой запуск Telegram-бота с нулевой толерантностью к рекламе через workflow run_bot
echo "Запуск Telegram-бота с нулевой толерантностью к рекламе..."
export REPLIT_WORKFLOW="run_bot"
python run_direct_zero_ads_bot.py