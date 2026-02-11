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

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="Master Guardia Medica - Porto Empedocle", layout="wide")

# --- 2. LOGICA FESTIVITÀ & DESCRIZIONI ---
def get_info_giorno(dt):
    festivi_fissi = {
        (1, 1): "CAPODANNO",
        (6, 1): "EPIFANIA",
        (25, 2): "SAN GERLANDO (Patrono)",
        (25, 4): "FESTA DELLA LIBERAZIONE",
        (1, 5): "FESTA DEI LAVORATORI",
        (2, 6): "FESTA DELLA REPUBBLICA",
        (15, 8): "FERRAGOSTO",
        (1, 11): "OGNISSANTI",
        (8, 12): "IMMACOLATA CONCEZIONE",
        (25, 12): "NATALE",
        (26, 12): "SANTO STEFANO"
    }
    if dt.month == 4 and dt.day == 5: return "Festivo", "PASQUA"
    if dt.month == 4 and dt.day == 6: return "Festivo", "LUNEDÌ DELL'ANGELO"
    if dt.month == 2 and dt.day == 25: return "Festivo", "SAN GERLANDO"
    if dt.month == 2 and dt.day == 24: return "Prefestivo", "VIGILIA PATRONO"
    if (dt.day, dt.month) in festivi_fissi:
        return "Festivo", festivi_fissi[(dt.day, dt.month)]
    wd = dt.weekday()
    if wd == 6: return "Festivo", "DOMENICA"
    if wd == 5: return "Prefestivo", "SABATO"
    return "Feriale", ""

# --- 3. FUNZIONI UTILI ---
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

# --- 4. STATO SESSIONE ---
if 'medici' not in st.session_state: 
    st.session_state.medici = ["Piscopo", "Celani", "Lombardo", "Siracusa"]
if 'assenze' not in st.session_state: 
    st.session_state.assenze = {m: [] for m in st.session_state.medici}
if 'db_turni' not in st.session_state: 
    st.session_state.db_turni = pd.DataFrame()

# --- 5. SIDEBAR ---
with st.sidebar:
    st.header("📅 Periodo e Staff")
    anno_sel = st.number_input("Anno:", min_value=2024, max_value=2030, value=2026)
    mesi_ita = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
    mese_nome = st.selectbox("Mese:", mesi_ita, index=1)
    m_idx_v = mesi_ita.index(mese_nome) + 1

    st.divider()
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
    st.header("🚫 Indisponibilità")
    m_sel = st.selectbox("Seleziona Medico:", st.session_state.medici)
    
    st.write("Segna tutti i:")
    g_sett = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
    cols_s = st.columns(4)
    for i, g_nome in enumerate(g_sett):
        if cols_s[i % 4].button(g_nome, key=f"btn_{g_nome}"):
            for d in range(1, 32):
                try:
                    if datetime(anno_sel, m_idx_v, d).weekday() == i:
                        if d not in st.session_state.assenze[m_sel]: st.session_state.assenze[m_sel].append(d)
                except: pass
            st.rerun()
    
    st.write("Calendario:")
    cal = calendar.monthcalendar(anno_sel, m_idx_v)
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day != 0:
                is_abs = day in st.session_state.assenze.get(m_sel, [])
                if cols[i].button(str(day), key=f"d_btn_{day}", type="primary" if is_abs else "secondary"):
                    if is_abs: st.session_state.assenze[m_sel].remove(day)
                    else: st.session_state.assenze[m_sel].append(day)
                    st.rerun()

# --- 6. DASHBOARD ORARI ---
st.title(f"Gestione Turni Porto Empedocle - {mese_nome} {anno_sel}")

col1, col2, col3 = st.columns(3)
with col1:
    f_n = st.text_input("Notte Feriale", value="20:00 - 08:00")
with col2:
    p_p = st.text_input("Pom. Prefestivo", value="10:00 - 20:00")
    p_n = st.text_input("Notte Prefestivo", value="20:00 - 08:00")
with col3:
    div_f = st.toggle("Dividi Mattina Festiva", value=True)
    fes_m = st.text_input("Mattina Festiva", value="08:00 - 14:00")
    fes_p = st.text_input("Pom. Festivo", value="14:00 - 20:00")
    fes_n = st.text_input("Notte Festiva", value="20:00 - 08:00")

# --- 7. GENERAZIONE LOGICA ---
st.divider()
if st.button("🚀 GENERA PIANO TURNI", type="primary", use_container_width=True):
    gg_m = calendar.monthrange(anno_sel, m_idx_v)[1]
    data_list = []
    ultimo_notte = None 
    g_sett_lista = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]

    for d in range(1, gg_m + 1):
        dt = datetime(anno_sel, m_idx_v, d)
        tipo, desc = get_info_giorno(dt)
        wd_nome = g_sett_lista[dt.weekday()]
        
        disp_oggi = [m for m in st.session_state.medici if d not in st.session_state.assenze.get(m, [])]
        disp_notte = [m for m in disp_oggi if m != ultimo_notte]
        if not disp_notte: disp_notte = disp_oggi if disp_oggi else st.session_state.medici

        if tipo == "Festivo":
            m_mat_list = random.sample(disp_oggi, min(2, len(disp_oggi))) if div_f else [random.choice(disp_oggi)]
            mat_txt = " / ".join(m_mat_list)
            rest_p = [m for m in disp_oggi if m not in m_mat_list]
            pom_m = random.choice(rest_p) if rest_p else random.choice(disp_oggi)
            rest_n = [m for m in disp_notte if m != pom_m and m not in m_mat_list]
            not_m = random.choice(rest_n) if rest_n else random.choice(disp_notte)
            h_m, h_p, h_n = fes_m, fes_p, fes_n
        elif tipo == "Prefestivo":
            mat_txt, h_m = "---", "---"
            pom_m = random.choice(disp_oggi)
            rest_n = [m for m in disp_notte if m != pom_m]
            not_m = random.choice(rest_n) if rest_n else random.choice(disp_notte)
            h_p, h_n = p_p, p_n
        else:
            mat_txt, h_m = "---", "---"
            pom_m, h_p = "---", "---"
            not_m = random.choice(disp_notte)
            h_n = f_n

        ultimo_notte = not_m
        data_list.append({
            "Data": f"{d} {wd_nome}", 
            "Tipo": tipo, 
            "Descrizione": desc,
            "Mattina": mat_txt, 
            "Pomeriggio": pom_m, 
            "Notte": not_m,
            "H_M": h_m, 
            "H_P": h_p, 
            "H_N": h_n
        })
    st.session_state.db_turni = pd.DataFrame(data_list)

# --- 8. TABELLONE MAGNIFICO ---
if not st.session_state.db_turni.empty:
    st.markdown("### 📝 Vista Colorata")
    def style_row(row):
