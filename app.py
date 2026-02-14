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

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="C.A. Porto Empedocle - Pro", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f7fafc; }
    .main-title { color: #2c5282; font-weight: 800; font-size: 2.2rem; text-align: center; margin-bottom: 20px; }
    .sidebar-header { color: #2b6cb0; font-weight: 700; border-bottom: 2px solid #bee3f8; padding-bottom: 5px; margin-bottom: 15px; }
    .alert-box { padding: 10px; background-color: #fff3cd; border-left: 5px solid #ffca28; color: #856404; border-radius: 5px; margin-bottom: 10px; }
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

def is_festivo(dt, fest): return dt.weekday() == 6 or (dt.day, dt.month) in fest
def is_prefestivo(dt, fest): return dt.weekday() == 5 or is_festivo(dt + timedelta(days=1), fest)

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
    st.markdown("<div class='sidebar-header'>⚖️ LIMITI ORE</div>", unsafe_allow_html=True)
    ore_max = st.slider("Limite ore mensili (Alert):", 120, 250, 180)

    st.divider()
    st.markdown("<div class='sidebar-header'>📅 SCORCIATOIE INDISPONIBILITÀ</div>", unsafe_allow_html=True)
    m_sel = st.selectbox("Seleziona Medico:", st.session_state.medici)
    cal_data = calendar.monthcalendar(anno_sel, m_idx_v)
    
    st.write("**Giorni Feriali (Notte):**")
    cols_f = st.columns(5)
    for i, l in enumerate(["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì"]):
        if cols_f[i].button(l):
            for s in cal_data:
                d = s[i]
                if d != 0: 
                    current = st.session_state.assenze[m_sel].get(str(d), [])
                    st.session_state.assenze[m_sel][str(d)] = list(set(current + ["N"]))
            st.rerun()

    st.write("**Weekend:**")
    c_s = st.columns(3)
    labels = ["Mattina", "Pomeriggio", "Notte"]
    codes = ["M", "P", "N"]
    for i in range(3):
        if c_s[i].button(f"Sab {labels[i]}"):
            for s in cal_data:
                if s[5] != 0:
                    d_str = str(s[5])
                    curr = st.session_state.assenze[m_sel].get(d_str, [])
                    st.session_state.assenze[m_sel][d_str] = list(set(curr + [codes[i]]))
            st.rerun()

    c_d = st.columns(3)
    for i in range(3):
        if c_d[i].button(f"Dom {labels[i]}"):
            for s in cal_data:
                if s[6] != 0:
                    d_str = str(s[6])
                    curr = st.session_state.assenze[m_sel].get(d_str, [])
                    st.session_state.assenze[m_sel][d_str] = list(set(curr + [codes[i]]))
            st.rerun()

    st.divider()
    if st.button("🗑️ SVUOTA ASSENZE MEDICO", use_container_width=True):
        st.session_state.assenze[m_sel] = {}; st.rerun()
    
    # Backup corretto
    backup_obj = {"assenze": st.session_state.assenze, "limite": ore_max}
    st.download_button("💾 SCARICA BACKUP", json.dumps(backup_obj), f"backup_{mese_nome}.json", use_container_width=True)

# --- 5. LOGICA GENERAZIONE ---
st.markdown(f"<div class='main-title'>C.A. Porto Empedocle - {mese_nome} {anno_sel}</div>", unsafe_allow_html=True)

if st.button("🚀 GENERA TURNI", type="primary", use_container_width=True):
    fest = get_festivita(anno_sel)
    gg_m = calendar.monthrange(anno_sel, m_idx_v)[1]
    res = []
    u_n = None 
    
    for d in range(1, gg_m + 1):
        dt = datetime(anno_sel, m_idx_v, d)
        tipo = "Festivo" if is_festivo(dt, fest) else ("Prefestivo" if is_prefestivo(dt, fest) else "Feriale")
        d_str = str(d)
        
        # Inizializzazione dati turno
        h_m, h_p, h_n = "---", "---", "20:00 - 08:00"
        o_m, o_p, o_n = 0, 0, 12
        
        if tipo == "Festivo":
            h_m, h_p = "08:00 - 14:00", "14:00 - 20:00"
            o_m, o_p = 6, 6
        elif tipo == "Prefestivo":
            h_m, h_p = "10:00 - 14:00", "14:00 - 20:00"
            o_m, o_p = 4, 6

        # Filtro disponibilità
        disp_m = [m for m in st.session_state.medici if "M" not in st.session_state.assenze[m].get(d_str, [])]
        disp_p = [m for m in st.session_state.medici if "P" not in st.session_state.assenze[m].get(d_str, [])]
        disp_n = [m for m in st.session_state.medici if "N" not in st.session_state.assenze[m].get(d_str, [])]

        # Assegnazione Notte
        n_m = random.choice([m for m in disp_n if m != u_n] or disp_n)
        u_n = n_m
        
        # Assegnazione Mattina/Pomeriggio
        m_m = random.choice([m for m in disp_m if m != n_m] or disp_m) if o_m > 0 else "---"
        p_m = random.choice([m for m in disp_p if m not in [n_m, m_m]] or disp_p) if o_p > 0 else "---"

        res.append({
            "Data": f"{d} {['LUN','MAR','MER','GIO','VEN','SAB','DOM'][dt.weekday()]}", 
            "Tipo": tipo, "Mattina": m_m, "Pomeriggio": p_m, "Notte": n_m, 
            "OreM": o_m, "OreP": o_p, "OreN": o_n,
            "H_M": h_m, "H_P": h_p, "H_N": h_n
        })
    st.session_state.db_turni = pd.DataFrame(res)

# --- 6. VISUALIZZAZIONE E STATISTICHE ---
if not st.session_state.db_turni.empty:
    # Calcolo statistiche sicuro
    stats_data = []
    df = st.session_state.db_turni
    for m in st.session_state.medici:
        ore_m = df[df['Mattina'] == m]['OreM'].sum()
        ore_p = df[df['Pomeriggio'] == m]['OreP'].sum()
        ore_n = df[df['Notte'] == m]['OreN'].sum()
        totale = ore_m + ore_p + ore_n
        stats_data.append({"Medico": m, "Ore Totali": totale})
        
        if totale > ore_max:
            st.markdown(f"<div class='alert-box'>⚠️ <b>{m}</b>: {totale} ore (Limite: {ore_max})</div>", unsafe_allow_html=True)

    st.subheader("Tabella Turni")
    st.data_editor(df[["Data", "Tipo", "Mattina", "Pomeriggio", "Notte"]], use_container_width=True, hide_index=True)
    
    st.subheader("📊 Riepilogo Ore")
    st.table(pd.DataFrame(stats_data))

    # --- 7. PDF ---
    def genera_pdf(stats_list):
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=0.8*cm, bottomMargin=0.8*cm, leftMargin=0.8*cm, rightMargin=0.8*cm)
        elements = []
        styles = getSampleStyleSheet()
        
        elements.append(Paragraph(f"<b>GUARDIA MEDICA PORTO EMPEDOCLE - {mese_nome.upper()} {anno_sel}</b>", styles['Title']))
        
        # Tabella Turni
        data = [["DATA", "TIPO", "MATTINA", "POMERIGGIO", "NOTTE"]]
        table_style = [
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('BACKGROUND', (0,0), (-1,0), colors.cadetblue),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke)
        ]
        
        for i, r in enumerate(df.to_dict('records')):
            data.append([r['Data'], r["Tipo"], f"{r['Mattina']}\n{r['H_M']}", f"{r['Pomeriggio']}\n{r['H_P']}", f"{r['Notte']}\n{r['H_N']}"])
            if r["Tipo"] == "Festivo": table_style.append(('BACKGROUND', (0, i+1), (-1, i+1), colors.Color(1, 0.8, 0.8)))
            elif r["Tipo"] == "Prefestivo": table_style.append(('BACKGROUND', (0, i+1), (-1, i+1), colors.Color(1, 1, 0.85)))
        
        t1 = Table(data, colWidths=[2.2*cm, 2*cm, 4.8*cm, 4.8*cm, 4.8*cm])
        t1.setStyle(TableStyle(table_style))
        elements.append(t1)
        
        elements.append(Spacer(1, 15))
        elements.append(Paragraph("<b>RIEPILOGO ORE TOTALI</b>", styles['Heading3']))
        
        # Tabella Ore
        data_s = [["MEDICO", "ORE TOTALI"]]
        for s in stats_list: data_s.append([s['Medico'], str(s['Ore Totali'])])
        t2 = Table(data_s, colWidths=[5*cm, 4*cm])
        t2.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('BACKGROUND', (0,0), (-1,0), colors.lightgrey)]))
        elements.append(t2)
        
        doc.build(elements)
        return buf.getvalue()

    st.download_button("📥 SCARICA PDF COLORATO", genera_pdf(stats_data), f"Turni_{mese_nome}.pdf", "application/pdf", use_container_width=True)
