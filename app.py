import streamlit as st
import pandas as pd
import calendar
import random
import io
import json
from datetime import datetime, timedelta
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm

# --- 1. CONFIGURAZIONE E DESIGN ---
st.set_page_config(page_title="Master Guardia Medica Pro", layout="wide")

st.markdown("""
    <style>
    .stApp {
        background-image: linear-gradient(rgba(255, 255, 255, 0.85), rgba(255, 255, 255, 0.85)), 
        url("https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?ixlib=rb-4.0.3&auto=format&fit=crop&w=1600&q=80");
        background-size: cover;
        background-attachment: fixed;
    }
    .main-title { color: #2c5282; font-weight: 800; font-size: 2.2rem; text-align: center; margin-bottom: 15px; }
    .settings-section { background-color: rgba(255, 255, 255, 0.95); padding: 12px; border-radius: 10px; border-left: 5px solid #4299e1; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 10px; }
    .sidebar-header { color: #2b6cb0; font-weight: 700; border-bottom: 2px solid #bee3f8; padding-bottom: 5px; margin-bottom: 10px; }
    div[data-baseweb="select"] *, div[data-baseweb="input"] * { color: #000000 !important; font-weight: bold; }
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
    
    return {
        (1, 1): "Capodanno", (6, 1): "Epifania", (25, 4): "Liberazione", (1, 5): "Festa Lavoro", 
        (2, 6): "Festa Repubblica", (15, 8): "Ferragosto", (1, 11): "Ognissanti", 
        (8, 12): "Immacolata", (25, 12): "Natale", (26, 12): "S. Stefano",
        (dt_p.day, dt_p.month): "Pasqua", (dt_pp.day, dt_pp.month): "Pasquetta", (25, 2): "S. Patrono"
    }

def is_festivo(dt, fest):
    return dt.weekday() == 6 or (dt.day, dt.month) in fest

def is_prefestivo(dt, fest):
    if dt.weekday() == 5: return True
    domani = dt + timedelta(days=1)
    return is_festivo(domani, fest)

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
# Inizializzazione sicura delle assenze come dizionario di dizionari
if 'assenze' not in st.session_state or not isinstance(st.session_state.assenze, dict):
    st.session_state.assenze = {m: {} for m in st.session_state.medici}

# Controllo integrità per ogni medico (trasforma liste vecchie in dizionari se necessario)
for m in st.session_state.medici:
    if m not in st.session_state.assenze or not isinstance(st.session_state.assenze[m], dict):
        st.session_state.assenze[m] = {}

if 'db_turni' not in st.session_state: st.session_state.db_turni = pd.DataFrame()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown("<div class='sidebar-header'>⚕️ GESTIONE</div>", unsafe_allow_html=True)
    anno_sel = st.number_input("Anno:", 2024, 2030, 2026)
    mesi_ita = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
    mese_nome = st.selectbox("Mese:", mesi_ita, index=0)
    m_idx_v = mesi_ita.index(mese_nome) + 1
    
    st.divider()
    st.markdown("<div class='sidebar-header'>📅 ASSENZE DETTAGLIATE</div>", unsafe_allow_html=True)
    m_sel = st.selectbox("Medico:", st.session_state.medici)
    fascia = st.radio("Assenza per:", ["Tutto il giorno", "Mattina", "Pomeriggio", "Notte"], horizontal=True)
    map_fascia = {"Tutto il giorno": ["M", "P", "N"], "Mattina": ["M"], "Pomeriggio": ["P"], "Notte": ["N"]}

    # Scorciatoie giorni (LUN, MAR...)
    g_short = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
    cal_data = calendar.monthcalendar(anno_sel, m_idx_v)
    cols_sh = st.columns(7)
    for i, label in enumerate(g_short):
        if cols_sh[i].button(label, key=f"sh_{label}"):
            days_to_toggle = [sett[i] for sett in cal_data if sett[i] != 0]
            for d in days_to_toggle:
                current = st.session_state.assenze[m_sel].get(d, [])
                if all(f in current for f in map_fascia[fascia]):
                    st.session_state.assenze[m_sel][d] = [f for f in current if f not in map_fascia[fascia]]
                else:
                    st.session_state.assenze[m_sel][d] = list(set(current + map_fascia[fascia]))
            st.rerun()

    # Griglia Calendario
    for week in cal_data:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day != 0:
                current_abs = st.session_state.assenze[m_sel].get(day, [])
                # Mostra le iniziali delle assenze sul bottone
                label = f"{day}\n{''.join(current_abs)}" if current_abs else f"{day}"
                if cols[i].button(label, key=f"btn_{m_sel}_{day}", type="primary" if current_abs else "secondary"):
                    if all(f in current_abs for f in map_fascia[fascia]):
                        st.session_state.assenze[m_sel][day] = [f for f in current_abs if f not in map_fascia[fascia]]
                    else:
                        st.session_state.assenze[m_sel][day] = list(set(current_abs + map_fascia[fascia]))
                    st.rerun()

    st.divider()
    st.download_button("📥 Scarica Backup", json.dumps({"medici": st.session_state.medici, "assenze": st.session_state.assenze}), f"backup_{mese_nome}.json", use_container_width=True)

# --- 5. INTERFACCIA PRINCIPALE ---
st.markdown(f"<div class='main-title'>C.A PORTO EMPEDOCLE: {mese_nome} {anno_sel}</div>", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("<div class='settings-section'><b>🏠 FERIALI</b>", unsafe_allow_html=True)
    f_n_h = st.text_input("Notte", "20:00 - 08:00", key="f_n_main")
with c2:
    st.markdown("<div class='settings-section'><b>🕒 PREFESTIVI</b>", unsafe_allow_html=True)
    p_m_h = st.text_input("Mattina (10-14)", "10:00 - 14:00", key="p_m_main")
    p_p_h = st.text_input("Pomeriggio (14-20)", "14:00 - 20:00", key="p_p_main")
    p_n_h = st.text_input("Notte", "20:00 - 08:00", key="p_n_main")
with c3:
    st.markdown("<div class='settings-section'><b>🚩 FESTIVI</b>", unsafe_allow_html=True)
    f_m_h = st.text_input("Mattina (08-14)", "08:00 - 14:00", key="f_m_main")
    f_p_h = st.text_input("Pomeriggio (14-20)", "14:00 - 20:00", key="f_p_main")
    f_n_h_fest = st.text_input("Notte", "20:00 - 08:00", key="f_n_fest_main")

if st.button("🚀 GENERA TURNI", type="primary", use_container_width=True):
    fest = get_festivita(anno_sel)
    gg_m = calendar.monthrange(anno_sel, m_idx_v)[1]
    res = []
    u_n = None 
    
    for d in range(1, gg_m + 1):
        dt = datetime(anno_sel, m_idx_v, d)
        nome_f = fest.get((d, m_idx_v), "")
        tipo = "Festivo" if is_festivo(dt, fest) else ("Prefestivo" if is_prefestivo(dt, fest) else "Feriale")
        
        # Filtro disponibilità fasce
        disp_m = [m for m in st.session_state.medici if "M" not in st.session_state.assenze[m].get(d, [])]
        disp_p = [m for m in st.session_state.medici if "P" not in st.session_state.assenze[m].get(d, [])]
        disp_n = [m for m in st.session_state.medici if "N" not in st.session_state.assenze[m].get(d, [])]

        # Logica Notte (evita consecutive)
        cand_n = [m for m in disp_n if m != u_n] or disp_n
        n_m = random.choice(cand_n)
        u_n = n_m
        
        m_m, p_m_v, h_m, h_p, h_n = "---", "---", "---", "---", "---"
        
        if tipo in ["Festivo", "Prefestivo"]:
            h_m = f_m_h if tipo == "Festivo" else p_m_h
            h_p = f_p_h if tipo == "Festivo" else p_p_h
            h_n = f_n_h_fest if tipo == "Festivo" else p_n_h
            # Assegnazione diurna evitando sovrapposizione con chi fa la notte lo stesso giorno
            m_m = random.choice([m for m in disp_m if m != n_m] or disp_m)
            p_m_v = random.choice([m for m in disp_p if m not in [n_m, m_m]] or disp_p)
        else:
            h_n = f_n_h

        res.append({
            "Data": f"{d} {g_short[dt.weekday()]}", 
            "Info": nome_f, "Tipo": tipo, 
            "Mattina": m_m, "Pomeriggio": p_m_v, "Notte": n_m, 
            "H_M": h_m, "H_P": h_p, "H_N": h_n
        })
    
    st.session_state.db_turni = pd.DataFrame(res)

# --- 6. RIEPILOGO E PDF ---
if not st.session_state.db_turni.empty:
    st.session_state.db_turni = st.data_editor(st.session_state.db_turni, use_container_width=True, hide_index=True)

    def genera_pdf():
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=0.5*cm, bottomMargin=0.5*cm, leftMargin=0.5*cm, rightMargin=0.5*cm)
        elements = [Paragraph(f"<b>C.A PORTO EMPEDOCLE - {mese_nome.upper()} {anno_sel}</b>", getSampleStyleSheet()['Title']), Spacer(1, 10)]
        
        data = [["DATA", "TIPO", "MATTINA", "POMERIGGIO", "NOTTE"]]
        t_styles = [('GRID', (0,0), (-1,-1), 0.5, colors.black), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('FONTSIZE', (0,0), (-1,-1), 7), ('BACKGROUND', (0,0), (-1,0), colors.cadetblue), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke)]
        
        for i, r in enumerate(st.session_state.db_turni.to_dict('records')):
            idx = i + 1
            data.append([r['Data'], r["Tipo"], f"{r['Mattina']}\n{r['H_M']}", f"{r['Pomeriggio']}\n{r['H_P']}", f"{r['Notte']}\n{r['H_N']}"])
            if r["Tipo"] == "Festivo": t_styles.append(('BACKGROUND', (0, idx), (-1, idx), colors.lightpink))
            elif r["Tipo"] == "Prefestivo": t_styles.append(('BACKGROUND', (0, idx), (-1, idx), colors.lightyellow))
        
        table = Table(data, colWidths=[2.8*cm, 2.2*cm, 4.8*cm, 4.8*cm, 4.8*cm])
        table.setStyle(TableStyle(t_styles))
        elements.append(table)
        doc.build(elements)
        return buf.getvalue()

    st.download_button("📥 SCARICA PDF", genera_pdf(), f"Turni_{mese_nome}.pdf", "application/pdf", use_container_width=True, type="primary")
