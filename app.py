import streamlit as st
import pandas as pd
from rapidfuzz import fuzz, process
import unicodedata

# ---------- Hilfsfunktionen ----------
def normalize(text):
    if pd.isna(text):
        return ""
    return unicodedata.normalize("NFKD", str(text)).casefold()

def load_data():
    return pd.read_csv("Applichem_Daten.csv")

def load_grundstoffe():
    df = pd.read_csv("Chemikalien_mit_Synonymen_bereinigt_final_no_headers.csv", header=None, names=["Stoff", "Synonyme"])
    df["Synonyme"] = df["Synonyme"].fillna("")
    synonym_map = {}
    for _, row in df.iterrows():
        synonym_map[normalize(row["Stoff"]).strip()] = row["Stoff"]
        for syn in row["Synonyme"].split(","):
            if syn.strip():
                synonym_map[normalize(syn).strip()] = row["Stoff"]
    return synonym_map

def score_product(product_name, query_tokens, grundstoffe_map):
    name = normalize(product_name)
    tokens = name.split()

    base_score = 0
    matching_grundstoff = ""
    for token in tokens:
        if token in grundstoffe_map:
            matching_grundstoff = grundstoffe_map[token]
            base_score += 0.5
            break

    for q in query_tokens:
        if q in name:
            base_score += 0.3
    return base_score, matching_grundstoff

# ---------- Streamlit App ----------
st.set_page_config(layout="wide")
st.title("🔍 Chemikalien-Suche")

applichem_data = load_data()
grudstoffe_map = load_grundstoffe()

user_query = st.text_input("Suchbegriff eingeben", "Toluol HPLC Plus ≥99.9% 1l")
uploaded_file = st.file_uploader("🔁 Optionale Vergleichsliste hochladen (CSV mit Produktnamen)", type="csv")

if st.button("Suchen"):
    with st.spinner("Suche läuft..."):
        query = normalize(user_query)
        query_tokens = query.split()

        results = []
        for _, row in applichem_data.iterrows():
            product_name = str(row["Produktname"])
            score, grundstoff = score_product(product_name, query_tokens, grudstoffe_map)
            if score > 0:
                results.append({
                    "Produktname": product_name,
                    "Grundstoff": grundstoff,
                    "Score": round(score, 2),
                    "Reinheit": row.get("Reinheit", ""),
                    "Verpackungseinheit": row.get("Verpackungseinheit", ""),
                    "Hinweise": row.get("Hinweise", "")
                })

        result_df = pd.DataFrame(results)
        result_df = result_df.sort_values(by="Score", ascending=False)

        st.success(f"{len(result_df)} Treffer gefunden")
        st.dataframe(result_df)

        csv = result_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Ergebnisse als CSV herunterladen",
            data=csv,
            file_name="Suchergebnisse.csv",
            mime="text/csv"
        )
