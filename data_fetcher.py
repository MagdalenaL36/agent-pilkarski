"""
data_fetcher.py — pobiera dane meczowe i kursy
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from config import FOOTBALL_DATA_API_KEY, ODDS_API_KEY, COMPETITIONS, HISTORICAL_SEASONS
import time


def fetch_historical_matches() -> pd.DataFrame:
    """Pobiera historyczne mecze z football-data.org"""
    all_matches = []
    headers = {"X-Auth-Token": FOOTBALL_DATA_API_KEY}

    for comp in COMPETITIONS:
        for season in HISTORICAL_SEASONS:
            url = f"https://api.football-data.org/v4/competitions/{comp}/matches"
            params = {"season": season, "status": "FINISHED"}
            try:
                r = requests.get(url, headers=headers, params=params, timeout=10)
                if r.status_code == 200:
                    matches = r.json().get("matches", [])
                    all_matches.extend(matches)
                    print(f"  [{comp}] {season}: {len(matches)} meczów")
                time.sleep(0.5)
            except Exception as e:
                print(f"  Błąd {comp} {season}: {e}")

    return _parse_matches(all_matches)


def _parse_matches(raw: list) -> pd.DataFrame:
    rows = []
    for m in raw:
        ft = m.get("score", {}).get("fullTime", {})
        hg, ag = ft.get("home"), ft.get("away")
        if hg is None or ag is None:
            continue
        rows.append({
            "match_id":   m["id"],
            "date":       m["utcDate"][:10],
            "competition":m["competition"]["code"],
            "home_team":  m["homeTeam"]["name"],
            "away_team":  m["awayTeam"]["name"],
            "home_goals": int(hg),
            "away_goals": int(ag),
            "result":     "H" if int(hg) > int(ag) else ("A" if int(ag) > int(hg) else "D"),
        })
    return pd.DataFrame(rows)


def fetch_upcoming_matches(days_ahead: int = 3) -> pd.DataFrame:
    """Nadchodzące mecze"""
    headers = {"X-Auth-Token": FOOTBALL_DATA_API_KEY}
    date_from = datetime.utcnow().strftime("%Y-%m-%d")
    date_to   = (datetime.utcnow() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    rows = []

    for comp in COMPETITIONS:
        url = f"https://api.football-data.org/v4/competitions/{comp}/matches"
        params = {"dateFrom": date_from, "dateTo": date_to, "status": "SCHEDULED"}
        try:
            r = requests.get(url, headers=headers, params=params, timeout=10)
            if r.status_code == 200:
                for m in r.json().get("matches", []):
                    rows.append({
                        "match_id":   m["id"],
                        "date":       m["utcDate"][:10],
                        "utc_time":   m["utcDate"],
                        "competition":m["competition"]["code"],
                        "home_team":  m["homeTeam"]["name"],
                        "away_team":  m["awayTeam"]["name"],
                    })
            time.sleep(0.5)
        except Exception as e:
            print(f"  Błąd upcoming {comp}: {e}")

    return pd.DataFrame(rows) if rows else pd.DataFrame()


def fetch_finished_matches(date_from: str, date_to: str) -> pd.DataFrame:
    """Zakończone mecze (do weryfikacji typów)"""
    headers = {"X-Auth-Token": FOOTBALL_DATA_API_KEY}
    rows = []

    for comp in COMPETITIONS:
        url = f"https://api.football-data.org/v4/competitions/{comp}/matches"
        params = {"dateFrom": date_from, "dateTo": date_to, "status": "FINISHED"}
        try:
            r = requests.get(url, headers=headers, params=params, timeout=10)
            if r.status_code == 200:
                for m in r.json().get("matches", []):
                    ft = m.get("score", {}).get("fullTime", {})
                    hg, ag = ft.get("home"), ft.get("away")
                    if hg is None:
                        continue
                    rows.append({
                        "match_id":   m["id"],
                        "date":       m["utcDate"][:10],
                        "home_team":  m["homeTeam"]["name"],
                        "away_team":  m["awayTeam"]["name"],
                        "home_goals": int(hg),
                        "away_goals": int(ag),
                        "result":     "H" if int(hg) > int(ag) else ("A" if int(ag) > int(hg) else "D"),
                    })
            time.sleep(0.5)
        except Exception as e:
            print(f"  Błąd finished {comp}: {e}")

    return pd.DataFrame(rows) if rows else pd.DataFrame()


def fetch_odds() -> pd.DataFrame:
    """Kursy bukmacherskie"""
    sports = [
        "soccer_epl", "soccer_germany_bundesliga",
        "soccer_italy_serie_a", "soccer_spain_la_liga",
        "soccer_france_ligue_one", "soccer_poland_ekstraklasa"
    ]
    rows = []

    for sport in sports:
        url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
        params = {
            "apiKey":     ODDS_API_KEY,
            "regions":    "eu",
            "markets":    "h2h",
            "oddsFormat": "decimal",
        }
        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 200:
                for event in r.json():
                    home = event["home_team"]
                    away = event["away_team"]
                    for bm in event.get("bookmakers", [])[:1]:
                        for market in bm.get("markets", []):
                            if market["key"] != "h2h":
                                continue
                            out = {o["name"]: o["price"] for o in market["outcomes"]}
                            rows.append({
                                "date":      event["commence_time"][:10],
                                "home_team": home,
                                "away_team": away,
                                "odds_H":    out.get(home),
                                "odds_D":    out.get("Draw"),
                                "odds_A":    out.get(away),
                            })
            time.sleep(0.3)
        except Exception as e:
            print(f"  Błąd odds {sport}: {e}")

    return pd.DataFrame(rows) if rows else pd.DataFrame()
