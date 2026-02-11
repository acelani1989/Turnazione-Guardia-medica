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

# --- 1. CONFIGURAZIONE E STILE ---
st.set_page_config(page_title="Master Guardia Medica", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f4f8fb; }
    .main-title { 
        color: #1a365d; 
        font-family: 'Helvetica Neue', Arial, sans-serif;
        font-weight: 700; font-size: 2.3rem; 
        border-bottom: 3px solid #63b3ed; 
        padding-bottom: 10px; margin-bottom: 25px;
    }
    .stat-card { 
        background-color: #ffffff; padding: 20px; border-radius: 12px; 
        border: 1px solid #e2e8f0; box-shadow: 0 4px 6px rgba(0,0,0,0.02); 
        text-align: center; border-top: 5px solid #63b3ed;
    }
    [data-testid="stSidebar"] { background-color: #e6f0f7; border-right: 1px solid #cbd5e0; }
    [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] label, [data-testid="stSidebar"] p { 
        color: #2c5282 !important; 
    }
    /* Stile per i bottoni delle scorciatoie e calendario */
    .stButton>button { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATI E TRADUZIONI ---
giorni_ita = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
mesi_ita = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", 
            "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]

if 'medici' not in st.session_state:
    st.session_state.medici = ["Piscopo", "Celani"]
if 'assenze' not in st.session_state:
    st.session_state.assenze = {m: [] for m in st.session_state.medici}
if 'db_turni' not in st.session_state:
    st.session_state.db_turni = pd.DataFrame()

# --- 3. SIDEBAR CON SCORCIATOIE E CALENDARIO EVIDENZIATO ---
with st.sidebar:
    st.markdown("## 🏥 Gestione Staff")
    
    nuovo_m = st.text_input("Aggiungi Medico:", key="add_doc", placeholder="Nome")
    if st.button("AGGIUNGI"):
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
    
    st.write("---")
    st.markdown("### 📅 Indisponibilità")
    m_sel = st.selectbox("Seleziona Medico:", st.session_state.medici)
    
    # --- SCORCIATOIE GIORNI FISSI ---
    st.write("Segna tutti i:")
    cols_scor = st.columns(4)
    m_idx_v = mesi_ita.index(st.session_state.get('ms', 'Febbraio')) + 1
    for i, g_nome in enumerate(giorni_ita):
        if cols_scor[i % 4].button(g_nome, key=f"fixed_{g_nome}"):
            for d in range(1, 32):
                try:
                    if datetime(2026, m_idx_v, d).weekday() == i:
                        if d not in st.session_state.assenze[m_sel]: 
                            st.session_state.assenze[m_sel].append(d)
                except: pass
            st.rerun()

    if st.button("🧹 Svuota Assenze " + m_sel):
        st.session_state.assenze[m_sel] = []
        st.rerun()

    # --- CALENDARIO VISIVO EVIDENZIATO ---
    st.write("Seleziona date specifiche:")
    cal = calendar.monthcalendar(2026, m_idx_v)
    for week in cal:
        cols_cal = st.columns(7)
        for i, day in enumerate(week):
            if day != 0:
                is_abs = day in st.session_state.assenze.get(m_sel, [])
                # Il trucco per l'evidenziazione: type="primary" colora il tasto
                if cols_cal[i].button(str(day), key=f"btn_d_{day}", type="primary" if is_abs else "secondary"):
                    if is_abs:
                        st.session_state.assenze[m_sel].remove(day)
                    else:
                        st.session_state.assenze[m_sel].append(day)
                    st.rerun()

# --- 4. LOGICA GENERAZIONE ---
def genera_piano():
    m_idx = mesi_ita.index(st.session_state.ms) + 1
    gg_m = calendar.monthrange(2026, m_idx)[1]
    data = []
    for d in range(1, gg_m + 1):
        dt = datetime(2026, m_idx, d)
        is_festivo = (dt.weekday() == 6 or (m_idx == 2 and d == 25))
        disp = [m for m in st.session_state.medici if d not in st.session_state.assenze.get(m, [])]
        if len(disp) < 3: disp = st.session_state.medici
        m_rand = random.sample(disp, min(3, len(disp)))
        while len(m_rand) < 3: m_rand.append("---")
        data.append({
            "Data": f"{d} {giorni_ita[dt.weekday()]}",
            "Stato": "🚩 FESTIVO" if is_festivo else "Feriale",
            "Mattina": m_rand[0] if is_festivo else "---",
            "Pomeriggio": m_rand[1],
            "Notte": m_rand[2]
        })
    st.session_state.db_turni = pd.DataFrame(data)

# --- 5. INTERFACCIA PRINCIPALE ---
st.markdown("<div class='main-title'>Med Turni Master - Guardia Medica Porto Empedocle</div>", unsafe_allow_html=True)

c1, c2, c3 = st.columns([1,1,1])
with c1: m_scelto = st.selectbox("Seleziona Mese", mesi_ita, index=1, key="ms")
with c2: st.write("### 📅 2026")
with c3:
    st.write("###")
    if st.button("🚀 GENERA PIANO TURNI", type="primary", use_container_width=True):
        genera_piano()

if not st.session_state.db_turni.empty:
    # Calcolo Ore
    ore = {m: 0 for m in st.session_state.medici}
    for col in ["Mattina", "Pomeriggio", "Notte"]:
        peso = 12 if col == "Notte" else 6
        for m in st.session_state.db_turni[col]:
            if m in ore: ore[m] += peso
    
    st.markdown("### 📊 Riepilogo Ore Mensili")
    c_ore = st.columns(len(st.session_state.medici))
    for i, med in enumerate(st.session_state.medici):
        with c_ore[i]:
            st.markdown(f"""<div class='stat-card'><b>DOTT. {med.upper()}</b><br><span style='font-size: 1.8rem; color: #3182ce;'>{ore[med]}h</span></div>""", unsafe_allow_html=True)

    st.divider()

    # Tabellone
    st.markdown("### 📅 Turnazione Mensile")
    edited_df = st.data_editor(
        st.session_state.db_turni,
        column_config={
            "Data": st.column_config.TextColumn("DATA", disabled=True),
            "Stato": st.column_config.TextColumn("TIPO", disabled=True),
            "Mattina": st.column_config.SelectboxColumn("MATTINA (08:00-14:00)", options=st.session_state.medici),
            "Pomeriggio": st.column_config.SelectboxColumn("POMERIGGIO (14:00-20:00)", options=st.session_state.medici),
            "Notte": st.column_config.SelectboxColumn("NOTTE (20:00-08:00)", options=st.session_state.medici),
        },
        hide_index=True, use_container_width=True
    )
    st.session_state.db_turni = edited_df

    # PDF con orari e conteggio
    def crea_pdf():
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=landscape(A4), topMargin=20)
        elements = []
        styles = getSampleStyleSheet()
        elements.append(Paragraph(f"<b>MASTER TURNI - GUARDIA MEDICA PORTO EMPEDOCLE</b>", styles['Title']))
        elements.append(Paragraph(f"<center>{m_scelto.upper()} 2026</center>", styles['Heading2']))
        elements.append(Spacer(1, 15))
        
        data_p = [["DATA", "TIPO", "MATTINA\n(08-14)", "POMERIGGIO\n(14-20)", "NOTTE\n(20-08)"]]
        for _, r in st.session_state.db_turni.iterrows():
            data_p.append([str(r["Data"]), str(r["Stato"]), str(r["Mattina"]), str(r["Pomeriggio"]), str(r["Notte"])])
        
        t = Table(data_p, colWidths=[80, 70, 170, 170, 170])
        t.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('BACKGROUND', (0,0), (-1,0), colors.cadetblue),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        elements.append(t)
        
        elements.append(Spacer(1, 25))
        elements.append(Paragraph("<b>RIEPILOGO ORE TOTALI PER MEDICO</b>", styles['Heading3']))
        ore_data = [["MEDICO", "TOTALE ORE"]]
        for m in st.session_state.medici:
            ore_data.append([f"Dott. {m}", f"{ore[m]} ore"])
        t2 = Table(ore_data, colWidths=[200, 100])
        t2.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.black), ('BACKGROUND', (0,0), (-1,0), colors.lightgrey)]))
        elements.append(t2)
        
        doc.build(elements)
        return buf.getvalue()

    st.divider()
    st.download_button("📥 SCARICA PDF UFFICIALE", data=crea_pdf(), file_name=f"Turni_Guardia_Medica_{m_scelto}.pdf", mime="application/pdf", use_container_width=True)