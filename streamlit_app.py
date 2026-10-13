import calendar
import datetime as dt
import hmac
import html
import json
import uuid
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

END = dt.date(2027, 12, 31)
START = dt.date(2020, 1, 1)
MONTHS = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
SPORTS = ['Salle de sport', 'Course à pied', 'Autre']
COLORS = {'Salle de sport': '#8154bc', 'Course à pied': '#277cb5', 'Autre': '#ad5b16'}
SHORT = {'Salle de sport': 'Salle', 'Course à pied': 'Course', 'Autre': 'Autre'}
TODAY = dt.datetime.now(ZoneInfo('Europe/Paris')).date()
DEFAULT = min(max(TODAY, START), END)


def month_shift(month, step):
    offset = month.year * 12 + month.month - 1 + step
    year, index = divmod(offset, 12)
    return dt.date(year, index + 1, 1)


def api(method, query='', body=None):
    headers = {'apikey': API_KEY, 'Content-Type': 'application/json'}
    # Les anciennes clés service_role sont des JWT. Les nouvelles clés
    # sb_secret_ utilisent uniquement l'en-tête apikey.
    if not API_KEY.startswith('sb_secret_'):
        headers['Authorization'] = 'Bearer ' + API_KEY
    if method == 'POST':
        headers['Prefer'] = 'resolution=merge-duplicates,return=minimal'
    raw = None if body is None else json.dumps(body, ensure_ascii=False).encode('utf-8')
    request = urllib.request.Request(
        DB_URL + '/rest/v1/suivi_personnel' + query,
        data=raw, headers=headers, method=method
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        result = response.read()
        return json.loads(result) if result else None


def load_records():
    result = []
    offset = 0
    while True:
        page = api('GET', f'?select=*&order=id.asc&limit=500&offset={offset}')
        result.extend(page)
        if len(page) < 500:
            return result
        offset += 500


def save_record(identifier, kind, date, payload):
    try:
        api('POST', '?on_conflict=id', {
            'id': identifier, 'kind': kind, 'event_date': date.isoformat(),
            'payload': payload
        })
    except (urllib.error.URLError, TimeoutError, ValueError):
        st.error("L'enregistrement a échoué. Tes changements ne sont pas sauvegardés : réessaie.")
        return False
    st.session_state['notice'] = 'Enregistré ✓'
    return True


def badge(text, color):
    return (f'<div class="badge" style="background:{color}" '
            f'title="{html.escape(text, quote=True)}">{html.escape(text)}</div>')


st.set_page_config(page_title='Mon suivi personnel', page_icon='📅', layout='centered')
st.markdown('''
<style>
.block-container {max-width:780px;padding:1rem .65rem 3rem;}
h1 {font-size:1.6rem!important;}
h2 {font-size:1.2rem!important;}
[data-testid="stHorizontalBlock"] {flex-wrap:nowrap!important;gap:.25rem!important;}
[data-testid="stColumn"] {min-width:0!important;}
[data-testid="stButton"] button {width:100%;min-height:2.65rem;border-radius:10px;padding:.2rem;}
.badges {height:66px;overflow:hidden;margin-top:-8px;}
.badge {font-size:10px;line-height:18px;margin:2px 0;border-radius:3px;color:white;padding:0 2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.weekday {text-align:center;font-size:12px;color:#6b7280;font-weight:600;}
.legend {font-size:12px;line-height:1.8;color:#475569;margin-bottom:10px;}
[data-testid="stTabs"] button {font-size:14px;}
</style>
''', unsafe_allow_html=True)
st.title('📅 Mon suivi personnel')

try:
    DB_URL = str(st.secrets.get('SUPABASE_URL', '')).rstrip('/')
    API_KEY = str(st.secrets.get('SUPABASE_KEY', ''))
    PASSWORD = str(st.secrets.get('APP_PASSWORD', ''))
except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
    DB_URL = API_KEY = PASSWORD = ''

if not DB_URL or not API_KEY or not PASSWORD:
    st.info("Il reste à connecter la sauvegarde. Suis le fichier GUIDE_INSTALLATION.txt fourni avec cette version.")
    st.stop()
if not DB_URL.startswith('https://'):
    st.error('SUPABASE_URL doit commencer par https://.')
    st.stop()

if not st.session_state.get('signed_in', False):
    st.write('Entre ton mot de passe pour accéder à ton suivi.')
    with st.form('login'):
        entered = st.text_input('Mot de passe', type='password')
        submitted = st.form_submit_button('Ouvrir mon suivi')
    if submitted:
        if hmac.compare_digest(entered.encode(), PASSWORD.encode()):
            st.session_state['signed_in'] = True
            st.rerun()
        else:
            st.error('Mot de passe incorrect.')
    st.stop()

with st.sidebar:
    st.caption('Ton suivi personnel')
    if st.button('Actualiser les données'):
        st.rerun()
    if st.button('Se déconnecter'):
        st.session_state.clear()
        st.rerun()

try:
    records = load_records()
except (urllib.error.URLError, TimeoutError, ValueError):
    st.error("Connexion à la sauvegarde impossible. Vérifie la configuration Supabase et la création de la table, puis réessaie.")
    st.stop()

if 'notice' in st.session_state:
    st.success(st.session_state.pop('notice'))

sessions = [r for r in records if r['kind'] == 'sport']
weights = sorted([r for r in records if r['kind'] == 'poids'], key=lambda r: r['event_date'])
calories = {r['event_date']: r for r in records if r['kind'] == 'calories'}
st.session_state.setdefault('month', DEFAULT.replace(day=1))
st.session_state.setdefault('selected_day', DEFAULT)
ag, wt, cal = st.tabs(['📅 Agenda', '⚖️ Poids', '🔥 Calories'])

with ag:
    month = st.session_state['month']
    left, title, right = st.columns([1, 5, 1])
    with left:
        if st.button('←', disabled=month <= START, key='prev'):
            st.session_state['month'] = month_shift(month, -1)
            st.rerun()
    with title:
        st.markdown(f"<div style='text-align:center;font-size:18px;font-weight:700;padding:8px 0'>{MONTHS[month.month-1]} {month.year}</div>", unsafe_allow_html=True)
    with right:
        if st.button('→', disabled=month >= END.replace(day=1), key='next'):
            st.session_state['month'] = month_shift(month, 1)
            st.rerun()
    if st.button('Aujourd’hui', disabled=TODAY > END or TODAY < START):
        st.session_state['month'] = TODAY.replace(day=1)
        st.session_state['selected_day'] = TODAY
        st.rerun()
    st.markdown('<div class="legend">🟣 Salle · 🔵 Course · 🟠 Autre · ✓ Réalisée<br>Déficit : vert = oui · rouge = non</div>', unsafe_allow_html=True)
    for col, label in zip(st.columns(7), ['L', 'M', 'M', 'J', 'V', 'S', 'D']):
        with col:
            st.markdown(f'<div class="weekday">{label}</div>', unsafe_allow_html=True)
    for week in calendar.Calendar(firstweekday=0).monthdatescalendar(month.year, month.month):
        for col, day in zip(st.columns(7), week):
            with col:
                in_month = day.month == month.month
                if st.button(str(day.day) if in_month else '·', key=f'day_{day}', disabled=not in_month,
                             type='primary' if day == st.session_state['selected_day'] else 'secondary'):
                    st.session_state['selected_day'] = day
                    st.session_state.pop('editing_session', None)
                    st.rerun()
                marks = []
                if in_month:
                    events = [s for s in sessions if s['event_date'] == day.isoformat()]
                    # Deux badges visibles ; les détails affichent toutes les séances.
                    for event in events[:2]:
                        p = event['payload']
                        marks.append(badge(SHORT.get(p['type'], 'Autre') + (' ✓' if p.get('done') else ''), COLORS.get(p['type'], '#ad5b16')))
                    entry = calories.get(day.isoformat())
                    if entry:
                        p = entry['payload']
                        label = f"Déficit {p['amount']}" if p['deficit'] else 'Déficit'
                        marks.append(badge(label, '#15803d' if p['deficit'] else '#b91c1c'))
                st.markdown('<div class="badges">' + ''.join(marks) + '</div>', unsafe_allow_html=True)
    selected = st.session_state['selected_day']
    st.subheader('📍 ' + selected.strftime('%d/%m/%Y'))
    st.caption('Touche une date, puis une séance pour la compléter ou la modifier. Les montants du calendrier sont en kcal.')
    selected_cal = calories.get(selected.isoformat())
    if selected_cal:
        p = selected_cal['payload']
        st.write(f"🔥 Déficit : {p['amount']} kcal" if p['deficit'] else '🔥 Déficit : non')
    daily_sessions = [s for s in sessions if s['event_date'] == selected.isoformat()]
    if not daily_sessions:
        st.caption('Aucune séance programmée ce jour.')
    for event in daily_sessions:
        p = event['payload']
        if st.button(f"{p['type']}{' ✓' if p.get('done') else ''} — {p.get('details') or 'Voir la séance'}", key='open_' + event['id']):
            st.session_state['editing_session'] = event['id']
            st.rerun()
    editing = next((s for s in daily_sessions if s['id'] == st.session_state.get('editing_session')), None)
    if editing:
        p = editing['payload']
        with st.form('edit_' + editing['id']):
            st.write('Détails de la séance')
            sport_type = st.selectbox('Activité', SPORTS, index=SPORTS.index(p['type']))
            details = st.text_input('Séance / objectif', value=p.get('details', ''))
            done = st.checkbox('Séance réalisée ✓', value=p.get('done', False))
            duration = st.number_input('Durée (minutes)', min_value=0, value=int(p.get('duration', 0)))
            km = st.number_input('Distance (km, si utile)', min_value=0.0, value=float(p.get('km', 0)), step=.1)
            notes = st.text_area('Exercices, séries, poids soulevés et notes', value=p.get('notes', ''))
            if st.form_submit_button('Enregistrer les détails'):
                if save_record(editing['id'], 'sport', selected, {'type': sport_type, 'details': details, 'done': done, 'duration': duration, 'km': km, 'notes': notes}):
                    st.rerun()
    with st.expander('➕ Programmer une séance'):
        with st.form('add_sport_' + selected.isoformat()):
            date = st.date_input('Date de la séance', selected, min_value=START, max_value=END)
            sport_type = st.selectbox('Activité', SPORTS)
            details = st.text_input('Séance / objectif')
            if st.form_submit_button('Programmer'):
                if save_record(str(uuid.uuid4()), 'sport', date, {'type': sport_type, 'details': details, 'done': False, 'duration': 0, 'km': 0.0, 'notes': ''}):
                    st.session_state['month'] = date.replace(day=1)
                    st.session_state['selected_day'] = date
                    st.rerun()

with wt:
    st.header('⚖️ Mon poids')
    date_weight = st.date_input('Date de la pesée', DEFAULT, min_value=START, max_value=END, key='weight_date')
    previous = next((r for r in weights if r['event_date'] == date_weight.isoformat()), None)
    with st.form('weight_' + date_weight.isoformat()):
        value = st.number_input('Poids (kg)', min_value=1.0, max_value=300.0,
                                value=float(previous['payload']['weight']) if previous else float(weights[-1]['payload']['weight']) if weights else 64.0, step=.1)
        if st.form_submit_button('Enregistrer le poids'):
            if save_record('poids_' + date_weight.isoformat(), 'poids', date_weight, {'weight': value}):
                st.rerun()
    st.caption('Une nouvelle saisie à la même date remplace la précédente.')
    if weights:
        df = pd.DataFrame([{'Date': pd.to_datetime(r['event_date']), 'Poids': float(r['payload']['weight'])} for r in weights])
        st.line_chart(df.set_index('Date')['Poids'])
        st.metric('Dernier poids enregistré', f"{weights[-1]['payload']['weight']:.1f} kg")
        with st.expander('Historique'):
            st.dataframe(df.sort_values('Date', ascending=False), hide_index=True)
    else:
        st.info('Aucune pesée enregistrée pour le moment.')

with cal:
    st.header('🔥 Déficit')
    calorie_date = st.date_input('Date du bilan', DEFAULT, min_value=START, max_value=END, key='calorie_date')
    previous = calories.get(calorie_date.isoformat())
    previous_p = previous['payload'] if previous else {}
    answer = st.radio('Déficit ce jour-là ?', ['À renseigner', 'Oui', 'Non'],
                      index=(1 if previous_p.get('deficit') else 2) if previous else 0,
                      key='answer_' + calorie_date.isoformat(), horizontal=True)
    amount = 0
    if answer == 'Oui':
        amount = st.number_input('Montant du déficit estimé (kcal)', min_value=0, step=10,
                                 value=int(previous_p.get('amount', 0)), key='amount_' + calorie_date.isoformat())
    if st.button('Enregistrer le bilan', disabled=answer == 'À renseigner'):
        if answer == 'Oui' and amount <= 0:
            st.info('Renseigne le montant avant d’enregistrer.')
        elif save_record('calories_' + calorie_date.isoformat(), 'calories', calorie_date, {'deficit': answer == 'Oui', 'amount': amount if answer == 'Oui' else 0}):
            st.session_state['month'] = calorie_date.replace(day=1)
            st.session_state['selected_day'] = calorie_date
            st.rerun()
    st.caption('Le bilan enregistré apparaît automatiquement dans l’agenda. Sans saisie, aucune mention ne s’affiche. La couleur décrit ta saisie ; ce n’est pas une note sur ta journée.')

with st.sidebar:
    st.download_button('Télécharger une copie de mes données', json.dumps(records, ensure_ascii=False, indent=2),
                       file_name='mon_suivi_' + TODAY.isoformat() + '.json', mime='application/json')
