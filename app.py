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
st.set_page_config(page_title="C.A. Porto Empedocle - Gestione Turni", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f7fafc; }
    .main-title { color: #2c5282; font-weight: 800; font-size: 2.2rem; text-align: center; margin-bottom: 20px; }
    .sidebar-header { color: #2b6cb0; font-weight: 700; border-bottom: 2px solid #bee3f8; padding-bottom: 5px; margin-bottom: 15px; }
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
    st.markdown("<div class='sidebar-header'>📅 SCORCIATOIE INDISPONIBILITÀ</div>", unsafe_allow_html=True)
    m_sel = st.selectbox("Seleziona Medico:", st.session_state.medici)
    
    cal_data = calendar.monthcalendar(anno_sel, m_idx_v)
    
    # Feriali
    st.write("**Giorni Feriali (Solo Notte):**")
    cols_fer = st.columns(5)
    g_feriali = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì"]
    for i, label in enumerate(g_feriali):
        if cols_fer[i].button(label):
            for sett in cal_data:
                d = sett[i]
                if d != 0:
                    curr = st.session_state.assenze[m_sel].get(d, [])
                    st.session_state.assenze[m_sel][d] = list(set(curr + ["N"])) if "N" not in curr else [f for f in curr if f != "N"]
            st.rerun()

    # Sabato
    st.write("**Sabato (Tutte le fasce):**")
    c_s1, c_s2, c_s3 = st.columns(3)
    if c_s1.button("Sabato Mattina"):
        for sett in cal_data:
            d = sett[5]; (d != 0 and st.session_state.assenze[m_sel].update({d: list(set(st.session_state.assenze[m_sel].get(d, []) + ["M"]))}))
        st.rerun()
    if c_s2.button("Sabato Pomeriggio"):
        for sett in cal_data:
            d = sett[5]; (d != 0 and st.session_state.assenze[m_sel].update({d: list(set(st.session_state.assenze[m_sel].get(d, []) + ["P"]))}))
        st.rerun()
    if c_s3.button("Sabato Notte"):
        for sett in cal_data:
            d = sett[5]; (d != 0 and st.session_state.assenze[m_sel].update({d: list(set(st.session_state.assenze[m_sel].get(d, []) + ["N"]))}))
        st.rerun()

    # Domenica
    st.write("**Domenica (Tutte le fasce):**")
    c_d1, c_d2, c_d3 = st.columns(3)
    if c_d1.button("Domenica Mattina"):
        for sett in cal_data:
            d = sett[6]; (d != 0 and st.session_state.assenze[m_sel].update({d: list(set(st.session_state.assenze[m_sel].get(d, []) + ["M"]))}))
        st.rerun()
    if c_d2.button("Domenica Pomeriggio"):
        for sett in cal_data:
            d = sett[6]; (d != 0 and st.session_state.assenze[m_sel].update({d: list(set(st.session_state.assenze[m_sel].get(d, []) + ["P"]))}))
        st.rerun()
    if c_d3.button("Domenica Notte"):
        for sett in cal_data:
            d = sett[6]; (d != 0 and st.session_state.assenze[m_sel].update({d: list(set(st.session_state.assenze[m_sel].get(d, []) + ["N"]))}))
        st.rerun()

    st.divider()
    # Calendario Puntuale
    st.write("**Calendario Manuale:**")
    for week in cal_data:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day != 0:
                curr_abs = st.session_state.assenze[m_sel].get(day, [])
                label = f"{day}\n{''.join(curr_abs)}" if curr_abs else f"{day}"
                if cols[i].button(label, key=f"cl_{day}", type="primary" if curr_abs else "secondary"):
                    st.session_state.assenze[m_sel][day] = ["M", "P", "N"] if not curr_abs else []
                    st.rerun()

    st.divider()
    # Gestione Dati
    if st.button("🗑️ SVUOTA TUTTE LE ASSENZE DEL MEDICO", type="secondary", use_container_width=True):
        st.session_state.assenze[m_sel] = {}
        st.rerun()

    backup_data = json.dumps({"medici": st.session_state.medici, "assenze": st.session_state.assenze}, indent=4)
    st.download_button("💾 SCARICA BACKUP DATI (JSON)", backup_data, f"backup_porto_empedocle_{mese_nome}.json", "application/json", use_container_width=True)

# --- 5. INTERFACCIA PRINCIPALE ---
st.markdown(f"<div class='main-title'>C.A. Porto Empedocle - {mese_nome} {anno_sel}</div>", unsafe_allow_html=True)

if st.button("🚀 GENERA TURNAZIONE", type="primary", use_container_width=True):
    fest = get_festivita(anno_sel)
    gg_m = calendar.monthrange(anno_sel, m_idx_v)[1]
    res = []
    u_n = None 
    g_it = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
    
    for d in range(1, gg_m + 1):
        dt = datetime(anno_sel, m_idx_v, d)
        tipo = "Festivo" if is_festivo(dt, fest) else ("Prefestivo" if is_prefestivo(dt, fest) else "Feriale")
        
        disp_m = [m for m in st.session_state.medici if "M" not in st.session_state.assenze[m].get(d, [])]
        disp_p = [m for m in st.session_state.medici if "P" not in st.session_state.assenze[m].get(d, [])]
        disp_n = [m for m in st.session_state.medici if "N" not in st.session_state.assenze[m].get(d, [])]

        cand_n = [m for m in disp_n if m != u_n] or disp_n
        n_m = random.choice(cand_n); u_n = n_m
        
        m_m, p_m_v, h_m, h_p, h_n = "---", "---", "---", "---", "---"
        
        if tipo in ["Festivo", "Prefestivo"]:
            h_m = "08:00 - 14:00" if tipo == "Festivo" else "10:00 - 14:00"
            h_p, h_n = "14:00 - 20:00", "20:00 - 08:00"
            m_m = random.choice([m for m in disp_m if m != n_m] or disp_m)
            p_m_v = random.choice([m for m in disp_p if m not in [n_m, m_m]] or disp_p)
        else:
            h_n = "20:00 - 08:00"

        res.append({"Data": f"{d} {g_it[dt.weekday()]}", "Tipo": tipo, "Mattina": m_m, "Pomeriggio": p_m_v, "Notte": n_m, "H_M": h_m, "H_P": h_p, "H_N": h_n})
    st.session_state.db_turni = pd.DataFrame(res)

if not st.session_state.db_turni.empty:
    st.data_editor(st.session_state.db_turni, use_container_width=True, hide_index=True)
    
    def genera_pdf():
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=0.5*cm, bottomMargin=0.5*cm, leftMargin=0.5*cm, rightMargin=0.5*cm)
        elements = [Paragraph(f"<b>C.A. Porto Empedocle - {mese_nome.upper()} {anno_sel}</b>", getSampleStyleSheet()['Title'])]
        data = [["DATA", "TIPO", "MATTINA", "POMERIGGIO", "NOTTE"]]
        for r in st.session_state.db_turni.to_dict('records'):
            data.append([r['Data'], r["Tipo"], f"{r['Mattina']}\n({r['H_M']})", f"{r['Pomeriggio']}\n({r['H_P']})", f"{r['Notte']}\n({r['H_N']})"])
        table = Table(data, colWidths=[2.8*cm, 2.2*cm, 4.8*cm, 4.8*cm, 4.8*cm])
        table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.black), ('FONTSIZE', (0,0), (-1,-1), 7), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('BACKGROUND', (0,0), (-1,0), colors.cadetblue), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke)]))
        elements.append(table); doc.build(elements); return buf.getvalue()

    st.download_button("📥 SCARICA TURNI IN PDF", genera_pdf(), f"Turni_CA_Porto_Empedocle_{mese_nome}.pdf", "application/pdf", use_container_width=True)
