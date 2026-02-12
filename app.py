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

# --- 1. CONFIGURAZIONE E DESIGN "GUARDIA MEDICA" ---
st.set_page_config(page_title="Master Guardia Medica Pro", layout="wide")

st.markdown("""
    <style>
    .stApp {
        background-image: linear-gradient(rgba(10, 25, 47, 0.4), rgba(10, 25, 47, 0.4)), 
        url("https://images.unsplash.com/photo-1516549655169-df83a0774514?ixlib=rb-4.0.3&auto=format&fit=crop&w=2000&q=80");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }
    /* Pannello principale in stile Glassmorphism medico */
    .main .block-container {
        background-color: rgba(255, 255, 255, 0.95);
        padding: 2.5rem;
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        margin-top: 15px;
        border: 1px solid rgba(0, 150, 255, 0.1);
    }
    .main-title { 
        color: #004a99; 
        font-weight: 900; 
        font-size: 2.8rem; 
        text-align: center; 
        margin-bottom: 5px;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    .sub-title {
        color: #555;
        text-align: center;
        margin-bottom: 30px;
        font-style: italic;
    }
    .settings-section { 
        background-color: #f0f7ff; 
        padding: 18px; 
        border-radius: 15px; 
        border-top: 4px solid #004a99; 
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    .sidebar-header { 
        color: #004a99; 
        font-weight: 800; 
        border-bottom: 3px solid #004a99; 
        padding-bottom: 8px; 
        margin-bottom: 20px;
        font-size: 1.2rem;
    }
    /* Input e Testi */
    label p { font-weight: 700 !important; color: #002d5c !important; }
    .stButton>button { border-radius: 10px; font-weight: 700; transition: 0.3s; }
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
    try: dt_pp = dt_p.replace(day=g_p+1)
    except: dt_pp = datetime(anno, m_p+1, 1)
    return {(1, 1): "Capodanno", (6, 1): "Epifania", (25, 4): "Liberazione", (1, 5): "Festa Lavoro", 
            (2, 6): "Festa Repubblica", (15, 8): "Ferragosto", (1, 11): "Ognissanti", 
            (8, 12): "Immacolata", (25, 12): "Natale", (26, 12): "S. Stefano",
            (dt_p.day, dt_p.month): "Pasqua", (dt_pp.day, dt_pp.month): "Pasquetta", (25, 2): "S. Patrono"}

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
    st.markdown("<div class='sidebar-header'>🚑 UNITÀ GESTIONALE</div>", unsafe_allow_html=True)
    anno_sel = st.number_input("Anno:", 2024, 2030, 2026)
    mesi_ita = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
    mese_nome = st.selectbox("Seleziona Mese:", mesi_ita, index=1)
    m_idx_v = mesi_ita.index(mese_nome) + 1
    
    soglia_ore = st.slider("Soglia Sicurezza Ore:", 100, 250, 160)
    
    st.divider()
    st.markdown("<div class='sidebar-header'>👩‍⚕️ STAFF MEDICO</div>", unsafe_allow_html=True)
    nuovo_m = st.text_input("Aggiungi Personale:")
    if st.button("➕ INSERISCI"):
        if nuovo_m and nuovo_m not in st.session_state.medici:
            st.session_state.medici.append(nuovo_m); st.session_state.assenze[nuovo_m] = []; st.rerun()
    
    for med in st.session_state.medici:
        c_n, c_d = st.columns([4, 1])
        c_n.write(f"**{med}**")
        if c_d.button("🗑️", key=f"del_{med}"):
            st.session_state.medici.remove(med); st.rerun()

    st.divider()
    st.markdown("<div class='sidebar-header'>🗓️ CALENDARIO ASSENZE</div>", unsafe_allow_html=True)
    m_sel = st.selectbox("Medico in ferie/indisponibile:", st.session_state.medici)
    
    if st.button("🧹 RESET ASSENZE MEDICO", use_container_width=True):
        st.session_state.assenze[m_sel] = []
        st.rerun()

    g_short = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
    cal_data = calendar.monthcalendar(anno_sel, m_idx_v)
    
    for week in cal_data:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day != 0:
                is_abs = day in st.session_state.assenze.get(m_sel, [])
                if cols[i].button(str(day), key=f"d_{day}", type="primary" if is_abs else "secondary"):
                    if is_abs: st.session_state.assenze[m_sel].remove(day)
                    else: st.session_state.assenze[m_sel].append(day)
                    st.rerun()

# --- 5. INTERFACCIA PRINCIPALE ---
st.markdown("<div class='main-title'>Sistema Gestione Turni</div>", unsafe_allow_html=True)
st.markdown(f"<div class='sub-title'>Presidio di Guardia Medica - {mese_nome} {anno_sel}</div>", unsafe_allow_html=True)



c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("<div class='settings-section'><b>🏠 SERVIZIO FERIALE</b>", unsafe_allow_html=True)
    f_n = st.text_input("Notte", "20:00 - 08:00")
with c2:
    st.markdown("<div class='settings-section'><b>🕓 PREFESTIVI</b>", unsafe_allow_html=True)
    p_p = st.text_input("Pomeriggio", "10:00 - 20:00", key="pp")
    p_n = st.text_input("Notte", "20:00 - 08:00", key="pn")
with c3:
    st.markdown("<div class='settings-section'><b>🚩 FESTIVI E DOMENICHE</b>", unsafe_allow_html=True)
    fes_m = st.text_input("Mattina", "08:00 - 14:00", key="fm")
    fes_p = st.text_input("Pomeriggio", "14:00 - 20:00", key="fp")
    fes_n = st.text_input("Notte", "20:00 - 08:00", key="fn")

if st.button("💾 GENERA PIANO TURNI MENSILE", type="primary", use_container_width=True):
    fest = get_festivita(anno_sel)
    gg_m = calendar.monthrange(anno_sel, m_idx_v)[1]
    res = []
    u_n = None
    
    vincoli = {"Piscopo_Dom": False, "Celani_Dom": False, "Piscopo_Ven": False, "Celani_Ven": False}
    
    for d in range(1, gg_m + 1):
        dt = datetime(anno_sel, m_idx_v, d)
        wd = dt.weekday()
        nome_f = fest.get((d, m_idx_v), "")
        tipo = "Festivo" if (wd == 6 or (d, m_idx_v) in fest) else ("Prefestivo" if (wd == 5 or (d==24 and m_idx_v==2)) else "Feriale")
        
        disp = [m for m in st.session_state.medici if d not in st.session_state.assenze.get(m, [])]
        if not disp: disp = st.session_state.medici
        cand = [m for m in disp if m != u_n] or disp
        
        m_m, p_m, n_m, h_m, h_p, h_n = "---", "---", "---", "---", "---", "---"
        
        # Logica Piscopo/Celani
        if wd == 6 and tipo == "Festivo":
            if not vincoli["Piscopo_Dom"] and "Piscopo" in cand: n_m = "Piscopo"; vincoli["Piscopo_Dom"] = True
            elif not vincoli["Celani_Dom"] and "Celani" in cand: n_m = "Celani"; vincoli["Celani_Dom"] = True
        elif wd == 4 and tipo == "Feriale":
            if not vincoli["Piscopo_Ven"] and "Piscopo" in cand: n_m = "Piscopo"; vincoli["Piscopo_Ven"] = True
            elif not vincoli["Celani_Ven"] and "Celani" in cand: n_m = "Celani"; vincoli["Celani_Ven"] = True

        if tipo == "Festivo":
            # Continuità Mattina-Pomeriggio
            m_m = random.choice([m for m in cand if m != n_m] or cand) if n_m != "---" else random.choice(cand)
            p_m = m_m 
            h_m, h_p = fes_m, fes_p
            if n_m == "---": n_m = random.choice([m for m in cand if m != m_m] or cand)
            h_n = fes_n
        elif tipo == "Prefestivo":
            p_m = random.choice(cand) if n_m == "---" else random.choice([m for m in cand if m != n_m] or cand)
            h_p = p_p
            if n_m == "---": n_m = random.choice([m for m in cand if m != p_m] or cand)
            h_n = p_n
        else:
            if n_m == "---": n_m = random.choice(cand)
            h_n = f_n
            
        u_n = n_m
        res.append({"Data": f"{d} {g_short[wd]}", "Info": nome_f, "Tipo": tipo, "Mattina": m_m, "Pomeriggio": p_m, "Notte": n_m, "H_M": h_m, "H_P": h_p, "H_N": h_n})
    st.session_state.db_turni = pd.DataFrame(res)

# --- 6. RIEPILOGO E PDF ---
if not st.session_state.db_turni.empty:
    t1, t2 = st.tabs(["📝 REVISIONE TURNI", "📄 EXPORT PDF"])
    with t1:
        st.session_state.db_turni = st.data_editor(st.session_state.db_turni, column_config={
            "Data": st.column_config.Column(disabled=True),
            "Info": st.column_config.Column("Note"),
            "Tipo": st.column_config.Column(disabled=True),
            "Mattina": st.column_config.SelectboxColumn(options=["---"] + st.session_state.medici),
            "Pomeriggio": st.column_config.SelectboxColumn(options=["---"] + st.session_state.medici),
            "Notte": st.column_config.SelectboxColumn(options=["---"] + st.session_state.medici)
        }, use_container_width=True, hide_index=True)
        
        ore_m = {m: 0.0 for m in st.session_state.medici}
        for _, r in st.session_state.db_turni.iterrows():
            if r["Mattina"] in ore_m: ore_m[r["Mattina"]] += calcola_durata(r["H_M"])
            if r["Pomeriggio"] in ore_m: ore_m[r["Pomeriggio"]] += calcola_durata(r["H_P"])
            if r["Notte"] in ore_m: ore_m[r["Notte"]] += calcola_durata(r["H_N"])
        
        for med, ore in ore_m.items():
            if ore > soglia_ore: st.error(f"⚠️ **SOGLIA SUPERATA**: {med} ({int(ore)}h)")
            elif ore > (soglia_ore - 15): st.warning(f"🔔 **ATTENZIONE**: {med} ({int(ore)}h)")

    with t2:
        def genera_pdf():
            buf = io.BytesIO()
            doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=0.4*cm, bottomMargin=0.4*cm, leftMargin=0.5*cm, rightMargin=0.5*cm)
            elements = []
            styles = getSampleStyleSheet()
            elements.append(Paragraph(f"TABELLA TURNI GUARDIA MEDICA - {mese_nome.upper()} {anno_sel}", styles['Title']))
            
            data = [["DATA", "TIPO", "MATTINA", "POMERIGGIO", "NOTTE"]]
            t_styles = [('GRID', (0,0), (-1,-1), 0.5, colors.black), ('FONTSIZE', (0,0), (-1,-1), 7), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#004a99")), ('TEXTCOLOR', (0,0), (-1,0), colors.white)]
            
            for i, r in enumerate(st.session_state.db_turni.to_dict('records')):
                row_idx = i + 1
                data.append([f"{r['Data']}", r["Tipo"], r["Mattina"], r["Pomeriggio"], r["Notte"]])
                if r["Tipo"] == "Festivo": t_styles.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor("#ffcccc")))
            
            t = Table(data, colWidths=[3*cm, 2.5*cm, 4.5*cm, 4.5*cm, 4.5*cm]); t.setStyle(TableStyle(t_styles))
            elements.append(t)
            doc.build(elements)
            return buf.getvalue()
        
        st.download_button("📥 SCARICA PROSPETTO UFFICIALE PDF", genera_pdf(), f"Turni_GM_{mese_nome}.pdf", "application/pdf", use_container_width=True)
