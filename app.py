import streamlit as st
import pandas as pd
from rapidfuzz import fuzz, process
import re

st.set_page_config(page_title="Chemikalien Produktsuche")
st.title("🔬 Chemikalien Produktsuche")

st.markdown("""
Lade die CSV mit Grundstoffen & Synonymen und gib dann die gewünschten Parameter ein:
""")

# Datei-Upload
uploaded_file = st.file_uploader("Lade die CSV mit Grundstoffen & Synonymen", type=["csv"])
grundstoffe_df = None
if uploaded_file is not None:
    grundstoffe_df = pd.read_csv(uploaded_file, header=None, names=["Grundstoff", "Synonym"])
    grundstoffe_df.dropna(inplace=True)

    # Setze alle Werte in Kleinbuchstaben
    grundstoffe_df["Grundstoff"] = grundstoffe_df["Grundstoff"].str.lower().str.strip()
    grundstoffe_df["Synonym"] = grundstoffe_df["Synonym"].str.lower().str.strip()

    # Mapping: Synonym -> Grundstoff
    synonym_map = pd.Series(grundstoffe_df.Grundstoff.values, index=grundstoffe_df.Synonym).to_dict()
    grundstoff_set = set(grundstoffe_df.Grundstoff.unique())
    synonym_set = set(synonym_map.keys())
else:
    st.warning("Bitte lade eine CSV-Datei mit Grundstoffen & Synonymen hoch.")

# Produkteingabe
st.subheader("Produktliste (ein Produkt pro Zeile)")
produkt_input = st.text_area("Liste der Produktnamen", height=200)

# Suchtext-Eingabe
st.subheader("Suchtext eingeben")
suchbegriff = st.text_input("Chemikalienname")
menge_input = st.text_input("Menge (z. B. 1, 2.5 etc.)")
einheit_input = st.selectbox("Einheit", ["", "ml", "l", "g", "kg"])

# Hilfsfunktion

def finde_grundstoff(text):
    text = text.lower()
    for token in re.findall(r"\w+", text):
        if token in grundstoff_set:
            return token
        if token in synonym_set:
            return synonym_map[token]
    return None

def extrahiere_reinheit(text):
    match = re.search(r"[<>]?=?\s?\d{1,3}(\.\d+)?\s?%", text)
    return match.group(0) if match else "-"

# Produktsuche starten
if st.button("Suchen") and uploaded_file is not None and produkt_input:
    produkte = [p.strip() for p in produkt_input.splitlines() if p.strip()]
    suchbegriff = suchbegriff.lower()
    grundstoff_gesucht = finde_grundstoff(suchbegriff)
    ziel_reinheit = extrahiere_reinheit(suchbegriff)

    treffer = []
    for i, produkt in enumerate(produkte):
        score = fuzz.partial_ratio(suchbegriff, produkt.lower()) / 100
        produkt_grundstoff = finde_grundstoff(produkt)
        produkt_reinheit = extrahiere_reinheit(produkt)
        
        # Einfache Abweichungserkennung
        abweichung = []
        if grundstoff_gesucht and produkt_grundstoff and grundstoff_gesucht != produkt_grundstoff:
            abweichung.append("Grundstoff unterschiedlich")
        if ziel_reinheit != "-" and produkt_reinheit != ziel_reinheit:
            abweichung.append("Reinheit abweichend")
        if menge_input and menge_input not in produkt:
            abweichung.append("Menge abweichend")
        if einheit_input and einheit_input not in produkt:
            abweichung.append("Einheit abweichend")

        treffer.append({
            "#": i,
            "Produktname": produkt,
            "Grundstoff erkannt": produkt_grundstoff or "-",
            "Reinheit erkannt": produkt_reinheit,
            "Score": round(score, 2),
            "Abweichung": ", ".join(abweichung) if abweichung else "-"
        })

    treffer_df = pd.DataFrame(treffer).sort_values(by="Score", ascending=False).reset_index(drop=True)

    st.subheader("🔍 Ergebnisse")
    st.dataframe(treffer_df, use_container_width=True)

elif uploaded_file is None:
    st.info("Bitte lade zuerst die CSV hoch.")
