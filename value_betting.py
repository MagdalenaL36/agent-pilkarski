"""
value_betting.py — logika value + Kelly Criterion
"""

from config import VALUE_THRESHOLD, MIN_MODEL_PROB, MAX_ODDS, MIN_ODDS
from config import BANKROLL, KELLY_FRACTION, MAX_BET_FRACTION
from model import load_error_weights


def find_value_bets(proba: dict, odds: dict, competition: str = "") -> list:
    error_weights = load_error_weights()
    bets = []

    for outcome in ["H", "D", "A"]:
        p   = proba.get(outcome)
        odd = odds.get(f"odds_{outcome}")

        if p is None or odd is None:
            continue
        if not (MIN_ODDS <= odd <= MAX_ODDS):
            continue

        # Zastosuj wagę błędu — jeśli ten wynik był często błędny, obniż pewność
        weight = error_weights.get(outcome, 1.0)
        p_adjusted = p * weight

        if p_adjusted < MIN_MODEL_PROB:
            continue

        ev = p_adjusted * odd - 1
        if ev >= VALUE_THRESHOLD:
            kelly = _kelly_stake(p_adjusted, odd)
            bets.append({
                "outcome":      outcome,
                "model_prob":   round(p, 4),
                "adj_prob":     round(p_adjusted, 4),
                "odds":         odd,
                "implied_prob": round(1 / odd, 4),
                "edge":         round(ev, 4),
                "kelly_stake":  kelly,
                "label":        _label(outcome),
                "weight":       round(weight, 3),
            })

    return sorted(bets, key=lambda x: x["edge"], reverse=True)


def _kelly_stake(p, odd):
    b = odd - 1
    kelly_full = (p * b - (1 - p)) / b
    kelly_full = max(kelly_full, 0.0)
    stake = BANKROLL * KELLY_FRACTION * kelly_full
    stake = min(stake, BANKROLL * MAX_BET_FRACTION)
    return round(stake, 2)


def _label(outcome):
    return {
        "H": "Wygrana Gospodarzy 🏠",
        "D": "Remis ⚖️",
        "A": "Wygrana Gości ✈️"
    }[outcome]


def format_bet_email(match: dict, bets: list) -> str:
    if not bets:
        return ""

    lines = [
        f"⚽ {match['home_team']} vs {match['away_team']}",
        f"📅 {match['date']} | 🏆 {match['competition']}",
        "",
    ]
    for b in bets:
        weight_info = f" (korekta błędów: {b['weight']}x)" if b['weight'] != 1.0 else ""
        lines += [
            f"✅ {b['label']}",
            f"   Kurs: {b['odds']} | Pewność modelu: {b['model_prob']*100:.1f}%{weight_info}",
            f"   Edge: +{b['edge']*100:.1f}% | Stawka Kelly: {b['kelly_stake']} PLN",
            "",
        ]
    return "\n".join(lines)
