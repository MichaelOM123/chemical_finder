import streamlit as st
import pandas as pd
import re
from rapidfuzz import fuzz
from io import StringIO

st.set_page_config(page_title="Chemikalien Produktsuche", layout="centered")
st.title("🔬 Chemikalien Produktsuche")

st.markdown("""
#### Lade die CSV mit Grundstoffen & Synonymen hoch
(optional, falls nicht genutzt, erfolgt die Analyse nur anhand des eingegebenen Suchtextes)
""")

# Datei-Upload
grundstoff_file = st.file_uploader("CSV Datei mit Grundstoffen & Synonymen", type=["csv"])

# Suchtextfelder
st.markdown("#### Suchtext eingeben")
suchtext = st.text_input("🔍 Chemikalienname", placeholder="z. B. Toluol ≥99.9%")
menge = st.text_input("Menge (z. B. 1, 2.5 etc.)", placeholder="1")
einheit = st.selectbox("Einheit", options=["", "ml", "l", "g", "kg"])

# Produkttabelle (zum Testen intern geladen, später API/Upload)
st.markdown("#### Liste der Produktnamen (einer pro Zeile)")
produkttabelle = st.text_area("Produktnamen", height=200, placeholder="Produkt 1\nProdukt 2\n...")

# Ergebnisanzeige
if st.button("🔎 Suchen"):
    if not suchtext:
        st.warning("Bitte einen Suchtext eingeben.")
    else:
        # Verarbeite Grundstoff-Datei (falls vorhanden)
        grundstoffe = set()
        synonym_map = {}

        if grundstoff_file:
            df_syn = pd.read_csv(grundstoff_file, header=None, names=["Stoff", "Synonym"])
            for _, row in df_syn.iterrows():
                stoff = row["Stoff"].strip().lower()
                synonym = row["Synonym"].strip().lower()
                grundstoffe.add(stoff)
                synonym_map[synonym] = stoff

        # Produkte vorbereiten
        produkte = [p.strip() for p in produkttabelle.strip().splitlines() if p.strip()]

        def parse_reinheit(text):
            match = re.search(r"([<>]?=?)\s*(\d{1,3}[\.,]?\d{0,2})\s*%", text)
            return float(match.group(2).replace(",", ".")) if match else None

        def clean_text(text):
            return re.sub(r"[^\w\s%\.\-]", "", text.lower())

        suchtext_clean = clean_text(suchtext)
        such_reinheit = parse_reinheit(suchtext)

        results = []

        for produkt in produkte:
            clean_prod = clean_text(produkt)
            score = fuzz.partial_ratio(suchtext_clean, clean_prod) / 100.0

            # Reinheit
            prod_reinheit = parse_reinheit(produkt)
            reinheit_ok = False
            if such_reinheit and prod_reinheit:
                reinheit_ok = prod_reinheit >= such_reinheit

            # Menge + Einheit
            menge_ok = True
            if menge:
                menge_match = re.search(rf"\b{menge}\b", produkt)
                menge_ok = menge_match is not None
            einheit_ok = True
            if einheit:
                einheit_match = re.search(rf"\b{einheit}\b", produkt)
                einheit_ok = einheit_match is not None

            # Grundstoffprüfung
            grundstoff_erkannt = False
            for syn, ziel in synonym_map.items():
                if syn in clean_prod:
                    grundstoff_erkannt = True
                    break
            for stoff in grundstoffe:
                if stoff in clean_prod:
                    grundstoff_erkannt = True
                    break

            # Filter
            if score > 0.3 and menge_ok and einheit_ok:
                results.append({
                    "Produkt": produkt,
                    "Score": round(score, 2),
                    "Reinheit erkannt": f"{prod_reinheit}%" if prod_reinheit else "-",
                    "Reinheit OK": "✅" if reinheit_ok else "❌" if prod_reinheit else "-",
                    "Menge OK": menge_ok,
                    "Einheit OK": einheit_ok,
                    "Grundstoff erkannt": "✅" if grundstoff_erkannt else "❌"
                })

        if not results:
            st.error("❌ Keine passenden Treffer gefunden.")
        else:
            df_result = pd.DataFrame(results)
            df_result = df_result.sort_values(by="Score", ascending=False)
            st.success(f"✅ {len(df_result)} Treffer gefunden")
            st.dataframe(df_result.reset_index(drop=True), use_container_width=True)
