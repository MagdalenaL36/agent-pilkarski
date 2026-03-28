# ============================================================
#  WPISZ TUTAJ SWOJE DANE
# ============================================================

FOOTBALL_DATA_API_KEY = "eefa8cd3902943429cdca38f0e48e866"
ODDS_API_KEY          = "7f81108b160f6a524bdc339690adae05"

# Gmail — alerty
GMAIL_NADAWCA    = "neo1993@gmail.com"
GMAIL_HASLO_APP  = "kybu rnrn tktx oepg"   # NIE zwykłe hasło — patrz README
GMAIL_ODBIORCA   = "neo1993@gmail.com"

# Ligi do śledzenia
COMPETITIONS = ["PL", "BL1", "SA", "PD", "FL1", "PPL"]

# Value betting
VALUE_THRESHOLD   = 0.04   # min. edge 4%
MIN_MODEL_PROB    = 0.40
MAX_ODDS          = 5.0
MIN_ODDS          = 1.30

# Bankroll
BANKROLL          = 1000.0  # PLN
KELLY_FRACTION    = 0.20
MAX_BET_FRACTION  = 0.03

# Cykl agenta (co ile godzin)
RUN_INTERVAL_HOURS = 6

# Sezony historyczne do treningu modelu
HISTORICAL_SEASONS = [2021, 2022, 2023, 2024]
