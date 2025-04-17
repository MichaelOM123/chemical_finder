import streamlit as st
import pandas as pd
import re

# ---------------------- Hilfsfunktionen ----------------------
def normalize(text):
    return re.sub(r"[^a-z0-9 ]", " ", str(text).lower()).replace("  ", " ").strip()

def clean_code(code):
    return re.sub(r"[^0-9]", "", str(code))

def gleiche_menge(m1, e1, m2, e2):
    e1, e2 = e1.strip().lower(), e2.strip().lower()
    umrechnung = {("ml", "l"): 0.001, ("l", "ml"): 1000, ("g", "kg"): 0.001, ("kg", "g"): 1000}
    if e1 == e2:
        return abs(m1 - m2) < 0.01
    if (e1, e2) in umrechnung:
        return abs(m1 * umrechnung[(e1, e2)] - m2) < 0.01
    if (e2, e1) in umrechnung:
        return abs(m2 * umrechnung[(e2, e1)] - m1) < 0.01
    return False

def extract_mindestgehalt(text):
    text = text.replace(",", ".")
    match = re.search(r"(\d{2,3}(\.\d+)?)\s?%", text)
    return float(match.group(1)) if match else None

@st.cache_data
def load_applichem():
    return pd.read_csv("Aplichem_Daten.csv", sep=None, engine="python", encoding="latin1")

@st.cache_data
def load_grundstoffe():
    df = pd.read_csv("Chemikalien_mit_Synonymen_bereinigt_final_no_headers.csv", header=None)
    df.columns = ["Grundstoff", "Synonym"]
    return df

# ---------------------- Suche ----------------------
def finde_treffer(suchtext, menge, einheit, df_appli, df_grundstoffe):
    suchtext_norm = normalize(suchtext)
    suchteile = suchtext_norm.split()
    mindestgehalt = extract_mindestgehalt(suchtext)
    menge = float(str(menge).replace(",", "."))
    einheit = einheit.strip().lower()

    # Grundstoff suchen
    grundstoff = None
    for _, row in df_grundstoffe.iterrows():
        if normalize(row["Grundstoff"]) in suchteile or normalize(str(row["Synonym"])) in suchteile:
            grundstoff = normalize(row["Grundstoff"])
            break

    perfekte, abweichungen = [], []

    for _, row in df_appli.iterrows():
        name = str(row["Deutsche Produktbezeichnung"])
        norm_name = normalize(name)

        # Check: Enthält der Produktname den gesuchten Grundstoff?
        if grundstoff and grundstoff not in norm_name:
            continue

        # Check: Mindestgehalt
        if mindestgehalt:
            gehalt_im_text = extract_mindestgehalt(name)
            if not gehalt_im_text or gehalt_im_text < mindestgehalt:
                continue

        # Check: Menge & Einheit
        try:
            m = float(str(row["Menge"]).replace(",", "."))
            e = str(row["Einheit"]).strip().lower()
        except:
            continue

        if gleiche_menge(m, e, menge, einheit):
            hinweis = "Perfekter Treffer ✅"
            perfekte.append({"Produkt": name, "Menge": m, "Einheit": e, "Hersteller": row["Hersteller"], "Code": clean_code(row["Code"]), "Hinweis": hinweis})
        else:
            hinweis = f"Abweichende Menge: {m} {e} ⚠️"
            abweichungen.append({"Produkt": name, "Menge": m, "Einheit": e, "Hersteller": row["Hersteller"], "Code": clean_code(row["Code"]), "Hinweis": hinweis})

    return pd.DataFrame(perfekte), pd.DataFrame(abweichungen)

# ---------------------- UI ----------------------
st.title("🔬 OMNILAB Chemikalien-Finder")
st.markdown("Suche z. B.: `Toluol HPLC ≥99.9% 1 l`")

chemikalie = st.text_input("🔎 Chemikalienbezeichnung inkl. Menge und ggf. Mindestgehalt")
menge = st.text_input("Menge", value="1")
einheit = st.selectbox("Einheit", ["ml", "l", "g", "kg"])

if st.button("Suchen") and chemikalie:
    try:
        df_appli = load_applichem()
        df_grundstoffe = load_grundstoffe()

        perfekte, abweichungen = finde_treffer(chemikalie, menge, einheit, df_appli, df_grundstoffe)

        if not perfekte.empty:
            st.subheader("✅ Perfekte Treffer")
            st.dataframe(perfekte)

        if not abweichungen.empty:
            st.subheader("⚠️ Abweichende Produkte")
            st.dataframe(abweichungen)

        if perfekte.empty and abweichungen.empty:
            st.info("Keine passenden Produkte gefunden.")

    except Exception as e:
        st.error(f"Fehler bei der Suche: {e}")
