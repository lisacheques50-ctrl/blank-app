import datetime
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Mon Suivi Sport", page_icon="🏃‍♀️", layout="centered")
st.markdown("""
<style>
.block-container { padding-top: 1rem; padding-bottom: 5rem; padding-left: 1rem; padding-right: 1rem; }
h1 { font-size: 1.8rem !important; text-align: center; }
h2 { font-size: 1.4rem !important; }
.stButton>button { width: 100%; border-radius: 10px; height: 3rem; font-size: 1rem; font-weight: bold; }
</style>
""", unsafe_allow_html=True)
st.title("🏃‍♀️ Mon Suivi Personnel")

if "sport_data" not in st.session_state:
    st.session_state.sport_data = pd.DataFrame([
        {"Date": datetime.date.today(), "Type": "Salle de sport", "Fait": False, "Duree": 0, "Details": "Séance Jambes & Fessiers", "Km": 0.0, "Notes": ""},
        {"Date": datetime.date.today() + datetime.timedelta(days=2), "Type": "Course à pied", "Fait": False, "Duree": 0, "Details": "Footing endurance 45 min", "Km": 0.0, "Notes": ""}
    ])
if "poids_data" not in st.session_state:
    st.session_state.poids_data = pd.DataFrame([
        {"Date": datetime.date.today() - datetime.timedelta(days=7), "Poids": 65.5},
        {"Date": datetime.date.today(), "Poids": 64.8}
    ])
if "calories_data" not in st.session_state:
    st.session_state.calories_data = {}

menu = st.tabs(["📅 Agenda", "⚖️ Poids", "🔥 Calories"])

with menu[0]:
    st.header("📅 Mes Séances")
    with st.expander("➕ Planifier une séance", expanded=False):
        date_sport = st.date_input("Date", datetime.date.today(), key="add_date")
        type_sport = st.selectbox("Sport", ["Salle de sport", "Course à pied", "Autre"])
        details = st.text_input("Objectif (ex: Séance Dos, Footing 5km)")
        if st.button("Enregistrer le planning"):
            nouvelle_seance = {"Date": date_sport, "Type": type_sport, "Fait": False, "Duree": 0, "Details": details, "Km": 0.0, "Notes": ""}
            st.session_state.sport_data = pd.concat([
                st.session_state.sport_data, pd.DataFrame([nouvelle_seance])
            ], ignore_index=True)
            st.rerun()

    st.subheader("Mes séances prévues et réalisées")
    if not st.session_state.sport_data.empty:
        df_sorted = st.session_state.sport_data.sort_values(by="Date")
        for index, row in df_sorted.iterrows():
            statut = "✅ Faite" if row["Fait"] else "⏳ À faire"
            with st.container(border=True):
                st.markdown(f"**{row['Date'].strftime('%d/%m')} - {row['Type']}** ({statut})")
                st.write(f"📋 Prévu : {row['Details']}")
                if not row["Fait"]:
                    with st.expander("📝 Compléter la séance"):
                        duree = st.number_input("Durée (minutes)", min_value=0, value=45, key=f"dur_{index}")
                        km = 0.0
                        if row["Type"] == "Course à pied":
                            km = st.number_input("Distance (km)", min_value=0.0, step=0.1, key=f"km_{index}")
                        notes = st.text_area("Poids soulevés / Commentaires", placeholder="Ex: Squat 4x10 à 40kg. Bonne sensation !", key=f"notes_{index}")
                        if st.button("Valider la séance", key=f"btn_{index}"):
                            st.session_state.sport_data.at[index, "Fait"] = True
                            st.session_state.sport_data.at[index, "Duree"] = duree
                            st.session_state.sport_data.at[index, "Km"] = km
                            st.session_state.sport_data.at[index, "Notes"] = notes
                            st.rerun()
                else:
                    st.write(f"⏱️ Durée : {row['Duree']} min")
                    if row["Type"] == "Course à pied":
                        st.write(f"🏃‍♀️ Distance : {row['Km']} km")
                    if row["Notes"]:
                        st.write(f"🏋️‍♂️ Mes notes : {row['Notes']}")
    else:
        st.info("Aucune séance de prévue.")

with menu[1]:
    st.header("⚖️ Mon Poids")
    col1, col2 = st.columns(2)
    with col1:
        poids_val = st.number_input("Poids du jour (kg)", min_value=30.0, max_value=150.0, value=64.0, step=0.1)
    with col2:
        st.write("")
        st.write("")
        if st.button("Noter le poids"):
            nouveau_poids = {"Date": datetime.date.today(), "Poids": poids_val}
            st.session_state.poids_data = pd.concat([
                st.session_state.poids_data, pd.DataFrame([nouveau_poids])
            ], ignore_index=True)
            st.rerun()
    if not st.session_state.poids_data.empty:
        df_poids = st.session_state.poids_data.sort_values(by="Date", kind="stable")
        st.line_chart(df_poids.set_index("Date")["Poids"])
        dernier_poids = df_poids.iloc[-1]["Poids"]
        st.metric("Dernier poids enregistré", f"{dernier_poids:.1f} kg")

with menu[2]:
    st.header("🔥 Mon bilan calorique estimé")
    date_cal = st.date_input("Choisir le jour", datetime.date.today(), key="date_cal")
    date_str = str(date_cal)
    if date_str not in st.session_state.calories_data:
        st.session_state.calories_data[date_str] = {"mange": 1600, "brules_base": 1800, "sport": 0}
    seances_du_jour = st.session_state.sport_data[
        (st.session_state.sport_data["Date"] == date_cal)
        & (st.session_state.sport_data["Fait"] == True)
    ]
    sport_auto = sum(int(s["Duree"] * 6) for _, s in seances_du_jour.iterrows())
    st.session_state.calories_data[date_str]["sport"] = sport_auto
    mange = st.number_input("Calories consommées (kcal)", min_value=0, value=int(st.session_state.calories_data[date_str]["mange"]), step=50, key=f"mange_{date_str}")
    base = st.number_input("Dépense quotidienne estimée hors sport (kcal)", min_value=0, value=int(st.session_state.calories_data[date_str]["brules_base"]), step=50, key=f"base_{date_str}")
    st.session_state.calories_data[date_str]["mange"] = mange
    st.session_state.calories_data[date_str]["brules_base"] = base
    total_brules = base + sport_auto
    deficit = total_brules - mange
    st.write("---")
    if deficit > 0:
        st.info(f"Déficit estimé : {deficit} kcal.")
    elif deficit < 0:
        st.info(f"Surplus estimé : {abs(deficit)} kcal.")
    else:
        st.info("Apports et dépenses estimés à l'équilibre.")
    st.caption(f"Dépenses estimées : {total_brules} kcal, dont {sport_auto} via le sport. Apports : {mange} kcal.")
    st.caption("Le calcul du sport utilise un forfait approximatif de 6 kcal/min. Ce bilan reste une estimation, pas un objectif à atteindre.")
