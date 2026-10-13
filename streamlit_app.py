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


def delete_record(identifier):
    try:
        query = '?' + urllib.parse.urlencode({'id': 'eq.' + identifier})
        api('DELETE', query)
    except (urllib.error.URLError, TimeoutError, ValueError):
        st.error('La suppression a échoué. Réessaie : la saisie est encore conservée.')
        return False
    st.session_state['notice'] = 'Supprimé ✓'
    return True


def open_session(identifier, day):
    st.session_state['selected_day'] = day
    st.session_state['editing_session'] = identifier
    st.session_state.pop('confirm_delete', None)


def select_day(day):
    st.session_state['selected_day'] = day
    st.session_state.pop('editing_session', None)
    st.session_state.pop('confirm_delete', None)


def calorie_navigation(day):
    st.session_state['main_nav'] = '🔥 Calories'
    st.session_state['calorie_date'] = day


st.set_page_config(page_title='Mon suivi personnel', page_icon='📅', layout='centered')
st.markdown("""
<style>
.block-container {max-width:900px;padding:1rem .6rem 3rem;}
h1 {font-size:1.65rem!important;}
h2 {font-size:1.2rem!important;}
[data-testid="stButton"] button {width:100%;min-height:2.6rem;border-radius:8px;}
.st-key-navigation [role="radiogroup"] {display:flex;flex-wrap:nowrap;gap:6px;}
.st-key-navigation [role="radiogroup"] > label {flex:1;justify-content:center;border:1px solid #b8c9d9;border-radius:10px;padding:9px 3px;background:#f3f7fa;}
.st-key-navigation [role="radiogroup"] > label:has(input:checked) {background:#dcebf7;border-color:#2474a8;}
.st-key-navigation [role="radiogroup"] > label p {font-size:14px!important;color:#16354c;}
.st-key-calgrid [data-testid="stHorizontalBlock"], .st-key-monthnav [data-testid="stHorizontalBlock"] {flex-wrap:nowrap!important;gap:2px!important;}
.st-key-calgrid [data-testid="stColumn"], .st-key-monthnav [data-testid="stColumn"] {min-width:0!important;}
.st-key-calgrid [data-testid="stVerticalBlock"] {gap:3px!important;}
[class*="st-key-calday_"] {border:1px solid #aabdcf!important;border-radius:2px!important;padding:4px!important;min-height:150px;background:#fff;}
[class*="st-key-calday_weekend_"] {background:#f3f6fa;}
[class*="st-key-calday_outside_"] {background:#eef1f5;}
[class*="st-key-calday_selected_"] {background:#e5f1fc;border:2px solid #2678b6!important;}
[class*="st-key-calday_"] [data-testid="stButton"] button {min-height:27px;border-radius:3px;padding:2px;border:0;}
[class*="st-key-datebutton_"] button {background:transparent;color:#334155;font-weight:700;}
[class*="st-key-datebutton_"] button p {font-size:12px!important;}
[class*="st-key-datebutton_today_"] button {background:#dbeafe;color:#144e82;}
[class*="st-key-event_"] button {border-left:4px solid!important;}
[class*="st-key-event_"] button p {font-size:11px!important;line-height:1.25!important;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}
[class*="st-key-event_salle_"] button {background:#eee5f8;color:#613390;border-color:#8154bc!important;}
[class*="st-key-event_course_"] button {background:#ddecf9;color:#145883;border-color:#277cb5!important;}
[class*="st-key-event_autre_"] button {background:#fff0de;color:#8e4610;border-color:#ad5b16!important;}
[class*="st-key-event_yes_"] button {background:#dff2e5;color:#12642e;border-color:#15803d!important;}
[class*="st-key-event_no_"] button {background:#fbe4e4;color:#982626;border-color:#b91c1c!important;}
.weekday {text-align:center;font-size:12px;font-weight:600;background:#e8eff5;color:#28455d;padding:8px 0;border:1px solid #aabdcf;}
.day-short {display:none;}
.legend {font-size:12px;line-height:1.8;margin-bottom:8px;}
@media(max-width:600px) {
 .day-full {display:none;}.day-short {display:inline;}
 [class*="st-key-calday_"] {padding:2px!important;min-height:132px;}
 [class*="st-key-event_"] button {border-left-width:2px!important;}
 [class*="st-key-event_"] button p {font-size:10px!important;}
 .weekday {font-size:11px;}
}
</style>
""", unsafe_allow_html=True)
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
# Un sélecteur mémorisé évite le retour à l'agenda lors des saisies,
# y compris avec les versions Streamlit qui ne mémorisent pas les onglets.
with st.container(key='navigation'):
    page = st.radio('Navigation', ['📅 Agenda', '⚖️ Poids', '🔥 Calories'],
                    key='main_nav', horizontal=True, label_visibility='collapsed')

if page == '📅 Agenda':
    month = st.session_state['month']
    with st.container(key='monthnav'):
        left, title, right = st.columns([1, 5, 1])
        with left:
            if st.button('←', disabled=month <= START, key='prev'):
                st.session_state['month'] = month_shift(month, -1)
                st.rerun()
        with title:
            st.markdown(f"<div style='text-align:center;font-size:19px;font-weight:700;padding:8px 0'>{MONTHS[month.month-1]} {month.year}</div>", unsafe_allow_html=True)
        with right:
            if st.button('→', disabled=month >= END.replace(day=1), key='next'):
                st.session_state['month'] = month_shift(month, 1)
                st.rerun()
    if st.button('Aujourd’hui', disabled=not START <= TODAY <= END):
        st.session_state['month'] = TODAY.replace(day=1)
        select_day(TODAY)
        st.rerun()
    st.markdown('<div class="legend">🟣 Salle · 🔵 Course · 🟠 Autre · ✓ Réalisée<br>Déficit : vert = oui · rouge = non</div>', unsafe_allow_html=True)
    with st.container(key='calgrid'):
        full_days = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        short_days = ['Lun.', 'Mar.', 'Mer.', 'Jeu.', 'Ven.', 'Sam.', 'Dim.']
        for col, full, short in zip(st.columns(7), full_days, short_days):
            with col:
                st.markdown(f'<div class="weekday"><span class="day-full">{full}</span><span class="day-short">{short}</span></div>', unsafe_allow_html=True)
        for week in calendar.Calendar(firstweekday=0).monthdatescalendar(month.year, month.month):
            for col, day in zip(st.columns(7), week):
                with col:
                    in_month = day.month == month.month
                    style = 'selected' if day == st.session_state['selected_day'] else 'outside' if not in_month else 'weekend' if day.weekday() >= 5 else 'normal'
                    with st.container(border=True, key=f'calday_{style}_{day}'):
                        with st.container(key=f"datebutton_{'today' if day == TODAY else 'normal'}_{day}"):
                            st.button(str(day.day), key=f'day_{day}', disabled=not in_month,
                                      help=day.strftime('%d/%m/%Y'), on_click=select_day, args=(day,))
                        if in_month:
                            events = [r for r in sessions if r['event_date'] == day.isoformat()]
                            for event in events[:3]:
                                p = event['payload']
                                color_name = {'Salle de sport':'salle', 'Course à pied':'course'}.get(p['type'], 'autre')
                                label = SHORT.get(p['type'], 'Autre') + (' ✓' if p.get('done') else '')
                                with st.container(key='event_' + color_name + '_' + event['id']):
                                    st.button(label, key='calendar_event_' + event['id'],
                                              help=p.get('details') or 'Ouvrir la séance',
                                              on_click=open_session, args=(event['id'], day))
                            if len(events) > 3:
                                st.button(f'+{len(events)-3}', key=f'more_{day}', on_click=select_day, args=(day,))
                            entry = calories.get(day.isoformat())
                            if entry:
                                p = entry['payload']
                                with st.container(key=f"event_{'yes' if p['deficit'] else 'no'}_{day}"):
                                    st.button(f"Déficit {p['amount']}" if p['deficit'] else 'Déficit',
                                              key=f'calendar_cal_{day}',
                                              help=f"{p['amount']} kcal" if p['deficit'] else 'Déficit : non',
                                              on_click=calorie_navigation, args=(day,))
    selected = st.session_state['selected_day']
    st.subheader('📍 ' + selected.strftime('%d/%m/%Y'))
    st.caption('Touche une séance dans le calendrier pour voir ses commentaires et la modifier ci-dessous.')
    selected_cal = calories.get(selected.isoformat())
    if selected_cal:
        p = selected_cal['payload']
        st.write(f"🔥 Déficit : {p['amount']} kcal" if p['deficit'] else '🔥 Déficit : non')
        st.button('Modifier ce bilan', on_click=calorie_navigation, args=(selected,))
    daily_sessions = [s for s in sessions if s['event_date'] == selected.isoformat()]
    if not daily_sessions:
        st.caption('Aucune séance programmée ce jour.')
    for event in daily_sessions:
        p = event['payload']
        st.button(f"{p['type']}{' ✓' if p.get('done') else ''} — {p.get('details') or 'Voir la séance'}",
                  key='open_' + event['id'], on_click=open_session, args=(event['id'], selected))
    editing = next((s for s in daily_sessions if s['id'] == st.session_state.get('editing_session')), None)
    if editing:
        p = editing['payload']
        with st.container(border=True):
            st.subheader('Détails de la séance')
            if p.get('notes'):
                st.write(p['notes'])
            else:
                st.caption('Aucun commentaire enregistré.')
            with st.form('edit_' + editing['id']):
                event_date = st.date_input('Date de la séance', dt.date.fromisoformat(editing['event_date']),
                                           min_value=START, max_value=END, format='DD/MM/YYYY', key='edit_date_' + editing['id'])
                sport_type = st.selectbox('Activité', SPORTS, index=SPORTS.index(p['type']))
                details = st.text_input('Séance / objectif', value=p.get('details', ''))
                done = st.checkbox('Séance réalisée ✓', value=p.get('done', False))
                duration = st.number_input('Durée (minutes)', min_value=0, value=int(p.get('duration', 0)))
                km = st.number_input('Distance (km, si utile)', min_value=0.0, value=float(p.get('km', 0)), step=.1)
                notes = st.text_area('Exercices, séries, poids soulevés et commentaires', value=p.get('notes', ''))
                if st.form_submit_button('Enregistrer les modifications'):
                    if save_record(editing['id'], 'sport', event_date, {'type': sport_type, 'details': details, 'done': done, 'duration': duration, 'km': km, 'notes': notes}):
                        st.session_state['month'] = event_date.replace(day=1)
                        st.session_state['selected_day'] = event_date
                        st.rerun()
            if st.button('🗑️ Supprimer cette séance', key='delete_' + editing['id']):
                st.session_state['confirm_delete'] = editing['id']
            if st.session_state.get('confirm_delete') == editing['id']:
                st.warning('Supprimer définitivement cette séance et ses commentaires ?')
                if st.button('Confirmer la suppression', key='confirm_' + editing['id']):
                    if delete_record(editing['id']):
                        st.session_state.pop('editing_session', None)
                        st.session_state.pop('confirm_delete', None)
                        st.rerun()
                if st.button('Annuler', key='cancel_' + editing['id']):
                    st.session_state.pop('confirm_delete', None)
                    st.rerun()
    with st.expander('➕ Programmer une séance'):
        with st.form('add_sport_' + selected.isoformat()):
            date = st.date_input('Date de la séance', selected, min_value=START, max_value=END, format='DD/MM/YYYY')
            sport_type = st.selectbox('Activité', SPORTS)
            details = st.text_input('Séance / objectif')
            notes = st.text_area('Commentaires')
            if st.form_submit_button('Programmer'):
                if save_record(str(uuid.uuid4()), 'sport', date, {'type': sport_type, 'details': details, 'done': False, 'duration': 0, 'km': 0.0, 'notes': notes}):
                    st.session_state['month'] = date.replace(day=1)
                    st.session_state['selected_day'] = date
                    st.rerun()

elif page == '⚖️ Poids':
    st.header('⚖️ Mon poids')
    date_weight = st.date_input('Date de la pesée', DEFAULT, min_value=START, max_value=END,
                                format='DD/MM/YYYY', key='weight_date')
    previous = next((r for r in weights if r['event_date'] == date_weight.isoformat()), None)
    with st.form('weight_' + date_weight.isoformat()):
        value = st.number_input('Poids (kg)', min_value=1.0, max_value=300.0,
                                value=float(previous['payload']['weight']) if previous else float(weights[-1]['payload']['weight']) if weights else 64.0, step=.1)
        if st.form_submit_button('Enregistrer le poids'):
            if save_record('poids_' + date_weight.isoformat(), 'poids', date_weight, {'weight': value}):
                st.rerun()
    st.caption('Choisis une date passée pour ajouter une pesée ou corriger son poids.')
    if weights:
        df = pd.DataFrame([{'Date': r['event_date'], 'Poids': float(r['payload']['weight'])} for r in weights])
        first = dt.date.fromisoformat(weights[0]['event_date']).replace(day=1)
        last = month_shift(dt.date.fromisoformat(weights[-1]['event_date']).replace(day=1), 1)
        ticks = []
        cursor = first
        while cursor < last:
            ticks.append(cursor.isoformat())
            cursor = month_shift(cursor, 1)
        stride = max(1, (len(ticks) + 5) // 6)
        axis_labels = "['Janv.','Févr.','Mars','Avr.','Mai','Juin','Juil.','Août','Sept.','Oct.','Nov.','Déc.'][utcmonth(datum.value)] + ' ' + utcyear(datum.value)"
        spec = {
            'height': 260,
            'mark': {'type':'line', 'point':True, 'color':'#277cb5'},
            'encoding': {
                'x': {'field':'Date', 'type':'temporal', 'title':None,
                      'scale':{'type':'utc', 'domain':[first.isoformat(), last.isoformat()]},
                      'axis':{'values':ticks[::stride], 'labelExpr':axis_labels, 'labelAngle':-30, 'labelOverlap':False}},
                'y': {'field':'Poids', 'type':'quantitative', 'title':'Poids (kg)', 'scale':{'zero':False}},
                'tooltip': [{'field':'Date', 'type':'temporal', 'format':'%d/%m/%Y', 'title':'Date'},
                            {'field':'Poids', 'type':'quantitative', 'title':'Poids (kg)', 'format':'.1f'}]
            }
        }
        st.vega_lite_chart(df, spec, use_container_width=True)
        st.metric('Dernier poids enregistré', f"{weights[-1]['payload']['weight']:.1f} kg")
        history = df.copy()
        history['Date'] = pd.to_datetime(history['Date'])
        st.subheader('Historique des pesées')
        st.dataframe(history.sort_values('Date', ascending=False), hide_index=True,
                     column_config={'Date':st.column_config.DateColumn('Date', format='DD/MM/YYYY'),
                                    'Poids':st.column_config.NumberColumn('Poids (kg)', format='%.1f')})
    else:
        st.info('Aucune pesée enregistrée pour le moment.')

elif page == '🔥 Calories':
    st.header('🔥 Déficit')
    st.session_state.setdefault('calorie_date', DEFAULT)
    calorie_date = st.date_input('Date du bilan', None, min_value=START, max_value=END,
                                 format='DD/MM/YYYY', key='calorie_date')
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
    if previous:
        if st.button('Effacer ce bilan', key='erase_cal_' + calorie_date.isoformat()):
            if delete_record(previous['id']):
                st.session_state.pop('answer_' + calorie_date.isoformat(), None)
                st.session_state.pop('amount_' + calorie_date.isoformat(), None)
                st.rerun()
    st.caption('Le bilan enregistré apparaît automatiquement dans l’agenda. Sans saisie, aucune mention ne s’affiche. La couleur décrit ta saisie ; ce n’est pas une note sur ta journée.')

with st.sidebar:
    st.download_button('Télécharger une copie de mes données', json.dumps(records, ensure_ascii=False, indent=2),
                       file_name='mon_suivi_' + TODAY.isoformat() + '.json', mime='application/json')
