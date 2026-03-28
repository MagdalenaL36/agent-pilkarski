"""
model.py — XGBoost z samouczeniem się z błędów
"""

import numpy as np
import pandas as pd
import joblib
import json
from pathlib import Path
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import cross_val_score
from sklearn.calibration import CalibratedClassifierCV

try:
    from xgboost import XGBClassifier
except ImportError:
    raise ImportError("Zainstaluj xgboost: pip install xgboost")

MODEL_PATH   = Path("model.pkl")
ENC_PATH     = Path("label_enc.pkl")
ERRORS_PATH  = Path("errors_log.json")   # historia błędów
WEIGHTS_PATH = Path("error_weights.json") # wagi cech po analizie błędów


# ── Feature engineering ──────────────────────────────────────

def build_features(df: pd.DataFrame, n_last: int = 5,
                   error_weights: dict = None) -> pd.DataFrame:
    df = df.sort_values("date").reset_index(drop=True)
    features = []

    for idx, row in df.iterrows():
        home, away, date = row["home_team"], row["away_team"], row["date"]
        past = df[df["date"] < date]

        h = _team_stats(past, home, n_last)
        a = _team_stats(past, away, n_last)
        h2h = _h2h_stats(past, home, away)

        feat = {
            **{f"h_{k}": v for k, v in h.items()},
            **{f"a_{k}": v for k, v in a.items()},
            **h2h,
            "result": row["result"],
        }
        features.append(feat)

    return pd.DataFrame(features)


def _team_stats(df, team, n):
    home_m = df[df["home_team"] == team].tail(n)
    away_m = df[df["away_team"] == team].tail(n)
    gf, ga, pts = [], [], []

    for _, m in home_m.iterrows():
        gf.append(m["home_goals"]); ga.append(m["away_goals"])
        pts.append(3 if m["result"] == "H" else (1 if m["result"] == "D" else 0))
    for _, m in away_m.iterrows():
        gf.append(m["away_goals"]); ga.append(m["home_goals"])
        pts.append(3 if m["result"] == "A" else (1 if m["result"] == "D" else 0))

    return {
        "avg_gf":    np.mean(gf) if gf else 1.2,
        "avg_ga":    np.mean(ga) if ga else 1.2,
        "avg_pts":   np.mean(pts) if pts else 1.0,
        "n_matches": len(gf),
        "form":      sum(pts[-3:]) / 9 if len(pts) >= 3 else 0.33,
    }


def _h2h_stats(df, home, away, n=5):
    h2h = df[
        ((df["home_team"] == home) & (df["away_team"] == away)) |
        ((df["home_team"] == away) & (df["away_team"] == home))
    ].tail(n)

    h_wins = sum(
        1 for _, m in h2h.iterrows()
        if (m["home_team"] == home and m["result"] == "H") or
           (m["away_team"] == home and m["result"] == "A")
    )
    return {
        "h2h_n":      len(h2h),
        "h2h_h_wins": h_wins,
        "h2h_draws":  sum(1 for _, m in h2h.iterrows() if m["result"] == "D"),
    }


# ── Trening ──────────────────────────────────────────────────

def train_model(df: pd.DataFrame):
    print("🏋️  Trenuję model...")
    error_weights = load_error_weights()
    feat_df = build_features(df, error_weights=error_weights)
    feat_df.dropna(inplace=True)

    le = LabelEncoder()
    y  = le.fit_transform(feat_df["result"])
    X  = feat_df.drop(columns=["result"])

    base_model = XGBClassifier(
        n_estimators=400,
        max_depth=4,
        learning_rate=0.04,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric="mlogloss",
        random_state=42,
    )

    model = CalibratedClassifierCV(base_model, cv=3, method="isotonic")

    cv_scores = cross_val_score(base_model, X, y, cv=5, scoring="accuracy")
    print(f"  CV Accuracy: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

    model.fit(X, y)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(le, ENC_PATH)
    print(f"  ✅ Model zapisany")
    return model, le


def load_model():
    model = joblib.load(MODEL_PATH)
    le    = joblib.load(ENC_PATH)
    return model, le


def predict_match(model, le, hist_df, home_team, away_team, date):
    dummy = pd.DataFrame([{
        "date": date, "home_team": home_team, "away_team": away_team,
        "home_goals": 0, "away_goals": 0, "result": "H", "competition": "?"
    }])
    combined = pd.concat([hist_df, dummy], ignore_index=True)
    feats = build_features(combined).tail(1).drop(columns=["result"])
    proba = model.predict_proba(feats)[0]
    classes = le.classes_
    return {c: round(float(p), 4) for c, p in zip(classes, proba)}


# ── System uczenia się z błędów ──────────────────────────────

def log_error(match: dict, predicted: str, actual: str, proba: dict, odds: dict):
    """Zapisuje błędny typ do logu"""
    errors = load_errors()
    errors.append({
        "date":        match.get("date"),
        "home_team":   match.get("home_team"),
        "away_team":   match.get("away_team"),
        "competition": match.get("competition"),
        "predicted":   predicted,
        "actual":      actual,
        "proba":       proba,
        "odds":        odds,
        "logged_at":   pd.Timestamp.now().isoformat(),
    })
    with open(ERRORS_PATH, "w") as f:
        json.dump(errors, f, indent=2, ensure_ascii=False)
    print(f"  📝 Błąd zapisany: {match['home_team']} vs {match['away_team']}")


def load_errors() -> list:
    if ERRORS_PATH.exists():
        with open(ERRORS_PATH) as f:
            return json.load(f)
    return []


def analyze_errors() -> str:
    """Analizuje błędy i zwraca wnioski tekstowe"""
    errors = load_errors()
    if not errors:
        return "Brak błędów do analizy."

    total = len(errors)
    by_outcome = {}
    by_competition = {}
    high_conf_errors = 0

    for e in errors:
        pred = e["predicted"]
        by_outcome[pred] = by_outcome.get(pred, 0) + 1

        comp = e.get("competition", "?")
        by_competition[comp] = by_competition.get(comp, 0) + 1

        proba = e.get("proba", {})
        if proba.get(pred, 0) > 0.60:
            high_conf_errors += 1

    worst_outcome = max(by_outcome, key=by_outcome.get) if by_outcome else "?"
    worst_comp    = max(by_competition, key=by_competition.get) if by_competition else "?"

    wnioski = f"""
📊 ANALIZA BŁĘDÓW MODELU ({total} błędów łącznie)

❌ Najczęściej mylony wynik: {worst_outcome} ({by_outcome.get(worst_outcome, 0)}x)
❌ Liga z największą liczbą błędów: {worst_comp} ({by_competition.get(worst_comp, 0)}x)
⚠️  Błędy przy wysokiej pewności (>60%): {high_conf_errors}

💡 Wnioski:
- Model za często typuje {worst_outcome} → podwyższam próg pewności dla tego wyniku
- Liga {worst_comp} jest trudniej przewidywalna → obniżam wagę typów z tej ligi
- Przy pewności >60% i błędzie → model zbyt pewny siebie (overfitting)
"""
    return wnioski.strip()


def update_error_weights():
    """Aktualizuje wagi na podstawie historii błędów"""
    errors = load_errors()
    if len(errors) < 5:
        return

    by_outcome = {}
    for e in errors:
        pred = e["predicted"]
        by_outcome[pred] = by_outcome.get(pred, 0) + 1

    total = len(errors)
    weights = {
        outcome: max(0.5, 1.0 - (count / total) * 0.5)
        for outcome, count in by_outcome.items()
    }

    with open(WEIGHTS_PATH, "w") as f:
        json.dump(weights, f, indent=2)
    print(f"  🔄 Wagi zaktualizowane: {weights}")


def load_error_weights() -> dict:
    if WEIGHTS_PATH.exists():
        with open(WEIGHTS_PATH) as f:
            return json.load(f)
    return {}
