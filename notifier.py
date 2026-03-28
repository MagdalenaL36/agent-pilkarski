"""
notifier.py — wysyłanie alertów przez Gmail
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import GMAIL_NADAWCA, GMAIL_HASLO_APP, GMAIL_ODBIORCA


def wyslij_email(temat: str, tresc: str) -> bool:
    try:
        msg = MIMEMultipart()
        msg["From"]    = GMAIL_NADAWCA
        msg["To"]      = GMAIL_ODBIORCA
        msg["Subject"] = temat

        msg.attach(MIMEText(tresc, "plain", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_NADAWCA, GMAIL_HASLO_APP)
            server.send_message(msg)

        print(f"  📧 Email wysłany: {temat}")
        return True
    except Exception as e:
        print(f"  ❌ Błąd emaila: {e}")
        return False


def wyslij_typy(typy: list):
    if not typy:
        wyslij_email(
            "🤖 Agent Piłkarski — Brak typów",
            "Dzisiaj brak value betów spełniających kryteria.\n\nAgent działa poprawnie."
        )
        return

    tresc = "🤖 AGENT PIŁKARSKI — DZISIEJSZE TYPY\n"
    tresc += "=" * 50 + "\n\n"
    tresc += "\n\n---\n\n".join(typy)
    tresc += "\n\n" + "=" * 50
    tresc += "\n⚠️  To jest analiza, nie gwarancja. Graj odpowiedzialnie!"

    wyslij_email(
        f"🤖 Agent Piłkarski — {len(typy)} typ(ów) na dziś",
        tresc
    )


def wyslij_weryfikacje(raport: str):
    wyslij_email("📊 Agent Piłkarski — Weryfikacja typów", raport)


def wyslij_blad(blad: str):
    wyslij_email("❌ Agent Piłkarski — Błąd", f"Wystąpił błąd:\n\n{blad}")
