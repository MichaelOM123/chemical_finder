import pandas as pd
import streamlit as st
import difflib
import re

st.set_page_config(page_title="Chemikalien Produktsuche", layout="centered")
st.title("🧪 Chemikalien Produktsuche")

# Datei-Upload: CSV mit Grundstoffen & Synonymen
st.subheader("Lade die CSV mit Grundstoffen & Synonymen")
synonym_file = st.file_uploader("", type="csv")

# Eingabe: Produktliste
st.subheader("Liste der Produktnamen (einer pro Zeile)")
product_input = st.text_area("", height=200)

# Eingabe: Suchtext
st.subheader("Suchtext eingeben")
search_query = st.text_input("", placeholder="z. B. Toluol HPLC Plus ≥99.9% 1 l")

# Funktion zur Vereinfachung von Text
def normalize(text):
    return re.sub(r"[^a-z0-9%mlg\.\+]+", " ", text.lower())

# Funktion: Suche nach Grundstoff & Synonymen
def find_base_substance(text, synonyms_df):
    text = normalize(text)
    best_match = (None, 0.0)
    for _, row in synonyms_df.iterrows():
        names = [row['Grundstoff']] + str(row['Synonym']).split(',')
        for name in names:
            name = name.strip().lower()
            if not name:
                continue
            score = difflib.SequenceMatcher(None, name, text).ratio()
            if score > best_match[1]:
                best_match = (row['Grundstoff'], score)
    return best_match

# Funktion: Reinheit extrahieren (z. B. 99.9)
def extract_purity(text):
    match = re.search(r"(\d{2,3}[\.,]\d+)%", text)
    return float(match.group(1).replace(',', '.')) if match else None

# Funktion: Volumen extrahieren (z. B. 1 l)
def extract_volume(text):
    match = re.search(r"(\d+(\.\d+)?)\s*(ml|l|g|kg)", text.lower())
    return match.group(0) if match else None

if synonym_file and product_input and search_query:
    synonyms_df = pd.read_csv(synonym_file, header=None, names=["Grundstoff", "Synonym"])
    search_text = normalize(search_query)
    
    # Extrahiere relevante Parameter
    target_substance, base_score = find_base_substance(search_text, synonyms_df)
    target_purity = extract_purity(search_query)
    target_volume = extract_volume(search_query)

    products = [line.strip() for line in product_input.split("\n") if line.strip()]

    st.markdown("---")
    st.subheader("Ergebnisse:")

    results = []
    for product in products:
        norm_product = normalize(product)
        base_match, score = find_base_substance(norm_product, synonyms_df)

        if base_match != target_substance:
            continue

        purity = extract_purity(product)
        volume = extract_volume(product)

        purity_score = 1.0 if (purity is None or (target_purity and purity >= target_purity)) else 0.5
        volume_score = 1.0 if (not target_volume or (volume and target_volume in volume)) else 0.5

        final_score = round((score + purity_score + volume_score) / 3, 3)

        if final_score > 0:
            results.append((product, final_score, volume or '-', purity or '-'))

    results = sorted(results, key=lambda x: x[1], reverse=True)

    if results:
        for prod, score, vol, pur in results:
            st.markdown(f"**🔹 {prod}**  ")
            st.markdown(f"→ Score: `{score}` | Volumen: `{vol}` | Reinheit: `{pur}`")
            st.markdown("---")
    else:
        st.info("Keine passenden Produkte gefunden.")
