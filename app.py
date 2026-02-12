import streamlit as st
import pandas as pd
import calendar
import random
import io
import json
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm

# --- 1. CONFIGURAZIONE GRAFICA PULITA ---
st.set_page_config(page_title="Gestione Turni Medica", layout="wide")

# CSS per garantire che tutto sia leggibile (testo nero su fondo chiaro)
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stMarkdown, p, h1, h2, h3, span { color: #1e293b !important; }
    .sidebar-header { 
        font-weight: bold; color: #38bdf8 !important; 
        border-bottom: 1px solid #475569; margin-bottom: 10px; 
    }
    .card {
        background-color: white; padding: 20px;
        border-radius: 10px; border: 1px solid #e2e8f0;
        margin-bottom: 20px; color: #1e293b;
    }
    </style>
    """, unsafe_allow_html=True)

# Immagine Intestazione (Studio Medico)
st.image("https://images.unsplash.com/photo-1504813184591-01592f279d6d?ixlib=rb-4.0.3&auto=format&fit=crop&w=1200&h=200&q=80", use_container_width=True)

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
        p = intervallo.split("-")
        d = (datetime.strptime(p[1].strip(), "%H:%M") - datetime.strptime(p[0].strip(), "%H:%M")).seconds / 3600
        return d if d > 0 else d + 24
    except: return 0

# --- 3. SESSION STATE ---
if 'medici' not in st.session_state: st.session_state.medici = ["Piscopo", "Celani", "Lombardo", "Siracusa"]
if 'assenze' not in st.session_state: st.session_state.assenze = {m: [] for m in st.session_state.medici}
if 'db_turni' not in st.session_state: st.session_state.db_turni = pd.DataFrame()

# --- 4. SIDEBAR (BACKUP, STAFF, INDISPONIBILITÀ) ---
with st.sidebar:
    st.markdown("<div class='sidebar-header'>⚕️ GESTIONE STUDIO</div>", unsafe_allow_html=True)
    anno_sel = st.number_input("Anno", 2024, 2030, 2026)
    mesi_ita = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
    mese_nome = st.selectbox("Mese", mesi_ita, index=1)
    m_idx = mesi_ita.index(mese_nome) + 1
    
    st.markdown("<div class='sidebar-header'>👨‍⚕️ MEDICI</div>", unsafe_allow_html=True)
    nuovo = st.text_input("Aggiungi Nome")
    if st.button("AGGIUNGI"):
        if nuovo and nuovo not in st.session_state.medici:
            st.session_state.medici.append(nuovo)
            st.session_state.assenze[nuovo] = []
            st.rerun()

    st.markdown("<div class='sidebar-header'>📅 INDISPONIBILITÀ</div>", unsafe_allow_html=True)
    m_sel = st.selectbox("Medico", st.session_state.medici)
    
    # Scorciatoie giorni
    g_short = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
    cols_sh = st.columns(7)
    cal_data = calendar.monthcalendar(anno_sel, m_idx)
    for i, label in enumerate(g_short):
        if cols_sh[i].button(label, key=f"sh_{label}"):
            g_da_cambiare = [s[i] for s in cal_data if s[i] != 0]
            current = st.session_state.assenze.get(m_sel, [])
            if all(d in current for d in g_da_cambiare):
                st.session_state.assenze[m_sel] = [d for d in current if d not in g_da_cambiare]
            else:
                st.session_state.assenze[m_sel] = list(set(current + g_da_cambiare))
            st.rerun()

    # Mini Calendario Sidebar
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
st.title(f"Turni Guardia Medica: {mese_nome} {anno_sel}")

# Orari
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("<div class='card'><b>🏠 FERIALI</b>", unsafe_allow_html=True)
    f_n = st.text_input("Notte", "20:00 - 08:00")
    st.markdown("</div>", unsafe_allow_html=True)
with c2:
    st.markdown("<div class='card'><b>🕒 PREFESTIVI</b>", unsafe_allow_html=True)
    p_p = st.text_input("Pomeriggio", "10:00 - 20:00")
    p_n = st.text_input("Notte", "20:00 - 08:00", key="pn1")
    st.markdown("</div>", unsafe_allow_html=True)
with c3:
    st.markdown("<div class='card'><b>🚩 FESTIVI</b>", unsafe_allow_html=True)
    fes_m = st.text_input("Mattina", "08:00 - 14:00")
    fes_p = st.text_input("Pomeriggio", "14:00 - 20:00")
    fes_n = st.text_input("Notte", "20:00 - 08:00", key="fn1")
    st.markdown("</div>", unsafe_allow_html=True)

if st.button("🚀 GENERA TURNI", type="primary", use_container_width=True):
    festivita = get_festivita(anno_sel)
    gg_m = calendar.monthrange(anno_sel, m_idx)[1]
    res = []
    u_n = None
    for d in range(1, gg_m + 1):
        dt = datetime(anno_sel, m_idx, d)
        wd = dt.weekday()
        is_f = (d, m_idx) in festivita
        tipo = "Festivo" if (wd == 6 or is_f) else ("Prefestivo" if wd == 5 else "Feriale")
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
        res.append({"Giorno": f"{d} {g_short[wd]}", "Tipo": tipo, "Mattina": m_m, "Pomeriggio": p_m, "Notte": n_m, "H_M": h_m, "H_P": h_p, "H_N": h_n})
    st.session_state.db_turni = pd.DataFrame(res)

# --- 6. RISULTATI ---
if not st.session_state.db_turni.empty:
    t1, t2 = st.tabs(["📝 MODIFICA DATI", "👁️ ANTEPRIMA & PDF"])
    with t1:
        st.session_state.db_turni = st.data_editor(st.session_state.db_turni, use_container_width=True, hide_index=True)
        ore = {m: 0.0 for m in st.session_state.medici}
        for _, r in st.session_state.db_turni.iterrows():
            d1, d2, d3 = calcola_durata(r["H_M"]), calcola_durata(r["H_P"]), calcola_durata(r["H_N"])
            for m, h in [(r["Mattina"], d1), (r["Pomeriggio"], d2), (r["Notte"], d3)]:
                if m in ore: ore[m] += h
        st.write("### 📊 Riepilogo Ore")
        st.table(pd.DataFrame([{"Medico": m, "Ore": int(h)} for m, h in ore.items()]))

    with t2:
        st.dataframe(st.session_state.db_turni[["Giorno", "Mattina", "Pomeriggio", "Notte"]], use_container_width=True, hide_index=True)
        
        def make_pdf():
            buf = io.BytesIO()
            doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=1*cm, bottomMargin=1*cm)
            elements = [Paragraph(f"TURNI {mese_nome.upper()} {anno_sel}", getSampleStyleSheet()['Title'])]
            data = [["GIORNO", "MATTINA", "POMERIGGIO", "NOTTE"]]
            styles = [('GRID', (0,0), (-1,-1), 0.5, colors.black), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('BACKGROUND', (0,0), (-1,0), colors.lightgrey)]
            for i, r in enumerate(st.session_state.db_turni.to_dict('records')):
                data.append([r["Giorno"], r["Mattina"], r["Pomeriggio"], r["Notte"]])
                if r["Tipo"] == "Festivo": styles.append(('BACKGROUND', (0, i+1), (-1, i+1), colors.lightpink))
            t = Table(data, colWidths=[3*cm, 5*cm, 5*cm, 5*cm])
            t.setStyle(TableStyle(styles))
            elements.append(t)
            doc.build(elements)
            return buf.getvalue()
        
        st.download_button("📥 SCARICA PDF", make_pdf(), f"Turni_{mese_nome}.pdf", "application/pdf", type="primary", use_container_width=True)
