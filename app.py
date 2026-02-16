import streamlit as st
import pandas as pd
import calendar
import json
import io
from datetime import datetime, timedelta

# --- 1. CONFIGURAZIONE E STILE ---
st.set_page_config(page_title="C.A. Porto Empedocle - Calvagna", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .main-title { color: #1e3a8a; font-weight: 800; text-align: center; margin-bottom: 20px; }
    .section-header { color: #2563eb; border-bottom: 2px solid #dbeafe; padding-bottom: 5px; margin: 15px 0; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGICA CALENDARIO E FESTIVITÀ ---
def get_festivita(anno):
    def calcola_pasqua(y):
        a, b, c = y % 19, y // 100, y % 100
        d, e = b // 4, b % 4
        f, g = (b + 8) // 25, (b - (b + 8) // 25 + 1) // 3
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

def is_festivo(dt, fest): return (dt.day, dt.month) in fest or dt.weekday() == 6
def is_prefestivo(dt, fest): return dt.weekday() == 5 or is_festivo(dt + timedelta(days=1), fest)

# --- 3. SESSION STATE ---
if 'medici' not in st.session_state: 
    st.session_state.medici = ["Piscopo", "Celani", "Lombardo", "Siracusa"]
if 'assenze' not in st.session_state: 
    st.session_state.assenze = {m: {} for m in st.session_state.medici}
if 'db_turni' not in st.session_state: 
    st.session_state.db_turni = pd.DataFrame()

# --- 4. SIDEBAR: GESTIONE E BACKUP ---
with st.sidebar:
    st.markdown("<div class='section-header'>⚙️ PARAMETRI</div>", unsafe_allow_html=True)
    anno_sel = st.number_input("Anno:", 2024, 2030, 2026)
    mesi_ita = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
    mese_nome = st.selectbox("Mese:", mesi_ita, index=2) # Default Marzo
    m_idx = mesi_ita.index(mese_nome) + 1
    
    st.markdown("<div class='section-header'>📅 INDISPONIBILITÀ (Solo Fest/Prefest)</div>", unsafe_allow_html=True)
    m_sel = st.selectbox("Medico:", st.session_state.medici)
    fest = get_festivita(anno_sel)
    
    # Visualizzazione giorni selezionabili per diurni
    cal_data = calendar.monthcalendar(anno_sel, m_idx)
    for week in cal_data:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day != 0:
                dt_c = datetime(anno_sel, m_idx, day)
                is_fp = is_festivo(dt_c, fest) or is_prefestivo(dt_c, fest)
                d_str = str(day)
                
                if is_fp:
                    curr = st.session_state.assenze[m_sel].get(d_str, [])
                    # Toggle semplice per indisponibilità totale del giorno festivo
                    if cols[i].button(f"{day}", key=f"d_{day}", type="primary" if curr else "secondary"):
                        st.session_state.assenze[m_sel][d_str] = ["M", "P", "N"] if not curr else []
                        st.rerun()
                else:
                    cols[i].write(f"~~{day}~~")

    st.markdown("<div class='section-header'>💾 BACKUP DATA</div>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Importa Backup (.json)", type="json")
    if uploaded_file:
        data = json.load(uploaded_file)
        st.session_state.assenze = data.get("assenze", {})
        st.success("Backup caricato!")

    backup_json = json.dumps({"assenze": st.session_state.assenze})
    st.download_button("Esporta Backup", backup_json, "backup_turni.json", use_container_width=True)

# --- 5. GENERAZIONE LOGICA CALVAGNA ---
st.markdown(f"<h1 class='main-title'>Gestione Turni Porto Empedocle - {mese_nome}</h1>", unsafe_allow_html=True)

if st.button("🚀 GENERA TURNI (Logica Documento)", type="primary", use_container_width=True):
    res = []
    ven_count = 0
    gg_m = calendar.monthrange(anno_sel, m_idx)[1]
    
    for d in range(1, gg_m + 1):
        dt = datetime(anno_sel, m_idx, d)
        wd = dt.weekday()
        d_str = str(d)
        tipo_g = fest.get((d, m_idx), "Domenica" if wd == 6 else ("Prefestivo" if is_prefestivo(dt, fest) else "Feriale"))
        is_fp = is_festivo(dt, fest) or is_prefestivo(dt, fest)
        
        m_m, p_m, n_m = "---", "---", "---"

        # Logica Notturna [cite: 7, 12]
        if wd == 0 or wd == 2: n_m = "Celani" [cite: 21, 27, 46, 52]
        elif wd == 1: n_m = "Piscopo" [cite: 24, 49, 74]
        elif wd == 3: n_m = "Lombardo" [cite: 30, 55, 80]
        elif wd == 4: # Venerdì alternati
            ven_count += 1
            n_m = "Piscopo" if ven_count % 2 == 0 else "Celani" [cite: 33, 58, 83, 108]
        elif wd == 5: n_m = "Siracusa" [cite: 38, 63, 88, 113]
        elif wd == 6: n_m = "Piscopo" [cite: 17, 43, 68, 93, 118]

        # Logica Diurna (Solo se Festivo/Prefestivo) [cite: 5, 6]
        if is_fp:
            m_m = "Siracusa" [cite: 15, 36, 41, 61, 66, 86, 91]
            p_m = "Siracusa" [cite: 16, 37, 42, 62, 67, 87, 92]
            
            # Applica indisponibilità (Sostituzione semplice)
            if "M" in st.session_state.assenze.get("Siracusa", {}).get(d_str, []):
                m_m = "Celani" if wd != 0 else "Piscopo"
            if "P" in st.session_state.assenze.get("Siracusa", {}).get(d_str, []):
                p_m = "Piscopo"

        h_m, h_p = ("08-14", "14-20") if is_festivo(dt, fest) else (("10-14", "14-20") if is_prefestivo(dt, fest) else ("---", "---"))

        res.append({
            "Data": f"{d} {['LUN','MAR','MER','GIO','VEN','SAB','DOM'][wd]}",
            "Tipo": tipo_g, "Mattina": m_m, "Pomeriggio": p_m, "Notte": n_m,
            "OreM": 6 if is_festivo(dt, fest) else (4 if is_prefestivo(dt, fest) else 0),
            "OreP": 6 if is_fp else 0, "OreN": 12, "H_M": h_m, "H_P": h_p
        })
    st.session_state.db_turni = pd.DataFrame(res)

# --- 6. TABELLA EDITABILE CON MENU A TENDINA ---
if not st.session_state.db_turni.empty:
    st.markdown("<div class='section-header'>📝 REVISIONE MANUALE</div>", unsafe_allow_html=True)
    
    # Configurazione colonne con menu a tendina
    lista_m = st.session_state.medici + ["---"]
    
    edited_df = st.data_editor(
        st.session_state.db_turni,
        column_order=("Data", "Tipo", "Mattina", "Pomeriggio", "Notte"),
        column_config={
            "Mattina": st.column_config.SelectboxColumn("Mattina (Diurna)", options=lista_m, required=True),
            "Pomeriggio": st.column_config.SelectboxColumn("Pomeriggio (Diurna)", options=lista_m, required=True),
            "Notte": st.column_config.SelectboxColumn("Notte (20-08)", options=lista_m, required=True),
            "Data": st.column_config.TextColumn(disabled=True),
            "Tipo": st.column_config.TextColumn(disabled=True),
        },
        use_container_width=True,
        hide_index=True
    )
    st.session_state.db_turni = edited_df

    # --- RIEPILOGO ORE ---
    st.markdown("<div class='section-header'>📊 RIEPILOGO ORE MENSILI</div>", unsafe_allow_html=True)
    stats = []
    for m in st.session_state.medici:
        o_m = edited_df[edited_df['Mattina'] == m]['OreM'].sum()
        o_p = edited_df[edited_df['Pomeriggio'] == m]['OreP'].sum()
        o_n = edited_df[edited_df['Notte'] == m]['OreN'].sum()
        stats.append({"Medico": m, "Ore Totali": o_m + o_p + o_n})
    
    st.table(pd.DataFrame(stats))
