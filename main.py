"""
main.py — główny orchestrator agenta piłkarskiego
Działa 24/7 na Railway/serwerze
"""

import traceback
import schedule
import time
import joblib
from pathlib import Path
from datetime import datetime

from config import RUN_INTERVAL_HOURS, HISTORICAL_SEASONS, COMPETITIONS
from data_fetcher import fetch_historical_matches, fetch_upcoming_matches, fetch_odds
from model import train_model, load_model, predict_match, MODEL_PATH
from value_betting import find_value_bets, format_bet_email
from notifier import wyslij_typy, wyslij_weryfikacje, wyslij_blad
from verificator import weryfikuj_typy, zapisz_oczekujace_typy

CACHE_PATH = Path("history_cache.pkl")


# ── Główna analiza ───────────────────────────────────────────

def run_agent():
    print(f"\n{'='*60}")
    print(f"  🤖 Agent startuje: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    try:
        # 1. Najpierw weryfikuj poprzednie typy
        print("\n🔍 Weryfikuję poprzednie typy...")
        raport_weryfikacji = weryfikuj_typy()
        if "Trafione" in raport_weryfikacji:
            wyslij_weryfikacje(raport_weryfikacji)
            print(raport_weryfikacji)

        # 2. Dane historyczne
        hist_df = _load_or_fetch_history()

        # 3. Model
        model, le = _load_or_train_model(hist_df)

        # 4. Nadchodzące mecze
        print("\n📅 Pobieram nadchodzące mecze...")
        upcoming = fetch_upcoming_matches(days_ahead=3)
        print(f"  Znaleziono: {len(upcoming)} meczów")

        if upcoming.empty:
            wyslij_typy([])
            return

        # 5. Kursy
        print("\n💰 Pobieram kursy...")
        odds_df = fetch_odds()

        # 6. Analiza value
        print("\n🔍 Szukam value betów...")
        wszystkie_typy = []
        typy_do_zapisu = []

        for _, match in upcoming.iterrows():
            proba = predict_match(
                model, le, hist_df,
                match["home_team"], match["away_team"], match["date"]
            )

            match_odds = _match_odds(odds_df, match["home_team"], match["away_team"])
            if match_odds is None:
                continue

            bets = find_value_bets(proba, match_odds, match.get("competition", ""))

            if bets:
                summary = format_bet_email(match.to_dict(), bets)
                wszystkie_typy.append(summary)

                # Zapisz do weryfikacji później
                for b in bets:
                    typy_do_zapisu.append({
                        **match.to_dict(),
                        "outcome": b["outcome"],
                        "odds":    {"odds_H": match_odds.get("odds_H"),
                                    "odds_D": match_odds.get("odds_D"),
                                    "odds_A": match_odds.get("odds_A")},
                        "proba":   proba,
                        "edge":    b["edge"],
                    })

                print(f"  ✅ VALUE: {match['home_team']} vs {match['away_team']}")

        # 7. Zapisz typy do przyszłej weryfikacji
        if typy_do_zapisu:
            zapisz_oczekujace_typy(typy_do_zapisu)

        # 8. Wyślij email
        print(f"\n📧 Wysyłam email ({len(wszystkie_typy)} typów)...")
        wyslij_typy(wszystkie_typy)
        print("  ✅ Gotowe!\n")

    except Exception as e:
        tb = traceback.format_exc()
        print(f"❌ Błąd: {tb}")
        wyslij_blad(tb[:2000])


# ── Helpers ──────────────────────────────────────────────────

def _load_or_fetch_history():
    if CACHE_PATH.exists():
        age_days = (datetime.now() - datetime.fromtimestamp(
            CACHE_PATH.stat().st_mtime)).days
        if age_days < 7:
            print("📂 Historia z cache...")
            return joblib.load(CACHE_PATH)

    print("⬇️  Pobieram dane historyczne...")
    import pandas as pd
    frames = []
    for comp in COMPETITIONS:
        df = fetch_historical_matches()
        frames.append(df)
        break  # fetch_historical_matches już iteruje po wszystkich

    combined = fetch_historical_matches()
    joblib.dump(combined, CACHE_PATH)
    print(f"  Zapisano {len(combined)} meczów")
    return combined


def _load_or_train_model(hist_df):
    retrain_flag = Path("retrain.flag")

    if MODEL_PATH.exists() and not retrain_flag.exists():
        print("🧠 Wczytuję model...")
        return load_model()

    model, le = train_model(hist_df)
    retrain_flag.unlink(missing_ok=True)
    return model, le


def _match_odds(odds_df, home_team, away_team):
    if odds_df.empty:
        return None
    h_key = home_team.split()[0].lower()
    a_key = away_team.split()[0].lower()
    mask = (
        odds_df["home_team"].str.lower().str.contains(h_key, na=False) &
        odds_df["away_team"].str.lower().str.contains(a_key, na=False)
    )
    row = odds_df[mask]
    if row.empty:
        return None
    return row.iloc[0].to_dict()


def _retrain():
    CACHE_PATH.unlink(missing_ok=True)
    Path("retrain.flag").touch()
    print("🔄 Retrain zaplanowany")


# ── Scheduler ────────────────────────────────────────────────

if __name__ == "__main__":
    print("🚀 Agent Piłkarski startuje...")

    # Pierwsze uruchomienie od razu
    run_agent()

    # Co N godzin
    schedule.every(RUN_INTERVAL_HOURS).hours.do(run_agent)

    # Przetrenowanie modelu co poniedziałek
    schedule.every().monday.at("03:00").do(_retrain)

    while True:
        schedule.run_pending()
        time.sleep(60)
