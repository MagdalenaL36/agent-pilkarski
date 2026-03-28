# 🤖 Agent Piłkarski — Instrukcja uruchomienia

## Jak ustawić hasło Gmail (WAŻNE!)

Gmail nie pozwala używać zwykłego hasła w kodzie.
Musisz stworzyć specjalne "Hasło aplikacji":

1. Zaloguj się na konto Google
2. Wejdź na: https://myaccount.google.com/security
3. Włącz "Weryfikacja dwuetapowa" (jeśli nie jest włączona)
4. Wróć do Security → szukaj "Hasła aplikacji" (App Passwords)
5. Kliknij → Wybierz aplikację: "Poczta" → Wybierz urządzenie: "Inne"
6. Wpisz nazwę np. "Agent Pilkarski" → Generuj
7. Dostaniesz 16-znakowe hasło (np. abcd efgh ijkl mnop)
8. Wklej to hasło do config.py jako GMAIL_HASLO_APP

## Jak wypełnić config.py

```python
FOOTBALL_DATA_API_KEY = "abc123..."   # z football-data.org
ODDS_API_KEY          = "xyz789..."   # z the-odds-api.com
GMAIL_NADAWCA         = "twoj@gmail.com"
GMAIL_HASLO_APP       = "abcdefghijklmnop"  # 16-znakowe hasło aplikacji
GMAIL_ODBIORCA        = "twoj@gmail.com"    # możesz wysyłać na ten sam email
```

## Jak wgrać na Railway

1. Wgraj wszystkie pliki na GitHub (nowe repozytorium)
2. W Railway: New Project → Deploy from GitHub
3. Wybierz swoje repozytorium
4. Railway automatycznie uruchomi agenta!

## Jak działa samouczenie

```
Agent typuje → zapisuje typ do pending_bets.json
       ↓
Po meczu → sprawdza wynik (fetch_finished_matches)
       ↓
Jeśli błąd → zapisuje do errors_log.json
       ↓
Aktualizuje wagi (error_weights.json)
       ↓
Przy kolejnym typowaniu → koryguje pewność o wagę błędów
       ↓
Wysyła raport weryfikacji emailem
```

## Pliki które tworzy agent

- `history_cache.pkl`  — dane historyczne (odświeżane co tydzień)
- `model.pkl`          — wytrenowany model
- `pending_bets.json`  — typy czekające na weryfikację
- `errors_log.json`    — historia błędów
- `error_weights.json` — wagi korygujące (samouczenie)
