import pandas as pd
import streamlit as st
import re
from io import StringIO
from rapidfuzz import fuzz

st.set_page_config(page_title="Chemikalien Produktsuche")
st.title("🔬 Chemikalien Produktsuche")

st.markdown("""
**Lade die CSV mit Grundstoffen & Synonymen**
""")
grundstoff_file = st.file_uploader("", type=["csv", "xlsx"])

# Eingabefelder
produkttext = st.text_input("🔍 Chemikalienname", "Toluol ≥99.9%")
menge = st.text_input("Menge (z. B. 1, 2,5 etc.)", "1")
einheit = st.selectbox("Einheit", ["ml", "l", "g", "kg", "mg"], index=1)

suchbegriffe = []
grundstoffe = set()
synonyme_map = {}

# Schritt 1: CSV vorbereiten
if grundstoff_file is not None:
    stringio = StringIO(grundstoff_file.getvalue().decode("utf-8"))
    df_grundstoffe = pd.read_csv(stringio, header=None, names=["Grundstoff", "Synonym"])

    for _, row in df_grundstoffe.iterrows():
        grundstoff = str(row["Grundstoff"]).strip().lower()
        synonym = str(row["Synonym"]).strip().lower()

        grundstoffe.add(grundstoff)
        if synonym != "nan" and synonym != "":
            synonyme_map[synonym] = grundstoff

    # Alle Synonyme ebenfalls als Grundstoff behandeln
    grundstoffe.update(synonyme_map.keys())

# Beispielproduktliste (diese könntest du auch aus Datei laden)
produkte = [
    "Toluol HPLC Plus ≥99.9% 1 l",
    "Toluol techn. Qualität 99% 1 l",
    "Toluol reinst 99.95% 2.5 l",
    "Methanol reinst 99.9% 1 l",
    "Benzol für Analyse 99.9% 1 l"
]

# Suche starten
if st.button("🔎 Suchen") and grundstoff_file is not None:
    suchtext = produkttext.strip().lower()
    extrahierte_grundstoffe = set()
    erkannte_reinheit = None
    erkannte_menge = None
    erkannte_einheit = einheit.lower()

    # Reinheit erkennen
    match = re.search(r"(≥|>=)\s*(\d{2,3}\.\d+)%", suchtext)
    if match:
        erkannte_reinheit = float(match.group(2))

    # Grundstoffe erkennen
    for wort in re.findall(r"\w+", suchtext):
        wort = wort.strip().lower()
        if wort in grundstoffe:
            extrahierte_grundstoffe.add(synonyme_map.get(wort, wort))

    # Menge erkennen
    menge_match = re.search(r"(\d+[\.,]?\d*)\s*" + re.escape(einheit), suchtext)
    if menge_match:
        try:
            erkannte_menge = float(menge_match.group(1).replace(",", "."))
        except:
            erkannte_menge = None

    perfekte_treffer = []
    abweichungen = []

    for produkt in produkte:
        ptext = produkt.lower()
        p_score = fuzz.token_sort_ratio(ptext, suchtext)
        p_einheit_match = re.search(r"(\d+[\.,]?\d*)\s*(ml|l|g|kg|mg)", ptext)
        p_menge = None
        p_einheit = None

        if p_einheit_match:
            try:
                p_menge = float(p_einheit_match.group(1).replace(",", "."))
                p_einheit = p_einheit_match.group(2)
            except:
                pass

        p_reinheit_match = re.search(r"(\d{2,3}\.\d+)%", ptext)
        p_reinheit = float(p_reinheit_match.group(1)) if p_reinheit_match else None

        enthielt_grundstoff = any(g in ptext for g in extrahierte_grundstoffe)
        menge_match = (erkannte_menge == p_menge and erkannte_einheit == p_einheit)
        reinheit_match = (p_reinheit is not None and erkannte_reinheit is not None and p_reinheit >= erkannte_reinheit)

        produkt_info = {
            "Produkt": produkt,
            "Score": round(p_score / 100, 2),
            "Grundstoff gefunden": "✅" if enthielt_grundstoff else "❌",
            "Reinheit erkannt": f"{p_reinheit}%" if p_reinheit else "-",
            "Menge erkannt": f"{p_menge} {p_einheit}" if p_menge else "-"
        }

        if enthielt_grundstoff and menge_match and reinheit_match:
            perfekte_treffer.append(produkt_info)
        else:
            abweichungen.append(produkt_info)

    st.markdown("""
    ### ✅ Perfekte Treffer
    """)
    st.dataframe(pd.DataFrame(perfekte_treffer))

    st.markdown("""
    ### ⚠️ Treffer mit Abweichungen
    """)
    st.dataframe(pd.DataFrame(abweichungen))
