import streamlit as st
import pandas as pd
import re
from rapidfuzz import fuzz

# Hilfsfunktion zur Extraktion von Reinheit
def extract_purity(text):
    match = re.search(r"(\d{2,3}\.\d{1,2}|\d{2,3})\s*%", text)
    if match:
        return float(match.group(1).replace(",", "."))
    return None

# Hilfsfunktion zur Scoring-Berechnung
def score_entry(entry, suchbegriff, grundstoffe, menge, einheit):
    score = 0
    name = entry["Produkt"].lower()
    gefunden = []
    
    # 1. Grundstoffprüfung
    for gs in grundstoffe:
        if gs.lower() in name:
            score += 1.0
            gefunden.append(gs)
            break

    # 2. Reinheit (wenn vorhanden)
    reinheit_suche = extract_purity(suchbegriff)
    reinheit_entry = extract_purity(name)
    if reinheit_suche and reinheit_entry:
        if reinheit_entry >= reinheit_suche:
            score += 0.5

    # 3. Menge und Einheit
    if menge and einheit:
        menge_pattern = rf"\b{menge}\s*{einheit}\b"
        if re.search(menge_pattern, name):
            score += 0.3

    return round(score, 2), ", ".join(gefunden)

# UI Aufbau
st.title("🔬 Chemikalien Produktsuche")

uploaded_file = st.file_uploader("📄 Lade die CSV mit Grundstoffen & Synonymen", type=["csv"])
grundstoffe = []

if uploaded_file is not None:
    df_grundstoffe = pd.read_csv(uploaded_file)
    for _, row in df_grundstoffe.iterrows():
        grundstoffe.append(row["Name"])
        if pd.notna(row["Synonym"]):
            grundstoffe.append(row["Synonym"])

suchbegriff = st.text_input("🔍 Chemikalienname", "Toluol ≥99.9%")
menge = st.text_input("Menge (z. B. 1, 2.5 etc.)", "1")
einheit = st.selectbox("Einheit", ["", "ml", "l", "g", "kg"])

st.markdown("**Liste der Produktnamen (einer pro Zeile)**")
produktliste_input = st.text_area("Produktnamen", height=200)
produktnamen = [x.strip() for x in produktliste_input.split("\n") if x.strip()]

if st.button("🔍 Suchen") and suchbegriff:
    if not produktnamen:
        st.warning("Bitte Produktnamen eingeben.")
    else:
        treffer = []
        for i, name in enumerate(produktnamen):
            eintrag = {"Produkt": name}
            score, begriffe = score_entry(eintrag, suchbegriff, grundstoffe, menge, einheit)
            if score >= 1.0:
                typ = "Perfekter Treffer"
            elif score > 0:
                typ = "Treffer mit Abweichungen"
            else:
                continue
            treffer.append({"Nr": i, "Produkt": name, "Score": score, "Typ": typ, "Begriffe gefunden": begriffe})

        if not treffer:
            st.error("❌ Keine passenden Treffer gefunden.")
        else:
            df_treffer = pd.DataFrame(treffer)
            df_perfekt = df_treffer[df_treffer["Typ"] == "Perfekter Treffer"]
            df_abweichung = df_treffer[df_treffer["Typ"] == "Treffer mit Abweichungen"]

            if not df_perfekt.empty:
                st.success("✅ Perfekte Treffer")
                st.dataframe(df_perfekt.drop(columns="Typ"))

            if not df_abweichung.empty:
                st.warning("⚠️ Treffer mit Abweichungen")
                st.dataframe(df_abweichung.drop(columns="Typ"))
