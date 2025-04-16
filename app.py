import streamlit as st
import pandas as pd

# Daten laden (hier als Platzhalter, kann durch echte CSV ersetzt werden)
@st.cache_data
def load_data():
    return pd.read_csv("Aplichem_Daten.csv", sep=None, engine="python")

# Matching-Logik
def finde_treffer(user_name, user_menge, user_einheit, df):
    user_menge = float(str(user_menge).replace(",", "."))
    treffer = []

    suchbegriffe = user_name.lower().split()

    for _, row in df.iterrows():
        produktname = str(row["Deutsche Produktbezeichnung"]).lower()
        if all(begriff in produktname for begriff in suchbegriffe):
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
                        "Produkt": row["Deutsche Produktbezeichnung"],
                        "Menge": menge,
                        "Einheit": einheit,
                        "Code": row["Code"],
                        "Hersteller": row["Hersteller"],
                        "Hinweis": hinweis
                    })
            except:
                continue

    return pd.DataFrame(treffer)

# Streamlit UI
st.title("🔬 OMNILAB Chemikalien-Finder")
st.markdown("Lade eine Excel-Datei hoch oder gib ein Produkt manuell ein.")

uploaded_file = st.file_uploader("📂 Excel-Datei mit Chemikalienwünschen hochladen", type=["csv", "xlsx"])

data = load_data()

if uploaded_file:
    try:
        if uploaded_file.name.endswith(".csv"):
            user_df = pd.read_csv(uploaded_file)
        else:
            user_df = pd.read_excel(uploaded_file)

        results = pd.DataFrame()
        for _, row in user_df.iterrows():
            treffer_df = finde_treffer(row["Chemikalie"], row["Menge"], row["Einheit"], data)
            results = pd.concat([results, treffer_df], ignore_index=True)

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
            result = finde_treffer(chem_name, menge, einheit, data)

            perfekte = result[result["Hinweis"].str.contains("Perfekter Treffer")]
            abweichungen = result[~result["Hinweis"].str.contains("Perfekter Treffer")]

            if not perfekte.empty:
                st.subheader("✅ Perfekte Treffer")
                st.dataframe(perfekte)

            if not abweichungen.empty:
                st.subheader("⚠️ Treffer mit Abweichungen")
                st.dataframe(abweichungen)

            if result.empty:
                st.warning("Keine passenden Produkte gefunden.")
        else:
            st.warning("Bitte alle Felder ausfüllen.")
