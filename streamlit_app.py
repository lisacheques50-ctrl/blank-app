import streamlit as st
import pandas as pd
import datetime

# Configuration pour un affichage mobile optimal
st.set_page_config(page_title="Mon Suivi Sport", page_icon="🏃‍♀️", layout="centered")

# CSS personnalisé pour forcer le look "Application Mobile"
st.markdown("""
<style>
.block-container { padding-top: 1rem; padding-bottom: 5rem; padding-left: 1rem; padding-right: 1rem; }
h1 { font-size: 1.8rem !important; text-align: center; }
h2 { font-size: 1.4rem !important; }
.stButton>button { width: 100%; border-radius: 10px; height: 3rem; font-size: 1rem; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("🏃‍♀️ Mon Suivi Personnel")

# Initialisation des bases de données en mémoire
if 'sport_data' not in st.session_state:
st.session_state.sport_data = pd.DataFrame([
{"Date": datetime.date.today(), "Type": "Salle de sport", "Fait": False, "Duree": 0, "Details": "Séance Jambes & Fessiers", "Km": 0.0, "Notes": ""},
{"Date": datetime.date.today() + datetime.timedelta(days=2), "Type": "Course à pied", "Fait": False, "Duree": 0, "Details": "Footing endurance 45 min", "Km": 0.0, "Notes": ""}
])
if 'poids_data' not in st.session_state:
st.session_state.poids_data = pd.DataFrame([
{"Date": datetime.date.today() - datetime.timedelta(days=7), "Poids": 65.5},
{"Date": datetime.date.today(), "Poids": 64.8}
])
if 'calories_data' not in st.session_state:
st.session_state.calories_data = {}

# Navigation par onglets (Parfait pour le pouce sur mobile)
menu = st.tabs(["📅 Agenda", "⚖️ Poids", "🔥 Calories"])

# --- ONGLET 1 : AGENDA SPORT ---
with menu[0]:
st.header("📅 Mes Séances")

# Formulaire de planification rapide
with st.expander("➕ Planifier une séance", expanded=False):
date_sport = st.date_input("Date", datetime.date.today(), key="add_date")
type_sport = st.selectbox("Sport", ["Salle de sport", "Course à pied", "Autre"])
details = st.text_input("Objectif (ex: Séance Dos, Footing 5km)")

if st.button("Enregistrer le planning"):
nouvelle_seance = {"Date": date_sport, "Type": type_sport, "Fait": False, "Duree": 0, "Details": details, "Km": 0.0, "Notes": ""}
st.session_state.sport_data = pd.concat([st.session_state.sport_data, pd.DataFrame([nouvelle_seance])], ignore_index=True)
st.success("C'est noté ! ✨")
st.rerun()

# Liste des séances
st.subheader("Régularité du mois")
if not st.session_state.sport_data.empty:
# Tri pour avoir les plus récentes en premier
df_sorted = st.session_state.sport_data.sort_values(by="Date", ascending=True)
for index, row in df_sorted.iterrows():
statut = "✅ Faite" if row["Fait"] else "⏳ À faire"
color = "green" if row["Fait"] else "orange"

with st.container(border=True):
st.markdown(f"**{row['Date'].strftime('%d/%m')} - {row['Type']}** ({statut})")
st.write(f"📋 *Prévu :* {row['Details']}")

if not row["Fait"]:
# Formulaire de validation rapide
with st.expander("📝 Compléter la séance"):
duree = st.number_input("Durée (minutes)", min_value=0, value=45, key=f"dur_{index}")
km = 0.0
if row["Type"] == "Course à pied":
km = st.number_input("Distance (Km)", min_value=0.0, step=0.1, key=f"km_{index}")

notes = st.text_area("Poids soulevés / Commentaires", placeholder="Ex: Squat 4x10 à 40kg. Bonne sensation !", key=f"notes_{index}")

if st.button("Valider la séance", key=f"btn_{index}"):
st.session_state.sport_data.at[index, "Fait"] = True
st.session_state.sport_data.at[index, "Duree"] = duree
st.session_state.sport_data.at[index, "Km"] = km
st.session_state.sport_data.at[index, "Notes"] = notes
st.success("Félicitations pour votre séance ! 🎉")
st.rerun()
else:
st.write(f"⏱️ **Durée :** {row['Duree']} min")
if row["Type"] == "Course à pied":
st.write(f"🏃‍♀️ **Distance :** {row['Km']} km")
if row["Notes"]:
st.write(f"🏋️‍♂️ **Mes notes :** {row['Notes']}")
else:
st.info("Aucune séance de prévue.")

# --- ONGLET 2 : SUIVI DU POIDS ---
with menu[1]:
st.header("⚖️ Mon Poids")

col1, col2 = st.columns([2, 1])
with col1:
poids_val = st.number_input("Poids du jour (kg)", min_value=30.0, max_value=150.0, value=64.0, step=0.1)
with col2:
st.write("") # Alignement
st.write("")
if st.button("Noter"):
nouveau_poids = {"Date": datetime.date.today(), "Poids": poids_val}
st.session_state.poids_data = pd.concat([st.session_state.poids_data, pd.DataFrame([nouveau_poids])], ignore_index=True)
st.success("Poids enregistré !")
st.rerun()

if not st.session_state.poids_data.empty:
df_poids = st.session_state.poids_data.sort_values(by="Date")
st.line_chart(df_poids.set_index("Date")["Poids"])

# Dernier poids affiché en gros
dernier_poids = df_poids.iloc[-1]["Poids"]
st.metric(label="Dernier poids enregistré", value=f"{dernier_poids} kg")

# --- ONGLET 3 : DEFICIT CALORIQUE ---
with menu[2]:
st.header("🔥 Mon Déficit")

date_cal = st.date_input("Choisir le jour", datetime.date.today())
date_str = str(date_cal)

# Initialiser la journée si elle n'existe pas
if date_str not in st.session_state.calories_data:
st.session_state.calories_data[date_str] = {"mange": 1600, "brules_base": 1800, "sport": 0}

# Vérifier si du sport a été validé ce jour-là
seances_du_jour = st.session_state.sport_data[(st.session_state.sport_data["Date"] == date_cal) & (st.session_state.sport_data["Fait"] == True)]
sport_auto = 0
for _, s in seances_du_jour.iterrows():
sport_auto += int(s["Duree"] * 6) # Base moyenne de 6kcal/min

st.session_state.calories_data[date_str]["sport"] = sport_auto

# Formulaire d'alimentation
mange = st.number_input("Calories mangées aujourd'hui (kcal)", min_value=0, value=st.session_state.calories_data[date_str]["mange"], step=50)
base = st.number_input("Votre métabolisme de base (kcal)", min_value=0, value=st.session_state.calories_data[date_str]["brules_base"], step=50)

st.session_state.calories_data[date_str]["mange"] = mange
st.session_state.calories_data[date_str]["brules_base"] = base

# Calcul final
total_brules = base + sport_auto
deficit = total_brules - mange

st.write("---")

if deficit > 0:
st.success(f"💚 **Déficit atteint !**\n\nVous avez éliminé **{deficit} kcal** de plus que ce que vous avez mangé.")
else:
st.error(f"❤️ **Pas de déficit aujourd'hui**\n\nVous avez un surplus de **{abs(deficit)} kcal**.")

# Petit récapitulatif visuel
st.caption(f"Détails : Brûlées ({total_brules} kcal dont {sport_auto} via le sport) - Mangées ({mange} kcal)")
