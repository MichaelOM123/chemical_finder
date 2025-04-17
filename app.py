import streamlit as st
import pandas as pd
import re
from rapidfuzz import fuzz, process

st.set_page_config(page_title="Chemikalien Produktsuche", layout="centered")
st.title("🔬 Chemikalien Produktsuche")

# Dateiupload für CSV mit Grundstoffen und Synonymen
st.markdown("### 📂 Lade die CSV mit Grundstoffen & Synonymen hoch (optional)")

synonym_csv = st.file_uploader("CSV-Datei auswählen", type=["csv"])
synonyms_df = pd.DataFrame(columns=["Grundstoff", "Synonym"])

if synonym_csv is not None:
    synonyms_df = pd.read_csv(synonym_csv, names=["Grundstoff", "Synonym"], encoding="utf-8")
    synonyms_df.dropna(inplace=True)

# Suchfeld für Nutzereingabe
st.markdown("### 🔍 Suchtext eingeben")
suchtext = st.text_input("Suchbegriff", placeholder="z.B. Toluol HPLC Plus ≥99.9% 1 l")
menge = st.text_input("Menge (z. B. 1, 2.5 etc.)", placeholder="1")
einheit = st.selectbox("Einheit", ["l", "ml", "g", "mg"], index=0)

# Produktdatenbank simuliert (hier kannst du deine Produktliste laden)
produktdaten = pd.DataFrame([
    {"Produkt": "Toluol HPLC Plus ≥99.9%", "Menge": "1", "Einheit": "l", "Code": "123456"},
    {"Produkt": "Methanol HPLC 99.8%", "Menge": "1", "Einheit": "l", "Code": "654321"},
    {"Produkt": "Ethanol absolut für HPLC", "Menge": "1", "Einheit": "l", "Code": "987654"},
    {"Produkt": "Toluol techn. 98%", "Menge": "2.5", "Einheit": "l", "Code": "121212"},
])

st.markdown("### 🔍 Ergebnisse")

if st.button("Suchen") and suchtext:
    def extrahiere_reinheit(text):
        match = re.search(r"(\d{2,3}[\.,]?\d{0,2})\s*%", text)
        return float(match.group(1).replace(",", ".")) if match else None

    def finde_grundstoff(text):
        for _, row in synonyms_df.iterrows():
            if row["Synonym"].lower() in text.lower():
                return row["Grundstoff"]
        return text.split()[0]

    ziel_reinheit = extrahiere_reinheit(suchtext)
    grundstoff = finde_grundstoff(suchtext)

    ergebnisse = []
    for _, row in produktdaten.iterrows():
        name = row["Produkt"]
        score = fuzz.partial_ratio(grundstoff.lower(), name.lower()) / 100

        produkt_reinheit = extrahiere_reinheit(name)
        rein_ok = ziel_reinheit is None or (produkt_reinheit and produkt_reinheit >= ziel_reinheit)

        menge_ok = (menge.strip() == row["Menge"].strip()) if menge else True
        einheit_ok = (einheit.strip() == row["Einheit"].strip()) if einheit else True

        if score > 0.6 and rein_ok and menge_ok and einheit_ok:
            ergebnisse.append({
                "Produkt": name,
                "Code": row["Code"],
                "Reinheit erkannt": produkt_reinheit or "-",
                "Score": round(score, 2)
            })

    if ergebnisse:
        df_result = pd.DataFrame(ergebnisse)
        df_result = df_result.sort_values(by="Score", ascending=False)
        st.success(f"{len(ergebnisse)} Treffer gefunden:")
        st.dataframe(df_result)
    else:
        st.error("❌ Keine passenden Treffer gefunden.")
