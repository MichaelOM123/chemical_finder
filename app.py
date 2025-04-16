import streamlit as st
import pandas as pd
import re

# Daten laden
@st.cache_data
def load_data():
    return pd.read_csv("Aplichem_Daten.csv", sep=None, engine="python")

# Reinheits-Mapping laden
@st.cache_data
def lade_reinheit_mapping():
    return pd.read_csv("reinheit_mapping.csv")

# Reinheit aus Suchtext extrahieren
def extrahiere_reinheit(suchtext):
    text = suchtext.replace("≥", ">=").replace("%", "")
    match = re.search(r">=?\s?(\d{2,3}(\.\d+)?)", text)
    if match:
        return float(match.group(1))
    return None

# Artikelnummer vereinheitlichen (nur Ziffern)
def clean_code(code):
    return re.sub(r"[^0-9]", "", str(code))

# Text normalisieren (z. B. "ph.eur." → "ph eur")
def normalize(text):
    return re.sub(r"[^a-z0-9 ]", " ", text.lower()).replace("  ", " ").strip()

# Matching-Logik
def finde_treffer(user_name, user_menge, user_einheit, df, mapping_df):
    user_menge = float(str(user_menge).replace(",", "."))
    suchtext = normalize(user_name)
    mindestreinheit = extrahiere_reinheit(suchtext)
    suchbegriffe = re.sub(r">=?\s?\d+(\.\d+)?%?", "", suchtext).split()
    treffer = []

    for _, row in df.iterrows():
        produktname_raw = str(row["Deutsche Produktbezeichnung"])
        produktname = normalize(produktname_raw)

        if all(begriff in produktname for begriff in suchbegriffe):
            erkannte_begriffe = []
            erkannte_reinheit = None

            if mindestreinheit:
                gefundene_werte = []
                for _, qual_row in mapping_df.iterrows():
                    bez = normalize(qual_row["Bezeichnung"])
                    if bez in produktname:
                        gefundene_werte.append(qual_row["Mindestwert"])
                        erkannte_begriffe.append(bez)
                if not gefundene_werte or max(gefundene_werte) < mindestreinheit:
                    continue
                erkannte_reinheit = max(gefundene_werte)

            try:
                menge = float(str(row["Menge"]).replace(",", "."))
                einheit = str(row["Einheit"]).lower()

                if einheit == user_einheit.lower():
                    differenz = menge - user_menge
                    if differenz == 0:
                        hinweis = "Perfekter Treffer ✅"
                    elif differenz > 0:
                        hinweis = f"Nur {menge} {einheit} verfügbar (größer) ⚠️"
                    else:
                        hinweis = f"Nur {menge} {einheit} verfügbar (kleiner) ⚠️"

                    treffer.append({
                        "Produkt": produktname_raw,
                        "Menge": menge,
                        "Einheit": einheit,
                        "Code": clean_code(row["Code"]),
                        "Hersteller": row["Hersteller"],
                        "Hinweis": hinweis,
                        "Reinheit erkannt": erkannte_reinheit if erkannte_reinheit else "-",
                        "Begriffe gefunden": ", ".join(set(erkannte_begriffe)) if erkannte_begriffe else "-"
                    })
            except:
                continue

    df_result = pd.DataFrame(treffer)
    if not df_result.empty:
        df_result.sort_values(by="Hinweis", ascending=False, inplace=True)
    return df_result

# Streamlit UI
st.title("🔬 OMNILAB Chemikalien-Finder")
st.markdown("Lade eine Excel-Datei hoch oder gib ein Produkt manuell ein.")

uploaded_file = st.file_uploader("📂 Excel-Datei mit Chemikalienwünschen hochladen", type=["csv", "xlsx"])

data = load_data()
mapping = lade_reinheit_mapping()

if uploaded_file:
    try:
        if uploaded_file.name.endswith(".csv"):
            user_df = pd.read_csv(uploaded_file)
        else:
            user_df = pd.read_excel(uploaded_file)

        results = pd.DataFrame()
        for _, row in user_df.iterrows():
            treffer_df = finde_treffer(row["Chemikalie"], row["Menge"], row["Einheit"], data, mapping)
            results = pd.concat([results, treffer_df], ignore_index=True)

        if results.empty:
            st.warning("Keine passenden Produkte gefunden.")
        else:
            perfekte = results[results["Hinweis"].str.contains("Perfekter Treffer")]
            abweichungen = results[~results["Hinweis"].str.contains("Perfekter Treffer")]

            if not perfekte.empty:
                st.subheader("✅ Perfekte Treffer")
                st.dataframe(perfekte)

            if not abweichungen.empty:
                st.subheader("⚠️ Treffer mit Abweichungen")
                st.dataframe(abweichungen)

            st.download_button(
                label="📥 Ergebnisse als Excel herunterladen",
                data=results.to_csv(index=False).encode("utf-8"),
                file_name="Suchergebnisse.csv",
                mime="text/csv"
            )

    except Exception as e:
        st.error(f"Fehler beim Verarbeiten der Datei: {e}")
else:
    chem_name = st.text_input("🔎 Chemikalienname")
    menge = st.text_input("Menge (z. B. 1, 2.5 etc.)")
    einheit = st.selectbox("Einheit", ["ml", "l", "g", "kg", "Stk"])

    if st.button("Suchen"):
        if chem_name and menge:
            result = finde_treffer(chem_name, menge, einheit, data, mapping)

            if result.empty:
                st.warning("Keine passenden Produkte gefunden.")
            else:
                perfekte = result[result["Hinweis"].str.contains("Perfekter Treffer")]
                abweichungen = result[~result["Hinweis"].str.contains("Perfekter Treffer")]

                if not perfekte.empty:
                    st.subheader("✅ Perfekte Treffer")
                    st.dataframe(perfekte)

                if not abweichungen.empty:
                    st.subheader("⚠️ Treffer mit Abweichungen")
                    st.dataframe(abweichungen)
        else:
            st.warning("Bitte alle Felder ausfüllen.")
