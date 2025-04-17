import streamlit as st
import pandas as pd
import re

# -------------------------------
# Hilfsfunktionen
# -------------------------------
def normalize(text):
    return re.sub(r"[^a-z0-9%.,\->= ]", " ", str(text).lower()).replace("  ", " ").strip()

def extrahiere_mindestgehalt(text):
    text = text.replace(",", ".").replace("≥", ">=").replace("%", "")
    match = re.search(r">=?\s?(\d{2,3}(\.\d+)?)", text)
    if match:
        return float(match.group(1))
    return None

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

def clean_code(code):
    return re.sub(r"[^0-9]", "", str(code))

# -------------------------------
# Trefferlogik
# -------------------------------
def finde_treffer(suchtext, menge_input, einheit_input, df):
    suchtext = normalize(suchtext)
    menge_input = float(str(menge_input).replace(",", "."))
    einheit_input = einheit_input.lower()

    mindestgehalt = extrahiere_mindestgehalt(suchtext)
    suchbegriffe = [w for w in re.sub(r">=?\s?\d{2,3}(\.\d+)?", "", suchtext).split() if w]

    perfekte = []
    abweichungen = []

    for _, row in df.iterrows():
        produkt_raw = str(row["Deutsche Produktbezeichnung"])
        produkt = normalize(produkt_raw)
        produkt_gehalt = extrahiere_mindestgehalt(produkt_raw)

        menge = float(str(row["Menge"]).replace(",", "."))
        einheit = str(row["Einheit"]).lower()

        code = clean_code(row["Code"])
        hersteller = row["Hersteller"]

        if not gleiche_menge(menge_input, einheit_input, menge, einheit):
            hinweis = f"Nur {menge} {einheit} verfügbar (abweichend)"
            status = "Abweichung"
        else:
            hinweis = "Perfekter Treffer"
            status = "Perfekt"

        # Check ob alle Begriffe vorkommen
        begriffe_im_namen = [b for b in suchbegriffe if b in produkt]
        alle_begriffe_da = len(begriffe_im_namen) == len(suchbegriffe)

        # Gehalt passt?
        gehalt_ok = True if not mindestgehalt else (produkt_gehalt and produkt_gehalt >= mindestgehalt)

        eintrag = {
            "Produkt": produkt_raw,
            "Code": code,
            "Hersteller": hersteller,
            "Menge": menge,
            "Einheit": einheit,
            "Hinweis": hinweis,
            "Mindestgehalt im Produkt": produkt_gehalt if produkt_gehalt else "-",
            "Begriffe gefunden": ", ".join(begriffe_im_namen)
        }

        if alle_begriffe_da and gehalt_ok and status == "Perfekt":
            perfekte.append(eintrag)
        elif gehalt_ok or alle_begriffe_da:
            abweichungen.append(eintrag)

    return pd.DataFrame(perfekte), pd.DataFrame(abweichungen)

# -------------------------------
# Daten laden
# -------------------------------
@st.cache_data
def load_applichem():
    return pd.read_csv("Aplichem_Daten.csv", encoding="utf-8", errors="replace")

# -------------------------------
# Streamlit UI
# -------------------------------
st.set_page_config(page_title="Chemikalien-Suchtool", layout="centered")
st.title("🔍 Chemikalien-Suchtool")

suchtext = st.text_input("Suchbegriff eingeben:")
menge = st.text_input("Menge (z. B. 1, 2.5 etc.)", value="1")
einheit = st.selectbox("Einheit", ["ml", "l", "g", "kg"])

if st.button("Suchen"):
    df_appli = load_applichem()
    perfekte, abweichungen = finde_treffer(suchtext, menge, einheit, df_appli)

    if perfekte.empty and abweichungen.empty:
        st.error("❌ Keine passenden Treffer gefunden.")
    else:
        if not perfekte.empty:
            st.success("✅ Perfekte Treffer")
            st.dataframe(perfekte)

        if not abweichungen.empty:
            st.warning("⚠️ Treffer mit Abweichungen")
            st.dataframe(abweichungen)
