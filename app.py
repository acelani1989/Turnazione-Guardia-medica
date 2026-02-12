import streamlit as st
import pandas as pd
import calendar
import random
import io
import json
import base64
from datetime import datetime
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
        background-image: linear-gradient(rgba(255, 255, 255, 0.8), rgba(255, 255, 255, 0.8)), 
        url("https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?ixlib=rb-4.0.3&auto=format&fit=crop&w=1600&q=80");
        background-size: cover;
        background-attachment: fixed;
    }
    .main-title { color: #1a365d; font-weight: 800; font-size: 2.2rem; text-align: center; margin-bottom: 15px; }
    .settings-section { background-color: rgba(255, 255, 255, 0.95); padding: 12px; border-radius: 10px; border-left: 5px solid #2b6cb0; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 10px; }
    .sidebar-header { color: #2b6cb0; font-weight: 700; border-bottom: 2px solid #bee3f8; padding-bottom: 5px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNZIONI LOGICHE (STABILI) ---
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
    st.markdown("<div class='sidebar-header'>⚕️ GESTIONE</div>", unsafe_allow_html=True)
    anno_sel = st.number_input("Anno:", 2024, 2030, 2026)
    mesi_ita = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
    mese_nome = st.selectbox("Mese:", mesi_ita, index=datetime.now().month - 1)
    m_idx_v = mesi_ita.index(mese_nome) + 1
    soglia_ore = st.slider("Soglia Alert Ore:", 100, 250, 160)
    
    st.divider()
    m_sel = st.selectbox("Assenze Medico:", st.session_state.medici)
    if st.button("🧹 SVUOTA ASSENZE", use_container_width=True):
        st.session_state.assenze[m_sel] = []; st.rerun()

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
st.markdown(f"<div class='main-title'>Gestione Turni: {mese_nome} {anno_sel}</div>", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("<div class='settings-section'><b>🏠 FERIALI</b>", unsafe_allow_html=True)
    f_n = st.text_input("Notte", "20:00 - 08:00")
with c2:
    st.markdown("<div class='settings-section'><b>🕒 PREFESTIVI</b>", unsafe_allow_html=True)
    p_p = st.text_input("Pomeriggio", "10:00 - 20:00", key="pp")
    p_n = st.text_input("Notte", "20:00 - 08:00", key="pn")
with c3:
    st.markdown("<div class='settings-section'><b>🚩 FESTIVI</b>", unsafe_allow_html=True)
    fes_m = st.text_input("Mattina", "08:00 - 14:00", key="fm")
    fes_p = st.text_input("Pomeriggio", "14:00 - 20:00", key="fp")
    fes_n = st.text_input("Notte", "20:00 - 08:00", key="fn")

if st.button("🚀 GENERA / RIGENERA TURNI", type="primary", use_container_width=True):
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
        
        if wd == 6 and tipo == "Festivo":
            if not vincoli["Piscopo_Dom"] and "Piscopo" in cand: n_m = "Piscopo"; vincoli["Piscopo_Dom"] = True
            elif not vincoli["Celani_Dom"] and "Celani" in cand: n_m = "Celani"; vincoli["Celani_Dom"] = True
        elif wd == 4 and tipo == "Feriale":
            if not vincoli["Piscopo_Ven"] and "Piscopo" in cand: n_m = "Piscopo"; vincoli["Piscopo_Ven"] = True
            elif not vincoli["Celani_Ven"] and "Celani" in cand: n_m = "Celani"; vincoli["Celani_Ven"] = True

        if tipo == "Festivo":
            m_m = random.choice([m for m in cand if m != n_m] or cand)
            p_m = m_m 
            h_m, h_p, h_n = fes_m, fes_p, fes_n
            if n_m == "---": n_m = random.choice([m for m in cand if m != m_m] or cand)
        elif tipo == "Prefestivo":
            p_m = random.choice(cand)
            h_p, h_n = p_p, p_n
            if n_m == "---": n_m = random.choice([m for m in cand if m != p_m] or cand)
        else:
            if n_m == "---": n_m = random.choice(cand)
            h_n = f_n
            
        u_n = n_m
        res.append({"Data": f"{d} {calendar.day_name[wd][:3].upper()}", "Info": nome_f, "Tipo": tipo, "Mattina": m_m, "Pomeriggio": p_m, "Notte": n_m, "H_M": h_m, "H_P": h_p, "H_N": h_n})
    st.session_state.db_turni = pd.DataFrame(res)

# --- 6. RIEPILOGO E PDF ---
if not st.session_state.db_turni.empty:
    t1, t2 = st.tabs(["📝 MODIFICA & ORE", "👁️ ANTEPRIMA & PDF"])
    
    # Calcolo Ore
    ore_m = {m: 0.0 for m in st.session_state.medici}
    for _, r in st.session_state.db_turni.iterrows():
        if r["Mattina"] in ore_m: ore_m[r["Mattina"]] += calcola_durata(r["H_M"])
        if r["Pomeriggio"] in ore_m: ore_m[r["Pomeriggio"]] += calcola_durata(r["H_P"])
        if r["Notte"] in ore_m: ore_m[r["Notte"]] += calcola_durata(r["H_N"])

    with t1:
        st.session_state.db_turni = st.data_editor(st.session_state.db_turni, use_container_width=True, hide_index=True)
        st.markdown(f"### 📊 Riepilogo Ore {mese_nome}")
        st.table(pd.DataFrame([{"Medico": m, "Ore": f"{int(h)} h"} for m, h in ore_m.items()]))

    with t2:
        def genera_pdf():
            buf = io.BytesIO()
            doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=0.5*cm, bottomMargin=0.5*cm, leftMargin=0.5*cm, rightMargin=0.5*cm)
            elements = []
            styles = getSampleStyleSheet()
            
            # Titolo Principale
            elements.append(Paragraph(f"<b>PROGRAMMAZIONE TURNI - {mese_nome.upper()} {anno_sel}</b>", styles['Title']))
            elements.append(Spacer(1, 10))
            
            # Tabella Turni
            data = [["DATA", "TIPO", "MATTINA", "POMERIGGIO", "NOTTE"]]
            t_styles = [
                ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('FONTSIZE', (0,0), (-1,-1), 8),
                ('BACKGROUND', (0,0), (-1,0), colors.cadetblue),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ]
            
            for i, r in enumerate(st.session_state.db_turni.to_dict('records')):
                idx = i + 1
                row = [f"{r['Data']}\n{r['Info']}", r["Tipo"], 
                       f"{r['Mattina']}\n{r['H_M']}" if r['Mattina']!="---" else "---",
                       f"{r['Pomeriggio']}\n{r['H_P']}" if r['Pomeriggio']!="---" else "---",
                       f"{r['Notte']}\n{r['H_N']}" if r['Notte']!="---" else "---"]
                data.append(row)
                
                # Colori righe
                if r["Tipo"] == "Festivo": t_styles.append(('BACKGROUND', (0, idx), (-1, idx), colors.lightpink))
                elif r["Tipo"] == "Prefestivo": t_styles.append(('BACKGROUND', (0, idx), (-1, idx), colors.lightyellow))
            
            table = Table(data, colWidths=[3*cm, 2.5*cm, 4.8*cm, 4.8*cm, 4.8*cm])
            table.setStyle(TableStyle(t_styles))
            elements.append(table)
            
            # Riepilogo Ore
            elements.append(Spacer(1, 15))
            elements.append(Paragraph(f"<b>RIEPILOGO ORE DEL MESE CORRENTE - {mese_nome.upper()}</b>", styles['Heading3']))
            
            data_ore = [["MEDICO", "TOTALE ORE"]] + [[m, f"{int(h)} h"] for m, h in ore_m.items()]
            t_ore = Table(data_ore, colWidths=[6*cm, 4*cm])
            t_ore.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTSIZE', (0,0), (-1,-1), 9)
            ]))
            elements.append(t_ore)
            
            doc.build(elements)
            return buf.getvalue()

        # Visualizzazione Anteprima
        pdf_bytes = genera_pdf()
        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
        
        st.download_button("📥 SCARICA PDF UFFICIALE", pdf_bytes, f"Turni_{mese_nome}.pdf", "application/pdf", use_container_width=True, type="primary")
