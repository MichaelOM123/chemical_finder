import streamlit as st
import pandas as pd
import re
from rapidfuzz import fuzz

# === Daten laden ===
@st.cache_data
def load_applichem():
    return pd.read_csv("Applichem_Daten.csv", sep=None, engine="python", encoding="latin1")

@st.cache_data
def load_reinheit_mapping():
    return pd.read_csv("reinheit_mapping.csv")

@st.cache_data
def load_grundstoffe():
    df = pd.read_csv("Chemikalien_mit_Synonymen_bereinigt_final_no_headers.csv", header=None)
    df.columns = ["Grundstoff", "Synonym"]
    return df

# === Utils ===
def normalize(text):
    return re.sub(r"[^a-z0-9 ]", " ", str(text).lower()).replace("  ", " ").strip()

def extrahiere_reinheit(suchtext):
    text = suchtext.replace("≥", ">=").replace("%", "")
    match = re.search(r">=?\s?(\d{2,3}(\.\d+)?)", text)
    if match:
        return float(match.group(1))
    return None

def gleiche_menge(menge1, einheit1, menge2, einheit2):
    umrechnung = {
        ("ml", "l"): 0.001,
        ("l", "ml"): 1000,
        ("g", "kg"): 0.001,
        ("kg", "g"): 1000
    }
    if einheit1 == einheit2:
        return abs(menge1 - menge2) < 0.01
    if (einheit1, einheit2) in umrechnung:
        return abs(menge1 * umrechnung[(einheit1, einheit2)] - menge2) < 0.01
    if (einheit2, einheit1) in umrechnung:
        return abs(menge2 * umrechnung[(einheit2, einheit1)] - menge1) < 0.01
    return False

def reinheit_aus_text(text):
    pattern = re.findall(r"(\d{2,3}[\.,]\d+|\d{2,3})\s?%", text.replace(",", "."))
    werte = [float(w.replace(",", ".")) for w in pattern]
    return max(werte) if werte else None

def enthaelt_grundstoff(text, grundstoffe):
    text = normalize(text)
    for _, row in grundstoffe.iterrows():
        if normalize(row["Grundstoff"]) in text or normalize(str(row["Synonym"])) in text:
            return row["Grundstoff"]
    return None

def finde_treffer(user_name, user_menge, user_einheit, df, mapping_df, grundstoffe):
    user_menge = float(str(user_menge).replace(",", "."))
    suchtext = normalize(user_name)
    mindestreinheit = extrahiere_reinheit(suchtext)
    suchbegriffe = re.sub(r">=?\s?\d+(\.\d+)?%?", "", suchtext).split()
    treffer = []
    aehnliche = []

    for _, row in df.iterrows():
        produktname_raw = str(row["Deutsche Produktbezeichnung"])
        produktname = normalize(produktname_raw)

        erkannte_begriffe = []
        erkannte_reinheit = "-"
        gefundene_werte = []

        for _, qual_row in mapping_df.iterrows():
            bez = normalize(qual_row["Bezeichnung"])
            if bez in produktname:
                gefundene_werte.append(qual_row["Mindestwert"])
                erkannte_begriffe.append(bez)

        reinheit_im_namen = reinheit_aus_text(produktname_raw)
        if reinheit_im_namen:
            gefundene_werte.append(reinheit_im_namen)

        if gefundene_werte:
            erkannte_reinheit = max(gefundene_werte)

        try:
            menge = float(str(row["Menge"]).replace(",", "."))
            einheit = str(row["Einheit"]).lower()

            if (einheit == user_einheit.lower()) or gleiche_menge(menge, einheit, user_menge, user_einheit.lower()):
                gemeinsame_begriffe = [b for b in suchbegriffe if b in produktname]
                grundstoff = enthaelt_grundstoff(produktname_raw, grundstoffe)

                if grundstoff and grundstoff in suchtext:
                    hinweis = "Perfekter Treffer ✅"
                    if not gleiche_menge(menge, einheit, user_menge, user_einheit.lower()):
                        hinweis = f"Abweichende Menge ({menge} {einheit}) ⚠️"
                    treffer.append({
                        "Produkt": produktname_raw,
                        "Menge": menge,
                        "Einheit": einheit,
                        "Code": row["Code"],
                        "Hersteller": row["Hersteller"],
                        "Hinweis": hinweis,
                        "Grundstoff erkannt": grundstoff,
                        "Reinheit erkannt": erkannte_reinheit
                    })
                elif isinstance(erkannte_reinheit, (int, float)) and mindestreinheit and erkannte_reinheit >= mindestreinheit:
                    aehnliche.append({
                        "Produkt": produktname_raw,
                        "Menge": menge,
                        "Einheit": einheit,
                        "Code": row["Code"],
                        "Hersteller": row["Hersteller"],
                        "Hinweis": "Alternative mit höherer Reinheit 🔁",
                        "Grundstoff erkannt": grundstoff if grundstoff else "-",
                        "Reinheit erkannt": erkannte_reinheit
                    })
        except:
            continue

    return pd.DataFrame(treffer), pd.DataFrame(aehnliche)

# === UI ===
st.title("🔬 OMNILAB Chemikalien-Finder")

df_appli = load_applichem()
mapping = load_reinheit_mapping()
grs = load_grundstoffe()

st.markdown("Gib hier die gewünschte Chemikalie, Reinheit und Menge ein:")
chem_name = st.text_input("🔎 Chemikalienname", placeholder="z.B. Toluol HPLC Plus ≥99.9%")
menge = st.text_input("Menge", placeholder="z.B. 1")
einh = st.selectbox("Einheit", ["ml", "l", "g", "kg", "Stk"])

if st.button("Suchen"):
    if chem_name and menge:
        res, alt = finde_treffer(chem_name, menge, einh, df_appli, mapping, grs)

        if res.empty and alt.empty:
            st.warning("Keine passenden Produkte gefunden.")
        else:
            if not res.empty:
                st.subheader("✅ Perfekte Treffer")
                st.dataframe(res)
            if not alt.empty:
                st.subheader("🔁 Ähnliche Produkte mit höherer Reinheit")
                st.dataframe(alt)
    else:
        st.warning("Bitte alle Felder ausfüllen.")
