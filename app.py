import streamlit as st
import pandas as pd
import re

# ------------------ Konfiguration ------------------
GRUNDSTOFF_FILE = "Chemikalien_mit_Synonymen_bereinigt_final_no_headers.csv"
APPLICHEM_FILE = "Applichem_Daten.csv"

# ------------------ Hilfsfunktionen ------------------

@st.cache_data
def load_applichem():
    return pd.read_csv(APPLICHEM_FILE, sep=None, engine="python", encoding="latin1")

@st.cache_data
def load_grundstoffe():
    df = pd.read_csv(GRUNDSTOFF_FILE, header=None, names=["Grundstoff", "Synonym"])
    df["Grundstoff"] = df["Grundstoff"].astype(str).str.lower()
    df["Synonym"] = df["Synonym"].astype(str).str.lower()
    return df

def normalize(text):
    return re.sub(r"[^a-z0-9 ]", " ", str(text).lower()).strip()

def extrahiere_mindestgehalt(text):
    text = text.replace("≥", ">=").replace("%", "")
    match = re.search(r">=?\s?(\d{2,3}(?:[\.,]\d+)?)", text)
    if match:
        return float(match.group(1).replace(",", "."))
    return None

def gleiche_menge(m1, e1, m2, e2):
    umrechnungen = {
        ("ml", "l"): 0.001,
        ("l", "ml"): 1000,
        ("g", "kg"): 0.001,
        ("kg", "g"): 1000
    }
    if e1 == e2:
        return abs(m1 - m2) < 0.01
    if (e1, e2) in umrechnungen:
        return abs(m1 * umrechnungen[(e1, e2)] - m2) < 0.01
    if (e2, e1) in umrechnungen:
        return abs(m2 * umrechnungen[(e2, e1)] - m1) < 0.01
    return False

def finde_treffer(user_text, user_menge, user_einheit, df_appli, df_grundstoffe):
    user_text_normalized = normalize(user_text)
    user_menge = float(str(user_menge).replace(",", "."))
    user_einheit = user_einheit.lower()

    # Mindestgehalt extrahieren
    mindestgehalt = extrahiere_mindestgehalt(user_text)
    suchtext_ohne_gehalt = re.sub(r">=?\s?\d+[\.,]?\d*\s?%?", "", user_text_normalized)

    # Grundstoff identifizieren
    grundstoffe = df_grundstoffe.dropna().drop_duplicates()
    gefundene_grundstoffe = grundstoffe[
        grundstoffe["Grundstoff"].apply(lambda g: g in suchtext_ohne_gehalt)
        | grundstoffe["Synonym"].apply(lambda s: s in suchtext_ohne_gehalt)
    ]
    if gefundene_grundstoffe.empty:
        return pd.DataFrame(), pd.DataFrame()

    relevante_begriffe = set(gefundene_grundstoffe["Grundstoff"]).union(set(gefundene_grundstoffe["Synonym"]))

    perfekte, abweichungen = [], []

    for _, row in df_appli.iterrows():
        produkt_raw = str(row["Deutsche Produktbezeichnung"])
        produkt_norm = normalize(produkt_raw)
        menge = float(str(row["Menge"]).replace(",", ".")) if "Menge" in row else 0
        einheit = str(row["Einheit"]).lower() if "Einheit" in row else ""

        # Prüfen, ob Grundstoff drin ist
        if not any(b in produkt_norm for b in relevante_begriffe):
            continue

        # Mindestgehalt prüfen
        produkt_gehalt = extrahiere_mindestgehalt(produkt_raw)
        if mindestgehalt and (not produkt_gehalt or produkt_gehalt < mindestgehalt):
            continue

        if gleiche_menge(user_menge, user_einheit, menge, einheit):
            hinweis = "Perfekter Treffer ✅"
        else:
            hinweis = f"{menge} {einheit} abweichend ⚠️"

        eintrag = {
            "Produkt": produkt_raw,
            "Code": row["Code"],
            "Hersteller": row["Hersteller"],
            "Menge": menge,
            "Einheit": einheit,
            "Hinweis": hinweis,
            "Mindestgehalt im Produkt": produkt_gehalt if produkt_gehalt else "-"
        }

        if hinweis == "Perfekter Treffer ✅":
            perfekte.append(eintrag)
        else:
            abweichungen.append(eintrag)

    return pd.DataFrame(perfekte), pd.DataFrame(abweichungen)

# ------------------ Streamlit App ------------------

st.title("🔬 OMNILAB Chemikalien-Finder")
st.markdown("Gib ein gewünschtes Produkt ein (z. B. `Toluol HPLC ≥99.9%`, `Aceton 1 l`) und finde passende Treffer.")

df_appli = load_applichem()
df_grundstoffe = load_grundstoffe()

chem_name = st.text_input("🔎 Chemikalienname")
menge = st.text_input("Menge (z. B. 1, 2.5 etc.)")
einheit = st.selectbox("Einheit", ["ml", "l", "g", "kg", "Stk"])

if st.button("Suchen"):
    if chem_name and menge:
        df_perf, df_abw = finde_treffer(chem_name, menge, einheit, df_appli, df_grundstoffe)

        if df_perf.empty and df_abw.empty:
            st.warning("❌ Kein passendes Produkt gefunden.")
        else:
            if not df_perf.empty:
                st.subheader("✅ Perfekte Treffer")
                st.dataframe(df_perf)

            if not df_abw.empty:
                st.subheader("⚠️ Treffer mit Abweichungen")
                st.dataframe(df_abw)
    else:
        st.warning("Bitte alle Felder ausfüllen.")
