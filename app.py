import csv
import re
from rapidfuzz import fuzz

# --- Konfiguration ---
GRUNDSTOFF_DATEI = "Chemikalien_mit_Synonymen_bereinigt_final_no_headers.csv"

# --- Hilfsfunktionen ---
def lade_grundstoffe(dateipfad):
    grundstoffe = {}
    with open(dateipfad, newline='', encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        for zeile in reader:
            if not zeile:
                continue
            name = zeile[0].strip().lower()
            synonyme = [s.strip().lower() for s in zeile[1:]] if len(zeile) > 1 else []
            grundstoffe[name] = set(synonyme)
    return grundstoffe

def finde_grundstoff(suchtext, grundstoffe):
    suchtext = suchtext.lower()
    for name, synonyme in grundstoffe.items():
        if name in suchtext:
            return name
        for synonym in synonyme:
            if synonym in suchtext:
                return name
    return None

def berechne_score(suchbegriff, produktname, grundstoff):
    score = 0.0
    if grundstoff:
        score += 0.5  # Gewichtung für Grundstoff
    # HPLC und Reinheit als Bonuspunkte
    if re.search(r"hplc", suchbegriff, re.IGNORECASE):
        if "hplc" in produktname.lower():
            score += 0.2
    if re.search(r"\d{2,3}\.\d{1,2}%", suchbegriff):
        reinheit = re.search(r"\d{2,3}\.\d{1,2}%", produktname)
        if reinheit:
            score += 0.2
    score += fuzz.token_sort_ratio(suchbegriff.lower(), produktname.lower()) / 500  # max 0.2
    return min(score, 1.0)

def finde_passende_produkte(suchbegriff, produktdaten, grundstoffe):
    ergebnisse = []
    for produkt in produktdaten:
        produktname = produkt["name"]
        grundstoff = finde_grundstoff(produktname, grundstoffe)
        score = berechne_score(suchbegriff, produktname, grundstoff)
        if score > 0.5:
            ergebnisse.append({
                "Produktname": produktname,
                "Grundstoff": grundstoff,
                "Score": round(score, 2),
                "Abweichungen": "-",
                "Reinheit": produkt.get("reinheit", ""),
                "Verpackungseinheit": produkt.get("verpackung", ""),
                "Hinweise": produkt.get("hinweis", "")
            })
    return sorted(ergebnisse, key=lambda x: x["Score"], reverse=True)

# --- Beispielnutzung ---
if __name__ == "__main__":
    # Beispielproduktdaten für Tests (können ersetzt werden durch echte DB)
    produktdaten = [
        {"name": "Toluol HPLC Plus ≥99.9%", "reinheit": "≥99.9%", "verpackung": "1 L", "hinweis": "HPLC"},
        {"name": "Lycopin Standardlösung 98%", "reinheit": "98%", "verpackung": "1 mg", "hinweis": "Standard"},
        {"name": "Toluol techn. Qualität", "reinheit": "98%", "verpackung": "2.5 L", "hinweis": "technisch"},
    ]
    
    grundstoffe = lade_grundstoffe(GRUNDSTOFF_DATEI)
    suchbegriff = "Toluol HPLC Plus ≥99.9%"
    ergebnisse = finde_passende_produkte(suchbegriff, produktdaten, grundstoffe)
    for e in ergebnisse:
        print(e)
