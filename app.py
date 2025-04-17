import streamlit as st
import pandas as pd
from rapidfuzz import fuzz
import re

# Dateinamen
APPLICHEM_FILE = "Applichem_Daten.csv"
GRUNDSTOFF_FILE = "Chemikalien_mit_Synonymen_bereinigt_final_no_headers.csv"

# Daten einlesen mit explizitem Trennzeichen
def load_applichem_data():
    return pd.read_csv(APPLICHEM_FILE, sep=";", encoding="utf-8", on_bad_lines="skip")

def load_grundstoffe():
    df = pd.read_csv(GRUNDSTOFF_FILE, sep=";", encoding="utf-8", header=None)
    df.columns = ["Grundstoff", "Synonym"]
    df = df.dropna()
    return df

def finde_grundstoffe(text, grundstoffe_df):
    text_lower = text.lower()
    matches = []
    for _, row in grundstoffe_df.iterrows():
        begriff = str(row["Grundstoff"]).lower()
        synonym = str(row["Synonym"]).lower()
        if begriff in text_lower or synonym in text_lower:
            matches.append(begriff)
    return matches

def berechne_score(row, suchtext, grundstoffe_df):
    name = str(row["Bezeichnung"]).lower()
    suchtext = suchtext.lower()
    score = fuzz.token_sort_ratio(name, suchtext) / 100

    # Grundstoff-Matching prüfen
    grundstofftreffer = finde_grundstoffe(name, grundstoffe_df)
    if grundstofftreffer:
        score += 0.3  # Bonus für enthaltenen Grundstoff

    # Reinheit bewerten
    if re.search(r"99[.,]?9%", name) and ("99.9" in suchtext or "hplc" in suchtext):
        score += 0.1

    # Verpackungseinheit prüfen (z. B. 1 L)
    if re.search(r"\b1 ?l\b", name) and "1 l" in suchtext:
        score += 0.1

    return min(score, 1.0)

def filtere_ergebnisse(df, suchtext, grundstoffe_df):
    df = df.copy()
    df["Score"] = df.apply(lambda row: berechne_score(row, suchtext, grundstoffe_df), axis=1)
    df = df[df["Score"] > 0.2]  # nur sinnvolle Treffer
    return df.sort_values(by="Score", ascending=False)

# UI
st.title("🔬 Chemikalien Produktsuche")
suchtext = st.text_input("Suchbegriff eingeben", "Toluol HPLC Plus ≥99.9% 1 L")

# Daten vorbereiten
try:
    df_appli = load_applichem_data()
    df_grundstoffe = load_grundstoffe()
except FileNotFoundError:
    st.error("Die Datei 'Applichem_Daten.csv' oder die Grundstoffliste wurde nicht gefunden. Bitte stelle sicher, dass beide im selben Verzeichnis liegen.")
    st.stop()

# Suche starten
if st.button("🔎 Suchen"):
    treffer = filtere_ergebnisse(df_appli, suchtext, df_grundstoffe)

    if treffer.empty:
        st.warning("Kein passender Treffer gefunden.")
    else:
        st.success(f"{len(treffer)} Treffer gefunden:")
        st.dataframe(treffer[["Artikelnummer", "Bezeichnung", "Score"]])
