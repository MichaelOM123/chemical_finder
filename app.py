import streamlit as st
import pandas as pd
import re
from rapidfuzz import fuzz
from io import StringIO

st.set_page_config(page_title="Chemikalien Produktsuche", layout="centered")
st.title("🔬 Chemikalien Produktsuche")

# Session State init
if 'synonym_data' not in st.session_state:
    st.session_state.synonym_data = pd.DataFrame(columns=['Stoff', 'Synonym'])

# File uploader
st.markdown("### Lade die CSV mit Grundstoffen & Synonymen (optional)")
file = st.file_uploader("CSV mit zwei Spalten: 'Stoff', 'Synonym'", type=['csv'])

if file:
    content = file.read().decode('utf-8')
    df = pd.read_csv(StringIO(content), header=None)
    df.columns = ['Stoff', 'Synonym']
    st.session_state.synonym_data = df
    st.success("Grundstoffliste geladen. Enthaltene Einträge: {}".format(len(df)))

# Produktsucheingabe
st.markdown("### Suchtext eingeben")
suchtext = st.text_input("🔍 Chemikalienname", "Toluol ≥99.9%")
menge = st.text_input("Menge (z. B. 1, 2.5 etc.)", "1")
einheit = st.selectbox("Einheit", ["ml", "l", "g", "kg", ""])

# Produktdaten manuell eingeben (für Demo)
st.markdown("### Liste der Produktnamen (einer pro Zeile)")
produkttext = st.text_area("Produktnamen", """Toluol ≥99.9% 1 l
Toluol HPLC Plus ≥99.9% 2.5 l
Toluol reinst 99.5% 1 l
Ethanol 96% 1 l
""")

produkte = [p.strip() for p in produkttext.split('\n') if p.strip()]

# Hilfsfunktionen

def extrahiere_reinheit(text):
    match = re.search(r"([<>]?=?)\s?(\d{1,3}(\.\d+)?\s?%)", text)
    return match.group(0).replace(" ", "") if match else None

def extrahiere_menge(text):
    match = re.search(r"(\d+(\.\d+)?)(\s)?(ml|l|g|kg)", text.lower())
    if match:
        return match.group(1), match.group(4)
    return None, None

def berechne_score(suchbegriff, produkt, grundstoffe):
    score = 0
    begriffe_gefunden = []
    suchbegriff_lower = suchbegriff.lower()

    for stoff in grundstoffe['Stoff'].unique():
        synonyme = grundstoffe[grundstoffe['Stoff'] == stoff]['Synonym'].tolist()
        if any(syn.lower() in suchbegriff_lower for syn in synonyme + [stoff]):
            score += 1.0
            begriffe_gefunden.append(stoff)
            break

    if extrahiere_reinheit(suchbegriff) and extrahiere_reinheit(suchbegriff) in produkt:
        score += 0.5
    if menge and einheit and f"{menge} {einheit}" in produkt:
        score += 0.5

    return score, ", ".join(begriffe_gefunden) if begriffe_gefunden else "-"

# Suche ausführen
if st.button("🔎 Suchen"):
    if not suchtext:
        st.warning("Bitte einen Suchtext eingeben.")
    else:
        st.markdown("---")
        st.subheader("Ergebnisse")
        df_result = pd.DataFrame(columns=['Produkt', 'Reinheit erkannt', 'Begriffe gefunden', 'Score'])

        for produkt in produkte:
            score, begriffe = berechne_score(suchtext, produkt, st.session_state.synonym_data)
            reinheit = extrahiere_reinheit(produkt)
            df_result = pd.concat([df_result, pd.DataFrame([{
                'Produkt': produkt,
                'Reinheit erkannt': reinheit or "-",
                'Begriffe gefunden': begriffe,
                'Score': round(score, 2)
            }])], ignore_index=True)

        perfekte = df_result[df_result['Score'] >= 1.9]
        abweichungen = df_result[(df_result['Score'] > 0) & (df_result['Score'] < 1.9)]

        if not perfekte.empty:
            st.success("✅ Perfekte Treffer")
            st.dataframe(perfekte)
        if not abweichungen.empty:
            st.warning("⚠️ Treffer mit Abweichungen")
            st.dataframe(abweichungen)
        if perfekte.empty and abweichungen.empty:
            st.error("❌ Keine passenden Treffer gefunden.")
