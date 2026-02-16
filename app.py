import streamlit as st
import pandas as pd
import calendar
import random
import io
import json
from datetime import datetime, timedelta

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="C.A. Porto Empedocle - Pro", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f7fafc; }
    .main-title { color: #2c5282; font-weight: 800; font-size: 2.2rem; text-align: center; margin-bottom: 20px; }
    .sidebar-header { color: #2b6cb0; font-weight: 700; border-bottom: 2px solid #bee3f8; padding-bottom: 5px; margin-bottom: 15px; }
    .alert-box { padding: 10px; background-color: #fff3cd; border-left: 5px solid #ffca28; color: #856404; border-radius: 5px; margin-bottom: 10px; }
    .total-box { padding: 15px; background-color: #e2e8f0; border-radius: 10px; text-align: center; font-weight: bold; font-size: 1.1rem; color: #2d3748; margin-top: 10px; border: 1px solid #cbd5e0; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNZIONI LOGICHE ---
def get_festivita(anno):
    def calcola_pasqua(y):
        a, b, c = y % 19, y // 100, y % 100
        d, e = b // 4, b % 4
        f = (b + 8) // 25
        g = (b - f + 1) // 3
        h = (19 * a + b - d - g + 15) % 30
        i, k = c // 4, c % 4
        l = (32 + 2 * e + 2 * i - h - k) % 7
        m = (a + 11 * h + 22 * l) // 451
        mese = (h + l - 7 * m + 114) // 31
        giorno = ((h + l - 7 * m + 114) % 31) + 1
        return giorno, mese
    g_p, m_p = calcola_pasqua(anno)
    dt_p = datetime(anno, m_p, g_p)
    dt_pp = dt_p + timedelta(days=1)
    return {(1, 1): "Capodanno", (6, 1): "Epifania", (25, 4): "Liberazione", (1, 5): "Festa Lavoro", 
            (2, 6): "Festa Repubblica", (15, 8): "Ferragosto", (1, 11): "Ognissanti", 
            (8, 12): "Immacolata", (25, 12): "Natale", (26, 12): "S. Stefano",
            (dt_p.day, dt_p.month): "Pasqua", (dt_pp.day, dt_pp.month): "Pasquetta", (25, 2): "S. Patrono"}

def is_festivo(dt, fest): 
    return (dt.day, dt.month) in fest or dt.weekday() == 6

def is_prefestivo(dt, fest): 
    return dt.weekday() == 5 or is_festivo(dt + timedelta(days=1), fest)

# --- 3. SESSION STATE ---
if 'medici' not in st.session_state: st.session_state.medici = ["Piscopo", "Celani", "Lombardo", "Siracusa"]
if 'assenze' not in st.session_state: st.session_state.assenze = {m: {} for m in st.session_state.medici}
if 'db_turni' not in st.session_state: st.session_state.db_turni = pd.DataFrame()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown("<div class='sidebar-header'>⚕️ IMPOSTAZIONI</div>", unsafe_allow_html=True)
    anno_sel = st.number_input("Anno:", 2024, 2030, 2026)
    mesi_ita = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
    mese_nome = st.selectbox("Mese:", mesi_ita)
    m_idx_v = mesi_ita.index(mese_nome) + 1
    
    st.divider()
    st.markdown("<div class='sidebar-header'>📅 INDISPONIBILITÀ</div>", unsafe_allow_html=True)
    m_sel = st.selectbox("Seleziona Medico:", st.session_state.medici)
    cal_data = calendar.monthcalendar(anno_sel, m_idx_v)
    
    # Visualizzazione Calendario Manuale
    for week in cal_data:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day != 0:
                d_str = str(day)
                curr_abs = st.session_state.assenze[m_sel].get(d_str, [])
                label = f"{day}\n{''.join(curr_abs)}" if curr_abs else f"{day}"
                if cols[i].button(label, key=f"btn_{day}", type="primary" if curr_abs else "secondary"):
                    st.session_state.assenze[m_sel][d_str] = ["M", "P", "N"] if not curr_abs else []
                    st.rerun()

    st.divider()
    # GESTIONE BACKUP
    st.markdown("<div class='sidebar-header'>💾 BACKUP E DATI</div>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Carica Backup (.json)", type="json")
    if uploaded_file:
        data_loaded = json.load(uploaded_file)
        st.session_state.assenze = data_loaded.get("assenze", {})
        st.success("Dati caricati correttamente!")

    backup_obj = {"assenze": st.session_state.assenze}
    st.download_button("💾 SCARICA BACKUP", json.dumps(backup_obj), f"backup_turni.json", use_container_width=True)

# --- 5. LOGICA GENERAZIONE ---
st.markdown(f"<div class='main-title'>C.A. Porto Empedocle - {mese_nome} {anno_sel}</div>", unsafe_allow_html=True)

if st.button("🚀 GENERA TURNI", type="primary", use_container_width=True):
    fest = get_festivita(anno_sel)
    gg_m = calendar.monthrange(anno_sel, m_idx_v)[1]
    res = []
    
    for d in range(1, gg_m + 1):
        dt = datetime(anno_sel, m_idx_v, d)
        wd = dt.weekday()
        d_str = str(d)
        
        # [cite_start]Identificazione tipo giorno [cite: 4, 5, 6]
        nome_fest = fest.get((dt.day, dt.month))
        tipo_label = "Festivo" if (nome_fest or wd == 6) else ("Prefestivo" if is_prefestivo(dt, fest) else "Feriale")
        
        # [cite_start]Orari standard basati sull'allegato [cite: 8, 9, 10, 11, 12]
        h_m, h_p, h_n = "---", "---", "20-08"
        o_m, o_p, o_n = 0, 0, 12
        
        if tipo_label == "Festivo": 
            h_m, h_p = "08-14", "14-20"
            o_m, o_p = 6, 6
        elif tipo_label == "Prefestivo": 
            h_m, h_p = "10-14", "14-20"
            o_m, o_p = 4, 6

        # Assegnazione di base (modificabile poi dal menu a tendina)
        res.append({
            "Data": f"{d} {['LUN','MAR','MER','GIO','VEN','SAB','DOM'][wd]}", 
            "Tipo": nome_fest if nome_fest else tipo_label,
            "Mattina": "---" if o_m == 0 else "Siracusa",
            "Pomeriggio": "---" if o_p == 0 else "Siracusa",
            "Notte": "Celani" if wd in [0, 2, 4] else "Piscopo",
            "OreM": o_m, "OreP": o_p, "OreN": o_n, "H_M": h_m, "H_P": h_p
        })
    st.session_state.db_turni = pd.DataFrame(res)

# --- 6. VISUALIZZAZIONE E EDITING (Menu a Tendina) ---
if not st.session_state.db_turni.empty:
    st.subheader("📅 Turni (Modificabili con Selezione Medico)")
    lista_medici = st.session_state.medici + ["---"]
    
    edited_df = st.data_editor(
        st.session_state.db_turni,
        column_order=("Data", "Tipo", "Mattina", "Pomeriggio", "Notte"),
        column_config={
            "Mattina": st.column_config.SelectboxColumn("Mattina", options=lista_medici),
            "Pomeriggio": st.column_config.SelectboxColumn("Pomeriggio", options=lista_medici),
            "Notte": st.column_config.SelectboxColumn("Notte", options=lista_medici),
            "Data": st.column_config.TextColumn(disabled=True),
            "Tipo": st.column_config.TextColumn(disabled=True),
        },
        use_container_width=True, hide_index=True
    )
    st.session_state.db_turni = edited_df

    # RIEPILOGO ORE
    st.markdown("<div class='sidebar-header'>📊 RIEPILOGO ORE</div>", unsafe_allow_html=True)
    stats = []
    for m in st.session_state.medici:
        t = edited_df[edited_df['Mattina'] == m]['OreM'].sum() + \
            edited_df[edited_df['Pomeriggio'] == m]['OreP'].sum() + \
            edited_df[edited_df['Notte'] == m]['OreN'].sum()
        stats.append({"Medico": m, "Ore Totali": t})
    st.table(pd.DataFrame(stats))
