import streamlit as st
import pandas as pd
import re

# -------------------- Hilfsfunktionen --------------------
def normalize(text):
    return re.sub(r"[^a-z0-9%.,\-\s]", "", str(text).lower())

def gleiche_menge(m1, e1, m2, e2):
    umrechnung = {
        ("ml", "l"): lambda x: x / 1000,
        ("l", "ml"): lambda x: x * 1000,
        ("g", "kg"): lambda x: x / 1000,
        ("kg", "g"): lambda x: x * 1000
    }
    try:
        m1 = float(m1)
        m2 = float(m2)
    except:
        return False

    if e1 == e2:
        return abs(m1 - m2) < 0.01
    if (e1, e2) in umrechnung:
        return abs(umrechnung[(e1, e2)](m1) - m2) < 0.01
    if (e2, e1) in umrechnung:
        return abs(umrechnung[(e2, e1)](m2) - m1) < 0.01
    return False

def extrahiere_mindestgehalt(text):
    text = text.replace(",", ".")
    match = re.search(r">=?\s?(\d{2,3}(\.\d+)?)%?", text)
    if match:
        return float(match.group(1))
    return None

def finde_treffer(suchtext, menge, einheit, df_appli, df_grundstoffe):
    suchtext_norm = normalize(suchtext)
    mindestgehalt = extrahiere_mindestgehalt(suchtext_norm)

    # Grundstoffe extrahieren
    grundstoffe = set(df_grundstoffe["Grundstoff"].str.lower())
    synonyme = set(df_grundstoffe["Synonym"].str.lower())
    begriffe = set(suchtext_norm.split())
    relevante_begriffe = grundstoffe.intersection(begriffe).union(synonyme.intersection(begriffe))

    perfekte = []
    abweichungen = []

    for _, row in df_appli.iterrows():
        produkt_raw = str(row["Deutsche Produktbezeichnung"])
        produkt_norm = normalize(produkt_raw)
        produkt_menge = row["Menge"]
        produkt_einheit = str(row["Einheit"]).lower()

        # Mindestgehalt vorhanden?
        produkt_gehalt = extrahiere_mindestgehalt(produkt_raw)
        gehalt_ok = not mindestgehalt or (produkt_gehalt and produkt_gehalt >= mindestgehalt)

        # Grundstoff enthalten?
        hat_grundstoff = any(w in produkt_norm for w in relevante_begriffe)

        # Menge vergleichbar?
        menge_match = gleiche_menge(menge, einheit.lower(), produkt_menge, produkt_einheit)

        eintrag = {
            "Produkt": produkt_raw,
            "Code": row["Code"],
            "Hersteller": row["Hersteller"],
            "Menge": produkt_menge,
            "Einheit": produkt_einheit,
            "Hinweis": "-",
            "Mindestgehalt": produkt_gehalt if produkt_gehalt else "-"
        }

        if hat_grundstoff and gehalt_ok and menge_match:
            eintrag["Hinweis"] = "Perfekter Treffer ✅"
            perfekte.append(eintrag)
        elif hat_grundstoff:
            eintrag["Hinweis"] = f"{produkt_menge} {produkt_einheit} abweichend ⚠️"
            abweichungen.append(enhanced := eintrag)

    return pd.DataFrame(perfekte), pd.DataFrame(abweichungen)

# -------------------- Streamlit UI --------------------
st.set_page_config(page_title="Chemikalien-Suchtool", layout="wide")
st.title("🔬 Chemikalien-Suchtool")

suchtext = st.text_input("🔍 Chemikalienname", "Toluol")
menge = st.text_input("Menge (z. B. 1, 2,5 etc.)", "1")
einheit = st.selectbox("Einheit", ["ml", "l", "g", "kg"])

# Dateien laden
APPLICHEM_FILE = "Aplichem_Daten.csv"
GRUNDSTOFF_FILE = "Chemikalien_mit_Synonymen_bereinigt_final_no_headers.csv"

try:
    df_appli = pd.read_csv(APPLICHEM_FILE, sep=None, engine="python", encoding="latin1")
    df_grundstoffe = pd.read_csv(GRUNDSTOFF_FILE, header=None, names=["Grundstoff", "Synonym"])

    if st.button("Suchen"):
        df_perfekt, df_abw = finde_treffer(suchtext, menge, einheit, df_appli, df_grundstoffe)

        if not df_perfekt.empty:
            st.markdown("### ✅ Perfekte Treffer")
            st.dataframe(df_perfekt)

        if not df_abw.empty:
            st.markdown("### ⚠️ Treffer mit Abweichungen")
            st.dataframe(df_abw)

        if df_perfekt.empty and df_abw.empty:
            st.error("❌ Keine passenden Treffer gefunden.")

except Exception as e:
    st.error(f"Fehler beim Laden der Dateien: {e}")
