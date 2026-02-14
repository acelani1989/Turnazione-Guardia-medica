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
if 'assenze' not in st.session_state: st.session_state.assenze = {m: [] for m in st.session_state.medici}
if 'db_turni' not in st.session_state: st.session_state.db_turni = pd.DataFrame()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown("<div class='sidebar-header'>⚕️ GESTIONE</div>", unsafe_allow_html=True)
    anno_sel = st.number_input("Anno:", 2024, 2030, 2026)
    mesi_ita = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
    mese_nome = st.selectbox("Mese:", mesi_ita, index=0)
    m_idx_v = mesi_ita.index(mese_nome) + 1
    soglia_ore = st.slider("Soglia Alert Ore:", 100, 250, 160)
    
    st.divider()
    st.markdown("<div class='sidebar-header'>👨‍⚕️ STAFF</div>", unsafe_allow_html=True)
    nuovo_m = st.text_input("Aggiungi Medico:")
    if st.button("➕ AGGIUNGI"):
        if nuovo_m and nuovo_m not in st.session_state.medici:
            st.session_state.medici.append(nuovo_m); st.session_state.assenze[nuovo_m] = []; st.rerun()
    
    for med in st.session_state.medici:
        c_n, c_d = st.columns([4, 1])
        c_n.write(f"**{med}**")
        if c_d.button("🗑️", key=f"del_{med}"):
            st.session_state.medici.remove(med); st.rerun()

    st.divider()
    st.markdown("<div class='sidebar-header'>📅 ASSENZE</div>", unsafe_allow_html=True)
    m_sel = st.selectbox("Seleziona Medico:", st.session_state.medici)
    
    # Scorciatoie giorni della settimana
    g_short = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
    cal_data = calendar.monthcalendar(anno_sel, m_idx_v)
    cols_sh = st.columns(7)
    for i, label in enumerate(g_short):
        if cols_sh[i].button(label, key=f"sh_{label}"):
            g_da_c = [sett[i] for sett in cal_data if sett[i] != 0]
            curr = st.session_state.assenze.get(m_sel, [])
            if all(d in curr for d in g_da_c):
                st.session_state.assenze[m_sel] = [d for d in curr if d not in g_da_c]
            else:
                st.session_state.assenze[m_sel] = list(set(curr + g_da_c))
            st.rerun()

    # Griglia calendario
    for week in cal_data:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day != 0:
                is_abs = day in st.session_state.assenze.get(m_sel, [])
                if cols[i].button(str(day), key=f"d_{day}", type="primary" if is_abs else "secondary"):
                    if is_abs: st.session_state.assenze[m_sel].remove(day)
                    else: st.session_state.assenze[m_sel].append(day)
                    st.rerun()

    st.divider()
    st.download_button("📥 Scarica Backup", json.dumps({"medici": st.session_state.medici, "assenze": st.session_state.assenze}), f"backup_{mese_nome}.json", use_container_width=True)
    up = st.file_uploader("📤 Carica Backup", type="json")
    if up:
        data = json.load(up); st.session_state.medici, st.session_state.assenze = data["medici"], data["assenze"]; st.rerun()

# --- 5. INTERFACCIA PRINCIPALE ---
st.markdown(f"<div class='main-title'>Gestione Turni: {mese_nome} {anno_sel}</div>", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("<div class='settings-section'><b>🏠 FERIALI</b>", unsafe_allow_html=True)
    f_n_h = st.text_input("Notte", "20:00 - 08:00", key="f_n_in")
with c2:
    st.markdown("<div class='settings-section'><b>🕒 PREFESTIVI</b>", unsafe_allow_html=True)
    p_m_h = st.text_input("Mattina (10-14)", "10:00 - 14:00", key="p_m_in")
    p_p_h = st.text_input("Pomeriggio (14-20)", "14:00 - 20:00", key="p_p_in")
    p_n_h = st.text_input("Notte", "20:00 - 08:00", key="p_n_in")
with c3:
    st.markdown("<div class='settings-section'><b>🚩 FESTIVI</b>", unsafe_allow_html=True)
    fes_m_h = st.text_input("Mattina (08-14)", "08:00 - 14:00", key="f_m_in")
    fes_p_h = st.text_input("Pomeriggio (14-20)", "14:00 - 20:00", key="f_p_in")
    fes_n_h = st.text_input("Notte", "20:00 - 08:00", key="f_n_in_fest")

if st.button("🚀 GENERA / RIGENERA TURNI", type="primary", use_container_width=True):
    fest = get_festivita(anno_sel)
    gg_m = calendar.monthrange(anno_sel, m_idx_v)[1]
    res = []
    u_n = None 
    
    for d in range(1, gg_m + 1):
        dt = datetime(anno_sel, m_idx_v, d)
        nome_f = fest.get((d, m_idx_v), "")
        tipo = "Festivo" if is_festivo(dt, fest) else ("Prefestivo" if is_prefestivo(dt, fest) else "Feriale")
        
        disp = [m for m in st.session_state.medici if d not in st.session_state.assenze.get(m, [])]
        if not disp: disp = st.session_state.medici
        
        cand_notte = [m for m in disp if m != u_n] or disp
        m_m, p_m_v, n_m, h_m, h_p, h_n = "---", "---", "---", "---", "---", "---"
        
        if tipo == "Festivo":
            m_m = random.choice(disp)
            p_m_v = random.choice([m for m in disp if m != m_m] or disp)
            n_m = random.choice([m for m in cand_notte if m not in [m_m, p_m_v]] or cand_notte)
            h_m, h_p, h_n = fes_m_h, fes_p_h, fes_n_h
        elif tipo == "Prefestivo":
            m_m = random.choice(disp)
            p_m_v = random.choice([m for m in disp if m != m_m] or disp)
            n_m = random.choice([m for m in cand_notte if m not in [m_m, p_m_v]] or cand_notte)
            h_m, h_p, h_n = p_m_h, p_p_h, p_n_h
        else:
            n_m = random.choice(cand_notte)
            h_n = f_n_h
            
        u_n = n_m
        res.append({"Data": f"{d} {g_short[dt.weekday()]}", "Info": nome_f, "Tipo": tipo, "Mattina": m_m, "Pomeriggio": p_m_v, "Notte": n_m, "H_M": h_m, "H_P": h_p, "H_N": h_n})
    
    st.session_state.db_turni = pd.DataFrame(res)

# --- 6. RIEPILOGO E PDF ---
if not st.session_state.db_turni.empty:
    # Calcolo ore per alert
    ore_m = {m: 0.0 for m in st.session_state.medici}
    for _, r in st.session_state.db_turni.iterrows():
        if r["Mattina"] in ore_m: ore_m[r["Mattina"]] += calcola_durata(r["H_M"])
        if r["Pomeriggio"] in ore_m: ore_m[r["Pomeriggio"]] += calcola_durata(r["H_P"])
        if r["Notte"] in ore_m: ore_m[r["Notte"]] += calcola_durata(r["H_N"])

    # Sezione Alert
    for med, ore in ore_m.items():
        if ore > soglia_ore: st.error(f"❌ {med} ha superato le {soglia_ore}h ({int(ore)}h)")

    # Editor Tabella
    st.session_state.db_turni = st.data_editor(st.session_state.db_turni, column_config={
        "Mattina": st.column_config.SelectboxColumn(options=["---"] + st.session_state.medici),
        "Pomeriggio": st.column_config.SelectboxColumn(options=["---"] + st.session_state.medici),
        "Notte": st.column_config.SelectboxColumn(options=["---"] + st.session_state.medici),
    }, use_container_width=True, hide_index=True)

    def genera_pdf():
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=0.5*cm, bottomMargin=0.5*cm, leftMargin=0.5*cm, rightMargin=0.5*cm)
        elements = []
        styles = getSampleStyleSheet()
        elements.append(Paragraph(f"<b>C.A PORTO EMPEDOCLE - {mese_nome.upper()} {anno_sel}</b>", styles['Title']))
        elements.append(Spacer(1, 10))
        
        data = [["DATA", "TIPO", "MATTINA", "POMERIGGIO", "NOTTE"]]
        t_styles = [('GRID', (0,0), (-1,-1), 0.5, colors.black), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('FONTSIZE', (0,0), (-1,-1), 7), ('BACKGROUND', (0,0), (-1,0), colors.cadetblue), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke)]
        
        for i, r in enumerate(st.session_state.db_turni.to_dict('records')):
            idx = i + 1
            f_txt = f" ({r['Info']})" if r['Info'] else ""
            data.append([f"{r['Data']}{f_txt}", r["Tipo"], f"{r['Mattina']}\n{r['H_M']}" if r['Mattina']!="---" else "---", f"{r['Pomeriggio']}\n{r['H_P']}" if r['Pomeriggio']!="---" else "---", f"{r['Notte']}\n{r['H_N']}" if r['Notte']!="---" else "---"])
            if r["Tipo"] == "Festivo": t_styles.append(('BACKGROUND', (0, idx), (-1, idx), colors.lightpink))
            elif r["Tipo"] == "Prefestivo": t_styles.append(('BACKGROUND', (0, idx), (-1, idx), colors.lightyellow))
        
        table = Table(data, colWidths=[3*cm, 2.2*cm, 4.6*cm, 4.6*cm, 4.6*cm])
        table.setStyle(TableStyle(t_styles))
        elements.append(table)
        doc.build(elements)
        return buf.getvalue()

    st.download_button("📥 SCARICA PDF C.A PORTO EMPEDOCLE", genera_pdf(), f"Turni_{mese_nome}.pdf", "application/pdf", use_container_width=True, type="primary")
