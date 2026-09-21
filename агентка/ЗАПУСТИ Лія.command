#!/bin/bash
cd "$(dirname "$0")"

echo "Готую Лію до запуску..."

if ! command -v python3 &> /dev/null; then
  echo "Python 3 не знайдено. Встанови його з https://www.python.org/downloads/ і спробуй ще раз."
  read -p "Натисни Enter, щоб закрити вікно..."
  exit 1
fi

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -q -r requirements.txt

python3 bot.py

read -p "Натисни Enter, щоб закрити вікно..."
