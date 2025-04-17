import streamlit as st
import pandas as pd
import re
from rapidfuzz import fuzz

# --- Einstellungen ---
APPLICHEM_FILE = "Applichem_Daten.csv"
GRUNDSTOFF_FILE = "Chemikalien_mit_Synonymen_bereinigt_final_no_headers.csv"

# --- Hilfsfunktionen ---
def lade_grundstoffe():
    df = pd.read_csv(GRUNDSTOFF_FILE, header=None, names=["Grundstoff", "Synonyme"])
    synonym_map = {}
    for _, row in df.iterrows():
        alle_namen = [row["Grundstoff"]] + str(row["Synonyme"]).split(",")
        alle_namen = [s.strip().lower() for s in alle_namen if s and s.strip() != ""]
        for name in alle_namen:
            synonym_map[name] = row["Grundstoff"].lower()
    return synonym_map

def parse_suchtext(suchtext):
    reinheit_match = re.search(r"(\d{2,3}(\.\d+)?)[ ]*%", suchtext)
    menge_match = re.search(r"\b(\d+(\.\d+)?)\b", suchtext)
    einheit_match = re.search(r"\b(ml|l|g|kg)\b", suchtext, re.IGNORECASE)
    
    reinheit = float(reinheit_match.group(1)) if reinheit_match else None
    menge = float(menge_match.group(1)) if menge_match else None
    einheit = einheit_match.group(1).lower() if einheit_match else None

    return reinheit, menge, einheit

def berechne_score(suchtext, produktname, grundstoffe, ziel_reinheit, ziel_menge, ziel_einheit):
    suchtext_clean = suchtext.lower()
    produktname_clean = produktname.lower()

    # Grundstoff finden
    gefunden = [stoff for stoff in grundstoffe if stoff in suchtext_clean]
    if not gefunden:
        return 0

    matched_grundstoff = grundstoffe[gefunden[0]]
    if matched_grundstoff not in produktname_clean:
        return 0.1  # schwacher Treffer, Grundstoff nicht im Produktnamen

    # Score aufbauen
    score = 1.0

    if ziel_reinheit and str(ziel_reinheit) not in produktname:
        score -= 0.3

    if ziel_menge and str(int(ziel_menge)) not in produktname:
        score -= 0.2

    if ziel_einheit and ziel_einheit not in produktname_clean:
        score -= 0.2

    score = max(score, 0.0)
    return round(score, 2)

def finde_treffer(suchtext, df, grundstoffe):
    reinheit, menge, einheit = parse_suchtext(suchtext)
    ergebnisse = []

    for _, row in df.iterrows():
        produkt = row["Produkt"]
        score = berechne_score(suchtext, produkt, grundstoffe, reinheit, menge, einheit)

        if score > 0:
            ergebnisse.append({
                "Produkt": produkt,
                "Code": row["Code"],
                "Reinheit erkannt": reinheit if reinheit else "-",
                "Score": score
            })

    return sorted(ergebnisse, key=lambda x: x["Score"], reverse=True)

# --- UI ---
st.set_page_config(page_title="Chemikalien-Suchtool", layout="centered")
st.title("🔍 Chemikalien-Suchtool")

suchtext = st.text_input("Suchbegriff eingeben:", "Toluol HPLC Plus ≥99.9% 1L")

# --- Daten laden ---
try:
    df_appli = pd.read_csv(APPLICHEM_FILE)
    grundstoffe = lade_grundstoffe()
    
    if suchtext:
        treffer = finde_treffer(suchtext, df_appli, grundstoffe)

        if treffer:
            st.success(f"{len(treffer)} Treffer gefunden:")
            st.dataframe(pd.DataFrame(treffer))
        else:
            st.error("❌ Keine passenden Treffer gefunden.")
except FileNotFoundError as e:
    st.error("Die Datei 'Applichem_Daten.csv' oder die Grundstoffliste wurde nicht gefunden. Bitte stelle sicher, dass beide im selben Verzeichnis liegen.")
