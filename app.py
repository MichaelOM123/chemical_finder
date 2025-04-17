import streamlit as st
import pandas as pd
import re

# Dateien laden
@st.cache_data
def load_appli_data():
    return pd.read_csv("Aplichem_Daten.csv", sep=None, engine="python", encoding="latin1")

@st.cache_data
def load_grundstoffe():
    df = pd.read_csv("Chemikalien_mit_Synonymen_bereinigt_final_no_headers.csv", header=None)
    df.columns = ["Grundstoff", "Synonym"]
    return df

# Hilfsfunktionen
def normalize(text):
    return re.sub(r"[^a-z0-9 ]+", " ", str(text).lower()).strip()

def gleiche_menge(m1, e1, m2, e2):
    umrechnung = {
        ("ml", "l"): 0.001,
        ("l", "ml"): 1000,
        ("g", "kg"): 0.001,
        ("kg", "g"): 1000
    }
    if e1 == e2:
        return abs(m1 - m2) < 0.01
    key = (e1, e2)
    if key in umrechnung:
        return abs(m1 * umrechnung[key] - m2) < 0.01
    key = (e2, e1)
    if key in umrechnung:
        return abs(m2 * umrechnung[key] - m1) < 0.01
    return False

def extract_mindestgehalt(text):
    text = text.replace(",", ".")
    match = re.search(r">=?\s?(\d{2,3}(\.\d+)?)", text)
    if match:
        return float(match.group(1))
    return None

def extract_mindestgehalt_from_product(name):
    name = name.replace(",", ".")
    match = re.search(r"(\d{2,3}(\.\d+)?)\s?%", name)
    if match:
        return float(match.group(1))
    return None

# Hauptvergleichsfunktion
def finde_treffer(suchtext, menge, einheit, df_appli, df_grundstoffe):
    suchtext_norm = normalize(suchtext)
    suchbegriffe = suchtext_norm.split()
    mindestgehalt = extract_mindestgehalt(suchtext_norm)
    menge = float(str(menge).replace(",", "."))

    perfekte, abweichende = [], []

    # Liste aller Grundstoffe und Synonyme
    grundstoff_map = {}
    for _, row in df_grundstoffe.iterrows():
        grund = normalize(row["Grundstoff"])
        syn = normalize(row["Synonym"])
        grundstoff_map.setdefault(grund, set()).add(grund)
        grundstoff_map[grund].add(syn)

    # Extrahiere den gesuchten Grundstoff
    gefundene_grundstoffe = []
    for wort in suchbegriffe:
        for grund, synonyme in grundstoff_map.items():
            if wort in synonyme:
                gefundene_grundstoffe.append(grund)

    for _, row in df_appli.iterrows():
        name_raw = str(row["Deutsche Produktbezeichnung"])
        name = normalize(name_raw)
        code = str(row["Code"])
        menge_prod = float(str(row["Menge"]).replace(",", ".")) if not pd.isna(row["Menge"]) else 0
        einheit_prod = str(row["Einheit"]).lower()

        if not gleiche_menge(menge, einheit.lower(), menge_prod, einheit_prod):
            hinweis = f"{menge_prod} {einheit_prod} abweichend ⚠️"
        else:
            hinweis = "Perfekter Treffer ✅"

        produkt_mindestgehalt = extract_mindestgehalt_from_product(name_raw)
        mindest_match = True
        if mindestgehalt is not None:
            if produkt_mindestgehalt is None or produkt_mindestgehalt < mindestgehalt:
                mindest_match = False

        # Trefferprüfung
        if any(g in name for g in gefundene_grundstoffe):
            ergebnis = {
                "Produkt": name_raw,
                "Code": code,
                "Hersteller": row["Hersteller"],
                "Menge": menge_prod,
                "Einheit": einheit_prod,
                "Hinweis": hinweis,
                "Mindestgehalt": produkt_mindestgehalt if produkt_mindestgehalt else "-"
            }
            if hinweis == "Perfekter Treffer ✅" and mindest_match:
                perfekte.append(ergebnis)
            else:
                abweichende.append(ergebnis)

    return pd.DataFrame(perfekte), pd.DataFrame(abweichende)


# Streamlit UI
st.title("🔬 Chemikalien-Suchtool")

suchtext = st.text_input("🔍 Chemikalienname", placeholder="z. B. Toluol ≥99.9%")
menge = st.text_input("Menge (z. B. 1, 2.5 etc.)", value="1")
einheit = st.selectbox("Einheit", ["ml", "l", "g", "kg", "Stk"])

if st.button("Suchen"):
    try:
        df_appli = load_appli_data()
        df_grundstoffe = load_grundstoffe()
        df_perfekt, df_abw = finde_treffer(suchtext, menge, einheit, df_appli, df_grundstoffe)

        if not df_perfekt.empty:
            st.markdown("### ✅ Perfekte Treffer")
            st.dataframe(df_perfekt, use_container_width=True)

        if not df_abw.empty:
            st.markdown("### ⚠️ Treffer mit Abweichungen")
            st.dataframe(df_abw, use_container_width=True)

        if df_perfekt.empty and df_abw.empty:
            st.warning("❌ Keine passenden Produkte gefunden.")

    except Exception as e:
        st.error(f"Fehler: {e}")
