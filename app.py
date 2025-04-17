import pandas as pd
import difflib
from typing import List, Tuple, Optional

# --- Konfiguration ---
REINHEIT_KEYWORDS = ["HPLC", ">=99.9%", "≥99.9%", "99.9%"]

# --- Hilfsfunktionen ---
def normalize_string(s: str) -> str:
    return s.strip().lower()

def extract_menge(text: str) -> Optional[float]:
    import re
    match = re.search(r"(\d+[\.,]?\d*)\s*(ml|l|liter|litre)", text.lower())
    if match:
        value = float(match.group(1).replace(",", "."))
        einheit = match.group(2)
        if einheit in ["ml"]:
            return value / 1000
        else:
            return value
    return None

def has_reinheit(text: str) -> bool:
    text = text.lower()
    return any(k.lower() in text for k in REINHEIT_KEYWORDS)

def compute_score(product: str, grundstoff: str, reinheit: bool, menge_match: bool) -> float:
    score = 0.0
    if grundstoff in normalize_string(product):
        score += 1.0
    if reinheit:
        score += 0.5
    if menge_match:
        score += 0.5
    return score

# --- Hauptlogik ---
def finde_grundstoff(suchtext: str, grundstoff_liste: pd.DataFrame) -> Optional[str]:
    suchtext_norm = normalize_string(suchtext)
    for _, row in grundstoff_liste.iterrows():
        name = normalize_string(row["Name"])
        synonyme = [normalize_string(s) for s in str(row["Synonyme"]).split(",") if s]
        if name in suchtext_norm or any(syn in suchtext_norm for syn in synonyme):
            return name
    return None

def suche_produkte(suchtext: str, produktdaten: pd.DataFrame, grundstoffe: pd.DataFrame) -> pd.DataFrame:
    grundstoff = finde_grundstoff(suchtext, grundstoffe)
    reinheit_erkannt = has_reinheit(suchtext)
    zielmenge = extract_menge(suchtext)

    ergebnisse = []
    for _, produkt in produktdaten.iterrows():
        produkt_name = produkt["Bezeichnung"]
        produkt_menge = extract_menge(produkt_name)
        menge_match = zielmenge is not None and produkt_menge is not None and abs(produkt_menge - zielmenge) < 0.05

        score = compute_score(produkt_name, grundstoff if grundstoff else "", has_reinheit(produkt_name) or reinheit_erkannt, menge_match)

        if score > 0.0:
            ergebnisse.append({
                "Produkt": produkt_name,
                "Grundstoff": grundstoff,
                "Reinheit erkannt": has_reinheit(produkt_name),
                "Menge erkannt": produkt_menge,
                "Score": round(score, 2)
            })

    df_result = pd.DataFrame(ergebnisse)
    df_result = df_result.sort_values(by="Score", ascending=False).reset_index(drop=True)
    return df_result
