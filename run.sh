#!/bin/bash
# WinFlash Pro — Quick launch script (Mac/Linux)
set -e

echo "⚡ WinFlash Pro — Установка зависимостей..."

# Create venv if missing
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo "🚀 Запуск WinFlash Pro..."
python main.py
