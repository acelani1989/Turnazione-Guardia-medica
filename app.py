import streamlit as st
import pandas as pd
import calendar
import random
import io
import json
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm

# --- 1. CONFIGURAZIONE GRAFICA MIRATA ---
st.set_page_config(page_title="Gestione Turni Medica", layout="wide")

st.markdown("""
    <style>
    /* Sfondo globale bianco per chiarezza */
    .stApp { background-color: #FFFFFF; }
    
    /* Sidebar: Sfondo Blu Scuro */
    [data-testid="stSidebar"] { 
        background-color: #001f3f !important; 
    }
    
    /* Titoli Sidebar in Giallo */
    .sidebar-header { 
        color: #FFD700 !important; 
        font-weight: 900; 
        font-size: 1.2rem !important;
        border-bottom: 2px solid #FFD700;
        margin-bottom: 15px;
        padding-top: 10px;
    }

    /* FIX: Testo nei menu a tendina (Mese) e Input (Anno) deve essere NERO */
    div[data-baseweb="select"] *, div[data-baseweb="input"] * {
        color: #000000 !important;
    }
    
    /* Testo etichette nella sidebar in BIANCO */
    [data-testid="stSidebar"] label p {
        color: #FFFFFF !important;
        font-weight: bold;
    }

    /* Calendario Sidebar: bottoni visibili */
    div[st-vertical-block] button {
        border: 1px solid #ffffff !important;
        background-color: #1a365d !important;
        color: #ffffff !important;
    }

    /* Area principale: contrasto alto */
    h1, h2, h3, .stMarkdown p { color: #000000 !important; }
    
    .settings-section { 
        background-color: #f1f5f9; 
        padding: 15px; 
        border-radius: 10px; 
        border: 2px solid #cbd5e1; 
    }
    </style>
    """, unsafe_allow_html=True)

# Immagine Studio Medico
st.image("https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?auto=format&fit=crop&q=80&w=1500&h=300", use_container_width=True)

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
    try: dt_pp = dt_p.replace(day=g_p+1)
    except: dt_pp = datetime(anno, m_p+1, 1)
    return {(1, 1): "Capodanno", (6, 1): "Epifania", (25, 4): "Liberazione", (1, 5): "Festa Lavoro", 
            (2, 6): "Festa Repubblica", (15, 8): "Ferragosto", (1, 11): "Ognissanti", 
            (8, 12): "Immacolata", (25, 12): "Natale", (26, 12): "S. Stefano",
            (dt_p.day, dt_p.month): "Pasqua", (dt_pp.day, dt_pp.month): "Pasquetta"}

def calcola_durata(intervallo):
    try:
        if "---" in str(intervallo) or not intervallo: return 0
        parti = intervallo.split("-")
        inizio = datetime.strptime(parti[0].strip(), "%H:%M")
        fine = datetime.strptime(parti[1].strip(), "%H:%M")
        durata = (fine - inizio).seconds / 3600
        return durata if durata > 0 else durata + 24
    except: return 0

# --- 3. SESSION STATE ---
if 'medici' not in st.session_state: st.session_state.medici = ["Piscopo", "Celani", "Lombardo", "Siracusa"]
if 'assenze' not in st.session_state: st.session_state.assenze = {m: [] for m in st.session_state.medici}
if 'db_turni' not in st.session_state: st.session_state.db_turni = pd.DataFrame()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown("<div class='sidebar-header'>📅 CONFIGURAZIONE</div>", unsafe_allow_html=True)
    anno_sel = st.number_input("Seleziona Anno", 2024, 2030, 2026)
    mesi_ita = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
    mese_nome = st.selectbox("Seleziona Mese", mesi_ita, index=1)
    m_idx_v = mesi_ita.index(mese_nome) + 1
    
    st.markdown("<div class='sidebar-header'>👨‍⚕️ STAFF</div>", unsafe_allow_html=True)
    nuovo_m = st.text_input("Aggiungi Medico:")
    if st.button("➕ AGGIUNGI"):
        if nuovo_m and nuovo_m not in st.session_state.medici:
            st.session_state.medici.append(nuovo_m)
            st.session_state.assenze[nuovo_m] = []
            st.rerun()
    
    for med in st.session_state.medici:
        c_n, c_d = st.columns([4, 1])
        c_n.markdown(f"**{med}**")
        if c_d.button("X", key=f"del_{med}"):
            st.session_state.medici.remove(med)
            st.rerun()

    st.markdown("<div class='sidebar-header'>🚫 ASSENZE</div>", unsafe_allow_html=True)
    m_sel = st.selectbox("Medico per assenze", st.session_state.medici)
    
    g_short = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
    cols_sh = st.columns(7)
    cal_data = calendar.monthcalendar(anno_sel, m_idx_v)
    for i, label in enumerate(g_short):
        if cols_sh[i].button(label, key=f"sh_{label}"):
            giorni = [sett[i] for sett in cal_data if sett[i] != 0]
            current = st.session_state.assenze.get(m_sel, [])
            st.session_state.assenze[m_sel] = [d for d in current if d not in giorni] if all(d in current for d in giorni) else list(set(current + giorni))
            st.rerun()

    for week in cal_data:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day != 0:
                is_abs = day in st.session_state.assenze.get(m_sel, [])
                if cols[i].button(str(day), key=f"d_{day}", type="primary" if is_abs else "secondary"):
                    if is_abs: st.session_state.assenze[m_sel].remove(day)
                    else: st.session_state.assenze[m_sel].append(day)
                    st.rerun()

    st.markdown("<div class='sidebar-header'>💾 BACKUP</div>", unsafe_allow_html=True)
    st.download_button("📥 SCARICA BACKUP", json.dumps({"medici": st.session_state.medici, "assenze": st.session_state.assenze}), "backup.json", use_container_width=True)
    up = st.file_uploader("📤 CARICA BACKUP", type="json")
    if up:
        d = json.load(up)
        st.session_state.medici, st.session_state.assenze = d["medici"], d["assenze"]
        st.rerun()

# --- 5. INTERFACCIA PRINCIPALE ---
st.markdown(f"<h1>Turni Studio Medico: {mese_nome} {anno_sel}</h1>", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("<div class='settings-section'><b>🏠 FERIALI</b>", unsafe_allow_html=True)
    f_n = st.text_input("Notte", "20:00 - 08:00")
with col2:
    st.markdown("<div class='settings-section'><b>🕒 PREFESTIVI</b>", unsafe_allow_html=True)
    p_p = st.text_input("Pomeriggio", "10:00 - 20:00")
    p_n = st.text_input("Notte", "20:00 - 08:00", key="pn_m")
with col3:
    st.markdown("<div class='settings-section'><b>🚩 FESTIVI</b>", unsafe_allow_html=True)
    fes_m = st.text_input("Mattina", "08:00 - 14:00")
    fes_p = st.text_input("Pomeriggio", "14:00 - 20:00")
    fes_n = st.text_input("Notte", "20:00 - 08:00", key="fn_m")

st.divider()
if st.button("🚀 GENERA CALENDARIO", type="primary", use_container_width=True):
    fest = get_festivita(anno_sel)
    gg_m = calendar.monthrange(anno_sel, m_idx_v)[1]
    res = []
    u_n = None
    for d in range(1, gg_m + 1):
        dt = datetime(anno_sel, m_idx_v, d)
        wd = dt.weekday()
        tipo = "Festivo" if (wd == 6 or (d, m_idx_v) in fest) else ("Prefestivo" if wd == 5 else "Feriale")
        disp = [m for m in st.session_state.medici if d not in st.session_state.assenze.get(m, [])]
        if not disp: disp = st.session_state.medici
        cand = [m for m in disp if m != u_n] or disp
        m_m, p_m, n_m = "---", "---", "---"
        h_m, h_p, h_n = "---", "---", "---"
        if tipo == "Festivo":
            m_m = random.choice(cand); h_m = fes_m
            p_m = random.choice([m for m in disp if m != m_m] or disp); h_p = fes_p
            n_m = random.choice([m for m in cand if m != p_m] or cand); h_n = fes_n
        elif tipo == "Prefestivo":
            p_m = random.choice(cand); h_p = p_p
            n_m = random.choice([m for m in cand if m != p_m] or cand); h_n = p_n
        else:
            n_m = random.choice(cand); h_n = f_n
        u_n = n_m
        res.append({"Data": f"{d} {g_short[wd]}", "Tipo": tipo, "Mattina": m_m, "Pomeriggio": p_m, "Notte": n_m, "H_M": h_m, "H_P": h_p, "H_N": h_n})
    st.session_state.db_turni = pd.DataFrame(res)

if not st.session_state.db_turni.empty:
    tab1, tab2 = st.tabs(["📝 MODIFICA & ORE", "👁️ PDF"])
    with tab1:
        st.session_state.db_turni = st.data_editor(st.session_state.db_turni, use_container_width=True, hide_index=True)
        ore = {m: 0.0 for m in st.session_state.medici}
        for _, r in st.session_state.db_turni.iterrows():
            d1, d2, d3 = calcola_durata(r["H_M"]), calcola_durata(r["H_P"]), calcola_durata(r["H_N"])
            for m, h in [(r["Mattina"], d1), (r["Pomeriggio"], d2), (r["Notte"], d3)]:
                if m in ore: ore[m] += h
        st.write("### 📊 Riepilogo Ore")
        st.table(pd.DataFrame([{"Medico": m, "Ore": int(h)} for m, h in ore.items()]))
    with tab2:
        st.dataframe(st.session_state.db_turni[["Data", "Mattina", "Pomeriggio", "Notte"]], use_container_width=True)
        def make_pdf():
            buf = io.BytesIO()
            doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=0.5*cm, bottomMargin=0.5*cm)
            elements = [Paragraph(f"TURNI {mese_nome.upper()} {anno_sel}", getSampleStyleSheet()['Title'])]
            data = [["GIORNO", "MATTINA", "POMERIGGIO", "NOTTE"]]
            styles = [('GRID', (0,0), (-1,-1), 0.5, colors.black), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('BACKGROUND', (0,0), (-1,0), colors.cadetblue)]
            for i, r in enumerate(st.session_state.db_turni.to_dict('records')):
                data.append([r["Data"], r["Mattina"], r["Pomeriggio"], r["Notte"]])
                if r["Tipo"] == "Festivo": styles.append(('BACKGROUND', (0, i+1), (-1, i+1), colors.lightpink))
            t = Table(data, colWidths=[3*cm, 5*cm, 5*cm, 5*cm])
            t.setStyle(TableStyle(styles))
            elements.append(t)
            doc.build(elements)
            return buf.getvalue()
        st.download_button("📥 SCARICA PDF", make_pdf(), f"Turni_{mese_nome}.pdf", "application/pdf", type="primary", use_container_width=True)
