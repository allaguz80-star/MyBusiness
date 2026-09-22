#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Лія — агентка-коуч у Telegram. Мозок — Claude Code (claude -p), пам'ять — .md файли поруч."""

from __future__ import annotations

import datetime
import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
CONFIG_EXAMPLE_PATH = BASE_DIR / "config.example.json"
OSOBYSTIST_PATH = BASE_DIR / "ОСОБИСТІСТЬ.md"
CIL_PATH = BASE_DIR / "ЦІЛЬ-КУРСУ.md"
JOURNAL_PATH = BASE_DIR / "ЖУРНАЛ.md"

CLAUDE_TIMEOUT_SEC = 90
JOURNAL_TAIL_LINES = 60
JOURNAL_ENTRY_MAX_CHARS = 500

FIRST_MEETING_PROMPT = (
    "(Це перший запуск бота. Привітайся тепло, у 2-3 реченнях скажи, що ти зрозуміла "
    "про мене з моєї конституції, і постав ОДНЕ питання: яка моя головна ціль на цей "
    "курс, одним реченням, з цифрою чи конкретним результатом.)"
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("liia-bot")


def load_config() -> dict:
    if not CONFIG_PATH.exists() and CONFIG_EXAMPLE_PATH.exists():
        shutil.copy(CONFIG_EXAMPLE_PATH, CONFIG_PATH)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(cfg: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def journal_tail(n: int) -> str:
    if not JOURNAL_PATH.exists():
        return ""
    lines = JOURNAL_PATH.read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[-n:])


def append_journal(agent_name: str, her_text: str, agent_text: str) -> None:
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    her_short = her_text.strip().replace("\n", " ")[:JOURNAL_ENTRY_MAX_CHARS]
    agent_short = agent_text.strip().replace("\n", " ")[:JOURNAL_ENTRY_MAX_CHARS]
    with open(JOURNAL_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n{ts}\nВона: {her_short}\n{agent_name}: {agent_short}\n")


def build_context(agent_name: str) -> str:
    personality = read_text(OSOBYSTIST_PATH)
    goal = read_text(CIL_PATH)
    tail = journal_tail(JOURNAL_TAIL_LINES)
    return (
        f"{personality}\n\n"
        f"## Ціль курсу (файл ЦІЛЬ-КУРСУ.md)\n{goal or '(ще не визначена)'}\n\n"
        f"## Останні записи журналу (пам'ять про минулі розмови)\n{tail or '(журнал ще порожній)'}\n\n"
        f"ВАЖЛИВО: відповідай як {agent_name} прямим текстом у Telegram, 2-5 речень, "
        f"одне питання за раз. Без службових приміток і без згадок, що ти AI-модель "
        f"чи що читаєш якісь файли."
    )


def ask_agent(agent_name: str, user_message: str) -> str | None:
    context = build_context(agent_name)
    try:
        result = subprocess.run(
            [
                "claude", "-p", user_message,
                "--append-system-prompt", context,
                "--restricted",
                "--output-format", "text",
            ],
            capture_output=True,
            text=True,
            timeout=CLAUDE_TIMEOUT_SEC,
            cwd=str(BASE_DIR),
        )
    except subprocess.TimeoutExpired:
        log.warning("claude call timed out")
        return None
    except Exception:
        log.exception("claude call failed")
        return None

    reply = result.stdout.strip()
    if result.returncode != 0 or not reply:
        log.error("claude call returned error (code %s): %s", result.returncode, result.stderr[:500])
        return None
    return reply


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await respond(update, context, synthetic_text=FIRST_MEETING_PROMPT)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await respond(update, context)


async def respond(update: Update, context: ContextTypes.DEFAULT_TYPE, synthetic_text: str | None = None) -> None:
    cfg = context.bot_data["cfg"]
    chat_id = update.effective_chat.id

    if cfg.get("owner_chat_id") is None:
        cfg["owner_chat_id"] = chat_id
        save_config(cfg)
        log.info("Owner chat_id saved: %s", chat_id)
    elif cfg["owner_chat_id"] != chat_id:
        return  # відповідаємо лише власниці

    user_text = synthetic_text or (update.message.text or "").strip()
    if not user_text:
        return

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    agent_name = cfg.get("agent_name", "Лія")
    reply = ask_agent(agent_name, user_text)

    if reply is None:
        reply = "Ой, я на секунду задумалась... Повтори, будь ласка. 💛"
    else:
        journal_entry_her = "(перший запуск)" if synthetic_text else user_text
        append_journal(agent_name, journal_entry_her, reply)

    await update.message.reply_text(reply)


def check_claude_available() -> bool:
    return shutil.which("claude") is not None


def main() -> None:
    cfg = load_config()
    token = cfg.get("bot_token", "")
    if not token or token.startswith("ВСТАВ"):
        print("Токен бота не знайдено в config.json. Встав токен від BotFather у поле bot_token і запусти ще раз.")
        sys.exit(1)

    if not check_claude_available():
        print(
            "Не бачу команду 'claude' у системі. Переконайся, що Claude Code встановлено, "
            "і що хоч раз відкривала його з Terminal / Command Prompt на цьому комп'ютері."
        )
        sys.exit(1)

    app = Application.builder().token(token).build()
    app.bot_data["cfg"] = cfg
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    agent_name = cfg.get("agent_name", "Лія")
    print(f"{agent_name} онлайн і слухає Telegram. Не закривай це вікно — це її «серце».")
    print("Щоб зупинити — закрий це вікно або натисни Ctrl+C.")
    app.run_polling()


if __name__ == "__main__":
    main()
