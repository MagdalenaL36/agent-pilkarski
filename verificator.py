"""
verificator.py — sprawdza wyniki poprzednich typów i wyciąga wnioski
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from data_fetcher import fetch_finished_matches
from model import log_error, analyze_errors, update_error_weights

PENDING_BETS_PATH = Path("pending_bets.json")


def zapisz_oczekujace_typy(typy: list):
    """Zapisuje dzisiejsze typy do weryfikacji"""
    pending = load_pending()
    pending.extend(typy)
    with open(PENDING_BETS_PATH, "w") as f:
        json.dump(pending, f, indent=2, ensure_ascii=False)
    print(f"  💾 Zapisano {len(typy)} typów do weryfikacji")


def load_pending() -> list:
    if PENDING_BETS_PATH.exists():
        with open(PENDING_BETS_PATH) as f:
            return json.load(f)
    return []


def weryfikuj_typy() -> str:
    """Sprawdza wyniki poprzednich typów"""
    pending = load_pending()
    if not pending:
        return "Brak typów do weryfikacji."

    # Pobierz wyniki z ostatnich 7 dni
    date_from = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    date_to   = datetime.utcnow().strftime("%Y-%m-%d")
    finished  = fetch_finished_matches(date_from, date_to)

    if finished.empty:
        return "Brak zakończonych meczów do weryfikacji."

    verified   = []
    still_pending = []
    wins = 0
    losses = 0

    for bet in pending:
        # Szukaj meczu w wynikach
        match = _find_match(finished, bet["home_team"], bet["away_team"])

        if match is None:
            still_pending.append(bet)
            continue

        actual_result = match["result"]
        predicted     = bet["outcome"]
        correct       = (actual_result == predicted)

        if correct:
            wins += 1
        else:
            losses += 1
            # Zapisz błąd do logu — agent się uczy
            log_error(
                match=bet,
                predicted=predicted,
                actual=actual_result,
                proba=bet.get("proba", {}),
                odds=bet.get("odds", {}),
            )

        verified.append({
            **bet,
            "actual":  actual_result,
            "correct": correct,
        })

    # Zaktualizuj wagi po weryfikacji
    if losses > 0:
        update_error_weights()

    # Zostaw tylko nierozstrzygnięte
    with open(PENDING_BETS_PATH, "w") as f:
        json.dump(still_pending, f, indent=2, ensure_ascii=False)

    # Generuj raport
    raport = _generuj_raport(verified, wins, losses)
    return raport


def _find_match(finished: pd.DataFrame, home: str, away: str):
    """Dopasowuje mecz po nazwie drużyny"""
    h_key = home.split()[0].lower()
    a_key = away.split()[0].lower()

    mask = (
        finished["home_team"].str.lower().str.contains(h_key, na=False) &
        finished["away_team"].str.lower().str.contains(a_key, na=False)
    )
    result = finished[mask]
    if not result.empty:
        return result.iloc[0].to_dict()
    return None


def _generuj_raport(verified: list, wins: int, losses: int) -> str:
    if not verified:
        return "Brak zweryfikowanych typów."

    total     = wins + losses
    skutecznosc = (wins / total * 100) if total > 0 else 0

    raport = f"""
📊 WERYFIKACJA TYPÓW AGENTA
{"=" * 40}

✅ Trafione: {wins}/{total} ({skutecznosc:.1f}%)
❌ Chybione: {losses}/{total}

SZCZEGÓŁY:
"""
    for v in verified:
        ikona = "✅" if v["correct"] else "❌"
        raport += f"\n{ikona} {v['home_team']} vs {v['away_team']}"
        raport += f"\n   Typowałem: {v['outcome']} | Rzeczywistość: {v['actual']}"
        if not v["correct"]:
            raport += f"\n   → Błąd zapisany, model wyciągnie wnioski"
        raport += "\n"

    # Dodaj analizę błędów
    raport += f"\n{'=' * 40}\n"
    raport += analyze_errors()

    return raport.strip()
