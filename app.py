import streamlit as st
import pandas as pd
import calendar
import random
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="Master Guardia Medica - Porto Empedocle", layout="wide")

st.markdown("""
    <style>
    .main-title { color: #1a365d; font-family: 'Helvetica', sans-serif; font-weight: 700; font-size: 2.3rem; border-bottom: 3px solid #63b3ed; padding-bottom: 10px; margin-bottom: 25px; }
    .settings-section { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNZIONI UTILI ---
def get_festivita(anno):
    """Ritorna un dizionario con le festività nazionali italiane + Patrono"""
    def pasqua(y):
        a, b, c = y % 19, y // 100, y % 100
        d, e, f = b // 4, b % 4, (b + 8) // 25
        g, h = (b - f + 1) // 3, (19 * a + b - d - g + 15) % 30
        i, k = c // 4, c % 4
        l = (32 + 2 * e + 2 * i - h - k) % 7
        m = (a + 11 * h + 22 * l) // 451
        mese = (h + l - 7 * m + 114) // 31
        giorno = ((h + l - 7 * m + 114) % 31) + 1
        return giorno, mese

    g_p, m_p = pasqua(anno)
    dt_p = datetime(anno, m_p, g_p)
    # Calcolo Pasquetta in modo sicuro
    try:
        dt_pp = dt_p.replace(day=g_p+1)
    except ValueError:
        dt_pp = datetime(anno, m_p+1, 1)

    fest = {
        (1, 1): "Capodanno", (6, 1): "Epifania",
        (25, 4): "Liberazione", (1, 5): "Festa Lavoro", (2, 6): "Festa Repubblica",
        (15, 8): "Ferragosto", (1, 11): "Ognissanti", (8, 12): "Immacolata",
        (25, 12): "Natale", (26, 12): "S. Stefano",
        (dt_p.day, dt_p.month): "Pasqua", (dt_pp.day, dt_pp.month): "Pasquetta",
        (25, 2): "S. Patrono" # Aggiunto Santo Patrono
    }
    return fest

def calcola_durata(intervallo):
    try:
        if "---" in str(intervallo) or not intervallo: return 0
        parti = intervallo.split("-")
        inizio = datetime.strptime(parti[0].strip(), "%H:%M")
        fine = datetime.strptime(parti[1].strip(), "%H:%M")
        durata = (fine - inizio).seconds / 3600
        if durata <= 0: durata += 24 
        return durata
    except: return 0

# --- 3. STATO SESSIONE ---
if 'medici' not in st.session_state: 
    st.session_state.medici = ["Piscopo", "Celani", "Lombardo", "Siracusa"]
if 'assenze' not in st.session_state: 
    st.session_state.assenze = {m: [] for m in st.session_state.medici}
if 'db_turni' not in st.session_state: 
    st.session_state.db_turni = pd.DataFrame()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown("## 📅 Periodo")
    anno_sel = st.number_input("Anno:", min_value=2024, max_value=2030, value=2026)
    mesi_ita = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
    mese_nome = st.selectbox("Mese:", mesi_ita, index=1)
    m_idx_v = mesi_ita.index(mese_nome) + 1
    festivita_anno = get_festivita(anno_sel)

    st.divider()
    st.markdown("## 👨‍⚕️ Staff")
    nuovo_m = st.text_input("Aggiungi Medico:")
    if st.button("AGGIUNGI"):
        if nuovo_m and nuovo_m not in st.session_state.medici:
            st.session_state.medici.append(nuovo_m)
            st.session_state.assenze[nuovo_m] = []
            st.rerun()

    for med in st.session_state.medici:
        c_n, c_d = st.columns([4, 1])
        c_n.write(f"**{med}**")
        if c_d.button("X", key=f"del_{med}"):
            st.session_state.medici.remove(med)
            st.rerun()
    
    st.divider()
    st.markdown("### 📅 Indisponibilità")
    m_sel = st.selectbox("Seleziona Medico:", st.session_state.medici)
    
    st.write("Segna tutti i:")
    giorni_sett = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
    cols_scor = st.columns(4)
    for i, g_nome in enumerate(giorni_sett):
        if cols_scor[i %
