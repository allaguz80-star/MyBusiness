#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Подвійний клік по цьому файлу запускає Лію (простіша альтернатива ЗАПУСТИ Лія.bat)."""

import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def pause(message: str = "Натисни Enter, щоб закрити вікно...") -> None:
    try:
        input(message)
    except (EOFError, KeyboardInterrupt):
        pass


def ensure_dependencies() -> None:
    try:
        import telegram  # noqa: F401
        return
    except ImportError:
        pass
    print("Встановлюю потрібні бібліотеки (один раз, це займе хвилину)...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-q", "-r", str(BASE_DIR / "requirements.txt")]
    )


def main() -> None:
    print("Готую Лію до запуску...")
    try:
        ensure_dependencies()
    except Exception as exc:
        print(f"Не вдалося встановити бібліотеки: {exc}")
        pause()
        return

    sys.path.insert(0, str(BASE_DIR))
    try:
        import bot
        bot.main()
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        print(f"Лія не змогла запуститись: {exc}")
        pause()


if __name__ == "__main__":
    main()
