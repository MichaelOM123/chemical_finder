import streamlit as st
import pandas as pd
import re
from rapidfuzz import fuzz

# UI Titel
st.title("🔬 Chemikalien Produktsuche")

# Datei-Uploads
produktdatei = st.file_uploader("📁 Lade die AppliChem Produktliste hoch", type=["csv"])
grundstoff_datei = "Chemikalien_mit_Synonymen_bereinigt_final_no_headers.csv"

# Suchparameter
st.subheader("🔍 Suchtext eingeben")
suchtext = st.text_input("Suchbegriff", placeholder="z. B. Toluol HPLC ≥99.9%")
menge = st.text_input("Menge (z. B. 1, 2.5 etc.)", placeholder="1")
einheit = st.selectbox("Einheit", options=["", "ml", "l", "g", "kg"])

# Hilfsfunktionen
def lade_grundstoffe(pfad):
    df = pd.read_csv(pfad, header=None, names=["Grundstoff", "Synonyme"])
    df["Synonyme"] = df["Synonyme"].fillna("").apply(lambda x: [i.strip().lower() for i in x.split(",") if i.strip()])
    df["Alle"] = df.apply(lambda x: [x["Grundstoff"].lower()] + x["Synonyme"], axis=1)
    return df

def finde_grundstoff(text, grundstoff_df):
    text = text.lower()
    for _, row in grundstoff_df.iterrows():
        for name in row["Alle"]:
            if name in text:
                return row["Grundstoff"], name
    return None, None

def extrahiere_reinheit(text):
    match = re.search(r"(>=|≥|>)\s*([0-9]+\.?[0-9]*)\s*%", text)
    return float(match.group(2)) if match else None

# Suche starten
if st.button("🔎 Suchen") and produktdatei and suchtext:
    produkte = pd.read_csv(produktdatei)
    grundstoffe = lade_grundstoffe(grundstoff_datei)

    # Extrahiere Infos aus Suchtext
    ziel_reinheit = extrahiere_reinheit(suchtext)
    ziel_menge = menge.strip()
    ziel_einheit = einheit.strip()
    ziel_grundstoff, synonym = finde_grundstoff(suchtext, grundstoffe)

    perfekte = []
    abweichungen = []

    for _, row in produkte.iterrows():
        name = str(row.get("Produkt", ""))
        punktzahl = 0
        gefundene = []

        # Grundstoffbewertung
        if ziel_grundstoff and ziel_grundstoff.lower() in name.lower():
            punktzahl += 0.4
            gefundene.append(ziel_grundstoff)
        elif synonym and synonym.lower() in name.lower():
            punktzahl += 0.3
            gefundene.append(synonym)

        # Reinheitsbewertung
        produkt_reinheit = extrahiere_reinheit(name)
        if ziel_reinheit and produkt_reinheit:
            if produkt_reinheit >= ziel_reinheit:
                punktzahl += 0.3
        elif ziel_reinheit:
            pass  # keine Angabe im Produktnamen

        # Mengenbewertung
        if ziel_menge and ziel_menge in name:
            punktzahl += 0.2
        if ziel_einheit and ziel_einheit in name:
            punktzahl += 0.1

        eintrag = {
            "Produkt": name,
            "Code": row.get("Code", ""),
            "Reinheit erkannt": produkt_reinheit if produkt_reinheit else "-",
            "Score": round(punktzahl, 2),
            "Begriffe gefunden": ", ".join(gefundene) if gefundene else "-"
        }

        if punktzahl >= 0.95:
            perfekte.append(eintrag)
        elif punktzahl > 0:
            abweichungen.append(eintrag)

    # Ausgabe
    st.subheader("📋 Ergebnisse")
    if perfekte:
        st.success(f"{len(perfekte)} perfekte Treffer gefunden:")
        st.dataframe(pd.DataFrame(perfekte))
    if abweichungen:
        st.warning("⚠️ Treffer mit Abweichungen")
        st.dataframe(pd.DataFrame(abweichungen))
    if not perfekte and not abweichungen:
        st.error("❌ Keine passenden Treffer gefunden.")
