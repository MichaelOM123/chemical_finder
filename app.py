import streamlit as st
import pandas as pd
from rapidfuzz import fuzz, process

# === FUNKTIONEN ===
@st.cache_data
def load_applichem_data():
    try:
        return pd.read_csv("Applichem_Daten.csv")
    except FileNotFoundError:
        st.error("❌ Die Datei 'Applichem_Daten.csv' wurde nicht gefunden. Bitte stelle sicher, dass sie im gleichen Verzeichnis liegt.")
        return pd.DataFrame()

@st.cache_data
def load_grundstoffliste():
    try:
        df = pd.read_csv("Chemikalien_mit_Synonymen_bereinigt_final_no_headers.csv", names=["Grundstoff", "Synonym"])
        df = df.dropna()
        return df
    except FileNotFoundError:
        st.error("❌ Die Datei mit Grundstoffen wurde nicht gefunden.")
        return pd.DataFrame()

def extrahiere_grundstoffe(text, grundstoffliste):
    kandidaten = []
    for _, row in grundstoffliste.iterrows():
        if str(row["Grundstoff"]).lower() in text.lower() or str(row["Synonym"]).lower() in text.lower():
            kandidaten.append(row["Grundstoff"])
    return list(set(kandidaten))

def berechne_score(produktname, suchbegriff):
    return fuzz.token_sort_ratio(produktname.lower(), suchbegriff.lower()) / 100

# === UI ===
st.title("🔍 Chemikalien-Suchtool")

suchbegriff = st.text_input("Suchbegriff eingeben:", "Toluol HPLC Plus ≥99.9% 1L")

grundstoffliste = load_grundstoffliste()
applichem_data = load_applichem_data()

if suchbegriff and not applichem_data.empty:
    # Grundstoffe extrahieren
    gefundene_grundstoffe = extrahiere_grundstoffe(suchbegriff, grundstoffliste)

    trefferliste = []

    for _, row in applichem_data.iterrows():
        name = str(row["Produktbezeichnung"])
        score = berechne_score(name, suchbegriff)
        enthält_grundstoff = any(gs.lower() in name.lower() for gs in gefundene_grundstoffe)

        if enthält_grundstoff:
            score += 0.3  # Bonus für Grundstoff-Match

        if "≥99.9%" in suchbegriff and "99.9" in name:
            score += 0.2

        if "1L" in suchbegriff or "1 L" in suchbegriff:
            if "1L" in name or "1 L" in name or "1000 ml" in name:
                score += 0.1

        trefferliste.append((name, round(score, 2)))

    # Sortieren
    trefferliste = sorted(trefferliste, key=lambda x: x[1], reverse=True)

    # Anzeigen
    st.subheader("🔎 Suchergebnisse")
    for name, score in trefferliste[:10]:
        st.write(f"**{name}** – Score: `{score}`")

