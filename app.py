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
    .total-box { padding: 15px; background-color: #e2e8f0; border-radius: 10px; text-align: center; font-weight: bold; font-size: 1.1rem; color: #2d3748; margin-top: 10px; border: 1px solid #cbd5e0; }
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

def is_festivo(dt, fest): 
    return (dt.day, dt.month) in fest or dt.weekday() == 6

def is_prefestivo(dt, fest): 
    return dt.weekday() == 5 or is_festivo(dt + timedelta(days=1), fest)

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
    st.markdown("<div class='sidebar-header'>📅 INDISPONIBILITÀ</div>", unsafe_allow_html=True)
    m_sel = st.selectbox("Seleziona Medico:", st.session_state.medici)
    cal_data = calendar.monthcalendar(anno_sel, m_idx_v)
    
    st.write("**Scorciatoie Feriali (Solo Notte):**")
    cols_f = st.columns(5)
    for i, l in enumerate(["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì"]):
        if cols_f[i].button(l):
            for s in cal_data:
                if s[i] != 0: 
                    d_str = str(s[i])
                    st.session_state.assenze[m_sel][d_str] = list(set(st.session_state.assenze[m_sel].get(d_str, []) + ["N"]))
            st.rerun()

    st.write("**Scorciatoie Sabati:**")
    c_sab = st.columns(3)
    fasce = ["Mattina", "Pomeriggio", "Notte"]
    fasce_cod = ["M", "P", "N"]
    for i in range(3):
        if c_sab[i].button(f"Sabato {fasce[i]}"):
            for s in cal_data:
                if s[5] != 0: 
                    d = str(s[5])
                    st.session_state.assenze[m_sel][d] = list(set(st.session_state.assenze[m_sel].get(d, []) + [fasce_cod[i]]))
            st.rerun()

    st.write("**Scorciatoie Domeniche:**")
    c_dom = st.columns(3)
    for i in range(3):
        if c_dom[i].button(f"Domenica {fasce[i]}"):
            for s in cal_data:
                if s[6] != 0: 
                    d = str(s[6])
                    st.session_state.assenze[m_sel][d] = list(set(st.session_state.assenze[m_sel].get(d, []) + [fasce_cod[i]]))
            st.rerun()

    st.write("**Calendario Manuale (Intera Giornata):**")
    for week in cal_data:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day != 0:
                d_str = str(day)
                curr_abs = st.session_state.assenze[m_sel].get(d_str, [])
                label = f"{day}\n{''.join(curr_abs)}" if curr_abs else f"{day}"
                if cols[i].button(label, key=f"btn_{day}", type="primary" if curr_abs else "secondary"):
                    st.session_state.assenze[m_sel][d_str] = ["M", "P", "N"] if not curr_abs else []
                    st.rerun()

    st.divider()
    if st.button("🗑️ SVUOTA ASSENZE MEDICO", use_container_width=True):
        st.session_state.assenze[m_sel] = {}; st.rerun()
    
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
        nome_fest = fest.get((dt.day, dt.month))
        tipo = nome_fest if nome_fest else ("Domenica" if dt.weekday() == 6 else ("Prefestivo" if is_prefestivo(dt, fest) else "Feriale"))
        tipo_label = "Festivo" if (nome_fest or dt.weekday() == 6) else ("Prefestivo" if is_prefestivo(dt, fest) else "Feriale")

        d_str = str(d)
        h_m, h_p, h_n = "---", "---", "20:00 - 08:00"
        o_m, o_p, o_n = 0, 0, 12
        if tipo_label == "Festivo": h_m, h_p = "08:00 - 14:00", "14:00 - 20:00"; o_m, o_p = 6, 6
        elif tipo_label == "Prefestivo": h_m, h_p = "10:00 - 14:00", "14:00 - 20:00"; o_m, o_p = 4, 6

        disp_m = [m for m in st.session_state.medici if "M" not in st.session_state.assenze[m].get(d_str, [])]
        disp_p = [m for m in st.session_state.medici if "P" not in st.session_state.assenze[m].get(d_str, [])]
        disp_n = [m for m in st.session_state.medici if "N" not in st.session_state.assenze[m].get(d_str, [])]

        n_m = random.choice([m for m in disp_n if m != u_n] or disp_n)
        u_n = n_m
        m_m = random.choice([m for m in disp_m if m != n_m] or disp_m) if o_m > 0 else "---"
        p_m = random.choice([m for m in disp_p if m not in [n_m, m_m]] or disp_p) if o_p > 0 else "---"

        res.append({
            "Data": f"{d} {['LUN','MAR','MER','GIO','VEN','SAB','DOM'][dt.weekday()]}", 
            "Tipo": tipo, "Label": tipo_label, "Mattina": m_m, "Pomeriggio": p_m, "Notte": n_m, 
            "OreM": o_m, "OreP": o_p, "OreN": o_n, "H_M": h_m, "H_P": h_p, "H_N": h_n
        })
    st.session_state.db_turni = pd.DataFrame(res)

# --- 6. VISUALIZZAZIONE E EDITING ---
if not st.session_state.db_turni.empty:
    # Qui abilitiamo la selezione manuale dei medici tramite data_editor
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("📅 Turni (Modificabili)")
        # Configuriamo le colonne come menu a tendina
        lista_medici_tendina = st.session_state.medici + ["---"]
        edited_df = st.data_editor(
            st.session_state.db_turni,
            column_order=("Data", "Tipo", "Mattina", "Pomeriggio", "Notte"),
            column_config={
                "Mattina": st.column_config.SelectboxColumn("Mattina", options=lista_medici_tendina),
                "Pomeriggio": st.column_config.SelectboxColumn("Pomeriggio", options=lista_medici_tendina),
                "Notte": st.column_config.SelectboxColumn("Notte", options=lista_medici_tendina),
                "Data": st.column_config.TextColumn("Data", disabled=True),
                "Tipo": st.column_config.TextColumn("Tipo", disabled=True),
            },
            use_container_width=True,
            hide_index=True,
            key="editor_turni"
        )
        # Aggiorniamo il db in session state con le modifiche manuali
        st.session_state.db_turni = edited_df

    with c2:
        st.subheader("📊 Riepilogo Ore")
        df = st.session_state.db_turni
        stats_data = []
        somma_ore_medici = 0
        ore_teoriche_mese = df['OreM'].sum() + df['OreP'].sum() + df['OreN'].sum()

        for m in st.session_state.medici:
            t_m = df[df['Mattina'] == m]['OreM'].sum()
            t_p = df[df['Pomeriggio'] == m]['OreP'].sum()
            t_n = df[df['Notte'] == m]['OreN'].sum()
            totale = t_m + t_p + t_n
            stats_data.append({"Medico": m, "Ore Totali": totale})
            somma_ore_medici += totale
            if totale > ore_max: 
                st.markdown(f"<div class='alert-box'>⚠️ <b>{m}</b>: {totale} ore</div>", unsafe_allow_html=True)

        st.table(pd.DataFrame(stats_data))
        st.markdown(f"<div class='total-box'>SOMMA ORE MEDICI: {somma_ore_medici}<br>SOMMA ORE MESE: {ore_teoriche_mese}</div>", unsafe_allow_html=True)

    # --- 7. PDF GENERATION ---
    def genera_pdf(stats_list, s_medici, s_mese):
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=0.4*cm, bottomMargin=0.4*cm, leftMargin=0.4*cm, rightMargin=0.4*cm)
        elements = []
        styles = getSampleStyleSheet()
        elements.append(Paragraph(f"<b>GUARDIA MEDICA PORTO EMPEDOCLE - {mese_nome.upper()} {anno_sel}</b>", styles['Title']))
        elements.append(Spacer(1, 4))
        
        data_t = [["DATA", "TIPO", "MATTINA", "POMERIGGIO", "NOTTE"]]
        ts_t = [
            ('GRID', (0,0), (-1,-1), 0.5, colors.black), ('FONTSIZE', (0,0), (-1,-1), 7),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,0), (-1,0), colors.cadetblue), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('TOPPADDING', (0,0), (-1,-1), 1), ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ]
        
        rows = st.session_state.db_turni.to_dict('records')
        for i, r in enumerate(rows):
            m_txt = f"{r['Mattina']} ({r['H_M']})" if r['Mattina'] not in ["---", None] else "---"
            p_txt = f"{r['Pomeriggio']} ({r['H_P']})" if r['Pomeriggio'] not in ["---", None] else "---"
            data_t.append([r['Data'], str(r['Tipo'])[:10], m_txt, p_txt, f"{r['Notte']} (20-08)"])
            label = r.get("Label", "")
            if label == "Festivo": ts_t.append(('BACKGROUND', (0, i+1), (-1, i+1), colors.Color(1, 0.88, 0.88)))
            elif label == "Prefestivo": ts_t.append(('BACKGROUND', (0, i+1), (-1, i+1), colors.Color(1, 1, 0.9)))
            
        table_turni = Table(data_t, colWidths=[2.1*cm, 2.3*cm, 5.2*cm, 5.2*cm, 5.2*cm])
        table_turni.setStyle(TableStyle(ts_t))
        elements.append(table_turni)
        elements.append(Spacer(1, 6))
        
        elements.append(Paragraph("<b>RIEPILOGO ORE</b>", styles['Normal']))
        data_r = [["MEDICO", "ORE TOTALI"]]
        for s in stats_list: data_r.append([s['Medico'], str(s['Ore Totali'])])
        data_r.append([f"TOTALE MEDICI: {s_medici}", f"TOTALE MESE: {s_mese}"])
        
        table_riepilogo = Table(data_r, colWidths=[10*cm, 10*cm])
        table_riepilogo.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('FONTSIZE', (0,0), (-1,-1), 8),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('BACKGROUND', (0, -1), (-1, -1), colors.whitesmoke), ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold')
        ]))
        elements.append(table_riepilogo)
        doc.build(elements)
        return buf.getvalue()

    st.download_button("📥 SCARICA PDF (PAGINA SINGOLA)", genera_pdf(stats_data, somma_ore_medici, ore_teoriche_mese), f"Turni_{mese_nome}.pdf", "application/pdf", use_container_width=True)
