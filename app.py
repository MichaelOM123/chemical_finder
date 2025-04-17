import streamlit as st
import pandas as pd
import re

APPLICHEM_FILE = "Applichem_Daten.csv"
GRUNDSTOFF_FILE = "Chemikalien_mit_Synonymen_bereinigt_final_no_headers.csv"

# Daten laden
@st.cache_data
def load_applichem():
    return pd.read_csv(APPLICHEM_FILE, sep=None, engine="python", encoding="latin1")

@st.cache_data
def load_grundstoffe():
    df = pd.read_csv(GRUNDSTOFF_FILE, header=None)
    df.columns = ["Grundstoff", "Synonym"]
    df["Synonym"] = df["Synonym"].fillna("")
    return df

# Hilfsfunktionen
def normalize(text):
    return re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()

def extract_mindestgehalt(text):
    text = text.replace("≥", ">=").replace("%", "")
    match = re.search(r"(>=|>)?\s*(\d{2,3}(?:\.\d+)?)", text)
    return float(match.group(2)) if match else None

def gleiche_menge(m1, e1, m2, e2):
    conversion = {
        ("ml", "l"): 0.001,
        ("l", "ml"): 1000,
        ("g", "kg"): 0.001,
        ("kg", "g"): 1000
    }
    if e1 == e2:
        return abs(m1 - m2) < 0.01
    if (e1, e2) in conversion:
        return abs(m1 * conversion[(e1, e2)] - m2) < 0.01
    if (e2, e1) in conversion:
        return abs(m2 * conversion[(e2, e1)] - m1) < 0.01
    return False

def finde_grundstoff(suchtext, grundstoff_df):
    suchtext = normalize(suchtext)
    for _, row in grundstoff_df.iterrows():
        grund = normalize(row["Grundstoff"])
        syn = normalize(row["Synonym"])
        if grund in suchtext or syn in suchtext:
            return row["Grundstoff"]
    return None

def finde_qualitaetsbegriff(suchtext):
    qualitaetsbegriffe = ["hplc", "acs", "iso", "ph eur", "reag", "usp"]
    text = normalize(suchtext)
    return [q for q in qualitaetsbegriffe if q in text]

def finde_treffer(suchbegriff, menge, einheit, df_appli, grundstoff_df):
    menge = float(str(menge).replace(",", "."))
    einheit = einheit.lower()
    text = normalize(suchbegriff)
    
    mindestgehalt = extract_mindestgehalt(suchbegriff)
    grundstoff = finde_grundstoff(suchbegriff, grundstoff_df)
    qual_begriffe = finde_qualitaetsbegriff(suchbegriff)

    perfekte, abweichend = [], []

    for _, row in df_appli.iterrows():
        name = str(row["Deutsche Produktbezeichnung"])
        norm_name = normalize(name)
        menge_db = float(str(row["Menge"]).replace(",", "."))
        einheit_db = str(row["Einheit"]).lower()

        # Bedingung: Grundstoff muss enthalten sein
        if grundstoff and normalize(grundstoff) not in norm_name:
            continue

        # Bedingung: Mindestgehalt muss enthalten sein
        if mindestgehalt:
            gehalt_im_text = extract_mindestgehalt(name)
            if not gehalt_im_text or gehalt_im_text < mindestgehalt:
                continue

        # Bedingung: Qualitätsbegriff muss gefunden werden
        if qual_begriffe and not all(q in norm_name for q in qual_begriffe):
            continue

        # Bedingung: Mengengleichheit
        if gleiche_menge(menge, einheit, menge_db, einheit_db):
            hinweis = "Perfekter Treffer ✅"
            perfekte.append({
                "Produkt": name,
                "Menge": menge_db,
                "Einheit": einheit_db,
                "Code": row["Code"],
                "Hersteller": row["Hersteller"],
                "Hinweis": hinweis
            })
        else:
            hinweis = f"Abweichende Menge: {menge_db} {einheit_db} ⚠️"
            abweichend.append({
                "Produkt": name,
                "Menge": menge_db,
                "Einheit": einheit_db,
                "Code": row["Code"],
                "Hersteller": row["Hersteller"],
                "Hinweis": hinweis
            })

    return pd.DataFrame(perfekte), pd.DataFrame(abweichend)

# UI
st.title("🔬 OMNILAB Chemikalien-Finder")

st.markdown("Gib eine Chemikalie ein oder lade eine Liste hoch.")

# Einzelabfrage
chem = st.text_input("🔎 Chemikalienname inkl. ggf. Mindestgehalt und Qualität")
menge = st.text_input("📦 Menge (z. B. 1, 2.5)")
einheit = st.selectbox("📐 Einheit", ["ml", "l", "g", "kg", "Stk"])

if st.button("Suchen"):
    if chem and menge:
        df_appli = load_applichem()
        grundstoffe = load_grundstoffe()
        res1, res2 = finde_treffer(chem, menge, einheit,_
