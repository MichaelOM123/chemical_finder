import streamlit as st
import pandas as pd
from rapidfuzz import fuzz

# === Konfiguration ===
APPLICHEM_FILE = "Applichem_Daten.csv"
GRUNDSTOFF_FILE = "Chemikalien_mit_Synonymen_bereinigt_final_no_headers.csv"

# === Hilfsfunktionen ===
def load_applichem_data():
    return pd.read_csv(APPLICHEM_FILE, sep=";", encoding="utf-8", dtype=str).fillna("")

def load_grundstoff_liste():
    df = pd.read_csv(GRUNDSTOFF_FILE, sep=",", header=None, names=["Grundstoff", "Synonym"], encoding="utf-8")
    df = df.fillna("")
    grundstoffe = set(df["Grundstoff"].str.lower())
    synonyme_map = {}
    for _, row in df.iterrows():
        grund = row["Grundstoff"].strip().lower()
        syn = row["Synonym"].strip().lower()
        if grund:
            synonyme_map.setdefault(grund, set()).add(grund)
        if grund and syn:
            synonyme_map.setdefault(grund, set()).add(syn)
    return grundstoffe, synonyme_map

def ermittle_treffer(produktname, df, grundstoff_synonyme):
    treffer = []
    suchbegriffe = produktname.lower().split()

    for _, row in df.iterrows():
        zeilen_text = " ".join([str(val).lower() for val in row.values])
        score = fuzz.partial_ratio(produktname.lower(), zeilen_text)

        grundstoff_score = 0
        for grundstoff, synonyme in grundstoff_synonyme.items():
            if any(syn in zeilen_text for syn in synonyme):
                grundstoff_score = 100
                break

        reinheit_score = 10 if any("99.9" in val for val in row.values) else 0
        menge_score = 10 if any("1 l" in str(val).lower() or "1l" in str(val).lower() for val in row.values) else 0

        final_score = 0.6 * score + 0.3 * grundstoff_score + 0.05 * reinheit_score + 0.05 * menge_score

        treffer.append({
            "Score": round(final_score, 2),
            "Produktzeile": row.to_dict()
        })

    treffer = sorted(treffer, key=lambda x: x["Score"], reverse=True)
    return treffer

# === Streamlit UI ===
st.set_page_config(page_title="Chemikalien-Finder", layout="wide")
st.title("🔍 Chemikalien Produktsuche")

suchbegriff = st.text_input("Suchbegriff eingeben", "Toluol HPLC Plus ≥99.9% 1 l")

if st.button("Suchen"):
    with st.spinner("Suche wird durchgeführt..."):
        df_appli = load_applichem_data()
        grundstoffe, synonym_map = load_grundstoff_liste()
        treffer = ermittle_treffer(suchbegriff, df_appli, synonym_map)

        if treffer:
            st.success(f"{len(treffer)} Treffer gefunden")
            for eintrag in treffer[:10]:
                st.markdown(f"**Score:** {eintrag['Score']}")
                st.json(eintrag["Produktzeile"])
        else:
            st.warning("Keine passenden Produkte gefunden.")
