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
    st.markdown("<div class='sidebar-header'>📅 SCORCIATOIE</div>", unsafe_allow_html=True)
    m_sel = st.selectbox("Medico:", st.session_state.medici)
    cal_data = calendar.monthcalendar(anno_sel, m_idx_v)
    
    st.write("**Feriali (Notte):**")
    cols_f = st.columns(5)
    for i, l in enumerate(["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì"]):
        if cols_f[i].button(l):
            for s in cal_data:
                d = s[i]
                if d != 0: st.session_state.assenze[m_sel][d] = list(set(st.session_state.assenze[m_sel].get(d, []) + ["N"]))
            st.rerun()

    st.write("**Weekend:**")
    c_s = st.columns(3)
    if c_s[0].button("Sab Mattina"):
        for s in cal_data: (s[5] != 0 and st.session_state.assenze[m_sel].update({s[5]: list(set(st.session_state.assenze[m_sel].get(s[5], []) + ["M"]))}))
        st.rerun()
    if c_s[1].button("Sab Pom"):
        for s in cal_data: (s[5] != 0 and st.session_state.assenze[m_sel].update({s[5]: list(set(st.session_state.assenze[m_sel].get(s[5], []) + ["P"]))}))
        st.rerun()
    if c_s[2].button("Sab Notte"):
        for s in cal_data: (s[5] != 0 and st.session_state.assenze[m_sel].update({s[5]: list(set(st.session_state.assenze[m_sel].get(s[5], []) + ["N"]))}))
        st.rerun()

    c_d = st.columns(3)
    if c_d[0].button("Dom Mattina"):
        for s in cal_data: (s[6] != 0 and st.session_state.assenze[m_sel].update({s[6]: list(set(st.session_state.assenze[m_sel].get(s[6], []) + ["M"]))}))
        st.rerun()
    if c_d[1].button("Dom Pom"):
        for s in cal_data: (s[6] != 0 and st.session_state.assenze[m_sel].update({s[6]: list(set(st.session_state.assenze[m_sel].get(s[6], []) + ["P"]))}))
        st.rerun()
    if c_d[2].button("Dom Notte"):
        for s in cal_data: (s[6] != 0 and st.session_state.assenze[m_sel].update({s[6]: list(set(st.session_state.assenze[m_sel].get(s[6], []) + ["N"]))}))
        st.rerun()

    st.divider()
    if st.button("🗑️ SVUOTA ASSENZE MEDICO", use_container_width=True):
        st.session_state.assenze[m_sel] = {}; st.rerun()
    st.download_button("💾 BACKUP JSON", json.dumps(st.session_state.assenze), f"backup_{mese_nome}.json", use_container_width=True)

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
        
        # Orari e Ore numeriche per conteggio
        h_m_txt, h_p_txt, h_n_txt = "---", "---", "20:00 - 08:00"
        ore_m, ore_p, ore_n = 0, 0, 12
        
        if tipo == "Festivo":
            h_m_txt, h_p_txt = "08:00 - 14:00", "14:00 - 20:00"
            ore_m, ore_p = 6, 6
        elif tipo == "Prefestivo":
            h_m_txt, h_p_txt = "10:00 - 14:00", "14:00 - 20:00"
            ore_m, ore_p = 4, 6

        disp_m = [m for m in st.session_state.medici if "M" not in st.session_state.assenze[m].get(d, [])]
        disp_p = [m for m in st.session_state.medici if "P" not in st.session_state.assenze[m].get(d, [])]
        disp_n = [m for m in st.session_state.medici if "N" not in st.session_state.assenze[m].get(d, [])]

        n_m = random.choice([m for m in disp_n if m != u_n] or disp_n); u_n = n_m
        m_m = random.choice([m for m in disp_m if m != n_m] or disp_m) if ore_m > 0 else "---"
        p_m = random.choice([m for m in disp_p if m not in [n_m, m_m]] or disp_p) if ore_p > 0 else "---"

        res.append({"Data": f"{d} {['LUN','MAR','MER','GIO','VEN','SAB','DOM'][dt.weekday()]}", "Tipo": tipo, 
                    "Mattina": m_m, "Pomeriggio": p_m, "Notte": n_m, 
                    "OreM": ore_m, "OreP": ore_p, "OreN": ore_n,
                    "H_M": h_m_txt, "H_P": h_p_txt, "H_N": h_n_txt})
    st.session_state.db_turni = pd.DataFrame(res)

# --- 6. STATISTICHE E ALERT ---
if not st.session_state.db_turni.empty:
    stats = []
    for m in st.session_state.medici:
        o_m = st.session_state.db_turni[st.session_state.db_turni['Mattina'] == m]['OreM'].sum()
        o_p = st.session_state.db_turni[st.session_state.db_turni['Pomeriggio'] == m]['OreP'].sum()
        o_n = st.session_state.db_turni[st.session_state.db_turni['Notte'] == m]['OreN'].sum()
        tot = o_m + o_p + o_n
        stats.append({"Medico": m, "Ore Totali": tot})
        if tot > ore_max:
            st.markdown(f"<div class='alert-box'>⚠️ <b>{m}</b> ha superato il limite con {tot} ore!</div>", unsafe_allow_html=True)

    st.subheader("Tabella Turni")
    st.data_editor(st.session_state.db_turni[["Data", "Tipo", "Mattina", "Pomeriggio", "Notte"]], use_container_width=True, hide_index=True)
    
    st.subheader("📊 Riepilogo Ore Mensili")
    st.table(pd.DataFrame(stats))

    # --- 7. PDF ---
    def genera_pdf():
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=1*cm, bottomMargin=1*cm, leftMargin=1*cm, rightMargin=1*cm)
        elements = [Paragraph(f"<b>TURNI C.A. PORTO EMPEDOCLE - {mese_nome.upper()}</b>", getSampleStyleSheet()['Title']), Spacer(1, 10)]
        
        # Tabella Turni
        data = [["DATA", "TIPO", "MATTINA", "POMERIGGIO", "NOTTE"]]
        style = [('GRID', (0,0), (-1,-1), 0.5, colors.black), ('FONTSIZE', (0,0), (-1,-1), 8), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('BACKGROUND', (0,0), (-1,0), colors.cadetblue), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke)]
        
        for i, r in enumerate(st.session_state.db_turni.to_dict('records')):
            data.append([r['Data'], r["Tipo"], f"{r['Mattina']}\n{r['H_M']}", f"{r['Pomeriggio']}\n{r['H_P']}", f"{r['Notte']}\n{r['H_N']}"])
            if r["Tipo"] == "Festivo": style.append(('BACKGROUND', (0, i+1), (-1, i+1), colors.Color(1, 0.8, 0.8)))
            elif r["Tipo"] == "Prefestivo": style.append(('BACKGROUND', (0, i+1), (-1, i+1), colors.Color(1, 1, 0.85)))
        
        t1 = Table(data, colWidths=[2.2*cm, 2*cm, 4.8*cm, 4.8*cm, 4.8*cm])
        t1.setStyle(TableStyle(style))
        elements.append(t1)
        elements.append(Spacer(1, 15))
        
        # Tabella Statistiche
        elements.append(Paragraph("<b>RIEPILOGO ORE TOTALI</b>", getSampleStyleSheet()['Normal']))
        data_s = [["MEDICO", "ORE TOTALI"]]
        for s in stats: data_s.append([s['Medico'], str(s['Ore Totali'])])
        t2 = Table(data_s, colWidths=[5*cm, 4*cm])
        t2.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('BACKGROUND', (0,0), (-1,0), colors.lightgrey)]))
        elements.append(t2)
        
        doc.build(elements); return buf.getvalue()

    st.download_button("📥 SCARICA PDF COMPLETO", genera_pdf(), f"Turni_{mese_nome}.pdf", "application/pdf", use_container_width=True)
