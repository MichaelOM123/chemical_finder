# Produkt-Suchlogik basierend auf Grundstoff, Reinheit und Menge
import re
import pandas as pd
from difflib import SequenceMatcher

# Lade die Grundstoffliste mit Synonymen (zwei Spalten: 'Name', 'Synonyme')
def load_grundstoffe(pfad):
    df = pd.read_csv(pfad, header=None, names=['Name', 'Synonyme'])
    df['Synonyme'] = df['Synonyme'].fillna('').apply(lambda s: [x.strip() for x in s.split(',') if x.strip()])
    return df

def finde_grundstoff(suchtext, grundstoff_df):
    suchtext_lower = suchtext.lower()
    for _, row in grundstoff_df.iterrows():
        name = row['Name'].lower()
        if name in suchtext_lower:
            return row['Name']
        for synonym in row['Synonyme']:
            if synonym.lower() in suchtext_lower:
                return row['Name']
    return None

def extrahiere_reinheit(suchtext):
    match = re.search(r"([<>]=?)?\s*(\d{1,3}(?:[\.,]\d+)?)[\s%]*", suchtext)
    if match:
        return float(match.group(2).replace(',', '.'))
    if 'hplc' in suchtext.lower():
        return 99.9
    return None

def extrahiere_menge(suchtext):
    match = re.search(r"(\d+(?:[\.,]\d+)?)\s*(ml|l|g|kg)", suchtext.lower())
    if match:
        menge = float(match.group(1).replace(',', '.'))
        einheit = match.group(2)
        return menge, einheit
    return None, None

def berechne_score(suchtext, produkt, grundstoff):
    score = 0.0
    suchtext = suchtext.lower()
    produkt = produkt.lower()

    if grundstoff.lower() in produkt:
        score += 0.5
    ratio = SequenceMatcher(None, suchtext, produkt).ratio()
    score += ratio * 0.4

    such_reinheit = extrahiere_reinheit(suchtext)
    prod_reinheit = extrahiere_reinheit(produkt)
    if such_reinheit and prod_reinheit:
        if prod_reinheit >= such_reinheit:
            score += 0.05

    such_menge, such_einheit = extrahiere_menge(suchtext)
    prod_menge, prod_einheit = extrahiere_menge(produkt)
    if such_menge and prod_menge and such_einheit == prod_einheit:
        if abs(such_menge - prod_menge) < 0.1:
            score += 0.05

    return round(score, 3)

def suche_passende_produkte(suchtext, produktliste, grundstoff_df):
    grundstoff = finde_grundstoff(suchtext, grundstoff_df)
    treffer = []
    for produkt in produktliste:
        score = berechne_score(suchtext, produkt, grundstoff)
        if score > 0:
            treffer.append((produkt, score))
    treffer.sort(key=lambda x: x[1], reverse=True)
    return treffer

# Beispielnutzung:
# grundstoffe = load_grundstoffe("Chemikalien_mit_Synonymen_bereinigt_final_no_headers.csv")
# produktliste = ["Toluol HPLC 99.9% 1 l", "Lichorin Lösung 0.5 %", "Aceton extra rein 500 ml"]
# suchergebnis = suche_passende_produkte("Toluol HPLC Plus ≥99.9% 1 l", produktliste, grundstoffe)
# for produkt, score in suchergebnis:
#     print(f"{produkt} -> Score: {score}")
