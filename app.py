import streamlit as st
import pandas as pd
import re

# -----------------------------
# Hilfsfunktionen
# -----------------------------
def normalize(text):
    return re.sub(r"[^a-z0-9%.,\- ]", "", str(text).lower()).replace(",", ".")

def extract_mindestgehalt(text):
    text = text.replace(",", ".")
    match = re.search(r"[\u2265>=]\s?(\d{2,3}(\.\d+)?)%", text)  # ≥ = ≥ (Unicode für ≥)
    if match:
        return float(match.group(1))
    return None

def extrahiere_mindestgehalt(text):
    werte = re.findall(r"(\d{2,3}(?:[.,]\d+)?)\s?%", text.replace(",", "."))
    werte_float = [float(w.replace(",", ".")) for w in werte]
    return max(werte_float) if werte_float else None

def gleiche_menge(m1, e1, m2, e2):
    umrechnung = {
        ("ml", "l"): 0.001,
        ("l", "ml"): 1000,
        ("g", "kg"): 0.001,
        ("kg", "g"): 1000
    }
    if e1 == e2:
        return abs(m1 - m2) < 0.01
    if (e1, e2) in umrechnung:
        return abs(m1 * umrechnung[(e1, e2)] - m2) < 0.01
    if (e2, e1) in umrechnung:
        return abs(m2 * umrechnung[(e2, e1)] - m1) < 0.01
    return False

# -----------------------------
# Daten laden
# -----------------------------
@st.cache_data

def load_applichem():
    return pd.read_csv("Applichem_Daten.csv", sep=None, engine="python", encoding="latin1")

@st.cache_data

def load_grundstoffe():
    df = pd.read_csv("Chemikalien_mit_Synonymen_bereinigt_final_no_headers.csv", encoding="utf-8")
    df.columns = ["Grundstoff", "Synonym"]
    df.dropna(inplace=True)
    return df

# -----------------------------
# Hauptlogik für Suche
# -----------------------------
def finde_treffer(suchtext, menge, einheit, df_appli, df_grund):
    suchtext_clean = normalize(suchtext)
    suchbegriffe = suchtext_clean.split()
    mind_gehalt = extract_mindestgehalt(suchtext)

    result_perfekt = []
    result_abweichend = []

    for _, row in df_appli.iterrows():
        bezeichnung_raw = str(row["Deutsche Produktbezeichnung"])
        bezeichnung = normalize(bezeichnung_raw)

        produkt_menge = row["Menge"]
        produkt_einheit = str(row["Einheit"]).lower()

        code = row["Code"]
        hersteller = row["Hersteller"]

        inhalt_gefunden = all(term in bezeichnung for term in suchbegriffe)

        # Grundstoffprüfung
        grundstoff_match = False
        for _, r in df_grund.iterrows():
            g = normalize(r["Grundstoff"])
            s = normalize(r["Synonym"])
            if g in suchtext_clean or s in suchtext_clean:
                if g in bezeichnung or s in bezeichnung:
                    grundstoff_match = True
                    break

        mindestgehalt_im_produkt = extrahiere_mindestgehalt(bezeichnung_raw)
        reinheit_ok = True if mind_gehalt is None else (
            mindestgehalt_im_produkt is not None and mindestgehalt_im_produkt >= mind_gehalt
        )

        menge_match = gleiche_menge(float(menge), einheit.lower(), float(produkt_menge), produkt_einheit)

        if grundstoff_match and reinheit_ok:
            treffer = {
                "Produkt": bezeichnung_raw,
                "Code": code,
                "Hersteller": hersteller,
                "Menge": produkt_menge,
                "Einheit": produkt_einheit,
                "Hinweis": "Perfekter Treffer ✅" if menge_match else f"{produkt_menge} {produkt_einheit} abweichend ⚠️",
                "Mindestgehalt": mindestgehalt_im_produkt if mindestgehalt_im_produkt else "-"
            }
            if menge_match:
                result_perfekt.append(treffer)
            else:
                result_abweichend.append(treffer)

    return pd.DataFrame(result_perfekt), pd.DataFrame(result_abweichend)

# -----------------------------
# Streamlit App
# -----------------------------
st.set_page_config(page_title="Chemikalien-Suchtool", layout="wide")
st.title("🔬 Chemikalien-Suchtool")

suchtext = st.text_input("Suchbegriff eingeben:", "Toluol")
menge = st.text_input("Menge (z. B. 1, 2.5 etc.)", "1")
einheit = st.selectbox("Einheit", ["ml", "l", "g", "kg"])

if st.button("Suchen"):
    df_appli = load_applichem()
    df_grundstoffe = load_grundstoffe()
    df_perfekt, df_abw = finde_treffer(suchtext, menge, einheit, df_appli, df_grundstoffe)

    if not df_perfekt.empty:
        st.subheader("✅ Perfekte Treffer")
        st.dataframe(df_perfekt)
    if not df_abw.empty:
        st.subheader("⚠️ Treffer mit Abweichungen")
        st.dataframe(df_abw)
    if df_perfekt.empty and df_abw.empty:
        st.error("❌ Keine passenden Treffer gefunden.")
