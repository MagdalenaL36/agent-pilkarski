"""
notifier.py — wysyłanie alertów przez Telegram
"""

import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def wyslij_telegram(tekst: str) -> bool:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": tekst,
            "parse_mode": "HTML"
        }, timeout=10)
        print(f"  📱 Telegram wysłany")
        return r.status_code == 200
    except Exception as e:
        print(f"  ❌ Błąd Telegram: {e}")
        return False


def wyslij_typy(typy: list):
    if not typy:
        wyslij_telegram("🤖 <b>Agent Piłkarski</b>\nDziś brak value betów.")
        return
    tekst = "🤖 <b>AGENT PIŁKARSKI — TYPY</b>\n\n"
    tekst += "\n\n---\n\n".join(typy)
    tekst += "\n\n⚠️ To analiza, nie gwarancja!"
    wyslij_telegram(tekst)


def wyslij_weryfikacje(raport: str):
    wyslij_telegram(f"📊 <b>Weryfikacja typów</b>\n\n{raport}")


def wyslij_blad(blad: str):
    wyslij_telegram(f"❌ <b>Błąd agenta</b>\n\n{blad[:500]}")
