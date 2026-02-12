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

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="Master Guardia Medica", layout="wide")

st.markdown("""
    <style>
    .main-title { color: #1a365d; font-family: 'Helvetica', sans-serif; font-weight: 700; font-size: 2.3rem; border-bottom: 3px solid #63b3ed; padding-bottom: 10px; margin-bottom: 25px; }
    .settings-section { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .sidebar-header { color: #2c5282; font-weight: 700; margin-top: 10px; border-bottom: 1px solid #eee; padding-bottom: 5px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNZIONI UTILI ---
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
    return {
        (1, 1): "Capodanno", (6, 1): "Epifania", (25, 4): "Liberazione", (1, 5): "Festa Lavoro", 
        (2, 6): "Festa Repubblica", (15, 8): "Ferragosto", (1, 11): "Ognissanti", 
        (8, 12): "Immacolata", (25, 12): "Natale", (26, 12): "S. Stefano",
        (dt_p.day, dt_p.month): "Pasqua", (dt_pp.day, dt_pp.month): "Pasquetta", (25, 2): "S. Patrono"
    }

def calcola_durata(intervallo):
    try:
        if "---" in str(intervallo) or not intervallo: return 0
        parti = intervallo.split("-")
        inizio = datetime.strptime(parti[0].strip(), "%H:%M")
        fine = datetime.strptime(parti[1].strip(), "%H:%M")
        durata = (fine - inizio).seconds / 3600
        if durata <= 0: durata += 24 
        return durata
    except: return 0

# --- 3. STATO SESSIONE ---
if 'medici' not in st.session_state: st.session_state.medici = ["Piscopo", "Celani", "Lombardo", "Siracusa"]
if 'assenze' not in st.session_state: st.session_state.assenze = {m: [] for m in st.session_state.medici}
if 'db_turni' not in st.session_state: st.session_state.db_turni = pd.DataFrame()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown("<div class='sidebar-header'>📅 CONFIGURA PERIODO</div>", unsafe_allow_html=True)
    anno_sel = st.number_input("Anno:", min_value=2024, max_value=2030, value=2026)
    mesi_ita = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
    mese_nome = st.selectbox("Mese:", mesi_ita, index=1)
    m_idx_v = mesi_ita.index(mese_nome) + 1
    festivita_anno = get_festivita(anno_sel)
    
    st.divider()
    st.markdown("<div class='sidebar-header'>👨‍⚕️ GESTIONE STAFF</div>", unsafe_allow_html=True)
    nuovo_m = st.text_input("Nome Medico:")
    if st.button("AGGIUNGI MEDICO"):
        if nuovo_m and nuovo_m not in st.session_state.medici:
            st.session_state.medici.append(nuovo_m)
            st.session_state.assenze[nuovo_m] = []
            st.rerun()
    
    for med in st.session_state.medici:
        c_n, c_d = st.columns([4, 1])
        c_n.write(f"**{med}**")
        if c_d.button("X", key=f"del_{med}"):
            st.session_state.medici.remove(med)
            if med in st.session_state.assenze: del st.session_state.assenze[med]
            st.rerun()
    
    st.divider()
    st.markdown("<div class='sidebar-header'>📅 INDISPONIBILITÀ</div>", unsafe_allow_html=True)
    m_sel = st.selectbox("Seleziona Medico:", st.session_state.medici)
    
    g_short = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
    cols_sh = st.columns(7)
    cal_data = calendar.monthcalendar(anno_sel, m_idx_v)
    for i, label in enumerate(g_short):
        if cols_sh[i].button(label, key=f"sh_{label}"):
            giorni_da_cambiare = [sett[i] for sett in cal_data if sett[i] != 0]
            current_abs = st.session_state.assenze.get(m_sel, [])
            if all(d in current_abs for d in giorni_da_cambiare):
                st.session_state.assenze[m_sel] = [d for d in current_abs if d not in giorni_da_cambiare]
            else:
                for d in giorni_da_cambiare:
                    if d not in current_abs: st.session_state.assenze[m_sel].append(d)
            st.rerun()

    for week in cal_data:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day != 0:
                is_abs = day in st.session_state.assenze.get(m_sel, [])
                if cols[i].button(str(day), key=f"d_btn_{day}", type="primary" if is_abs else "secondary"):
                    if is_abs: st.session_state.assenze[m_sel].remove(day)
                    else: st.session_state.assenze[m_sel].append(day)
                    st.rerun()

    st.markdown("<br><br><br>", unsafe_allow_html=True)
    data_to_export = {"medici": st.session_state.medici, "assenze": st.session_state.assenze}
    st.download_button(label="📥 Scarica Backup", data=json.dumps(data_to_export, indent=4), file_name=f"backup_guardia_{datetime.now().strftime('%Y%m%d')}.json", mime="application/json", use_container_width=True)

# --- 5. INTERFACCIA PRINCIPALE ---
st.markdown(f"<div class='main-title'>Gestione Turni: {mese_nome} {anno_sel}</div>", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("<div class='settings-section'><b>🏠 FERIALI</b>", unsafe_allow_html=True)
    f_n = st.text_input("Notte", value="20:00 - 08:00")
with col2:
    st.markdown("<div class='settings-section'><b>🕒 PREFESTIVI</b>", unsafe_allow_html=True)
    p_p = st.text_input("Pomeriggio", value="10:00 - 20:00", key="kp_p")
    p_n = st.text_input("Notte", value="20:00 - 08:00", key="kp_n")
with col3:
    st.markdown("<div class='settings-section'><b>🚩 FESTIVI</b>", unsafe_allow_html=True)
    fes_m = st.text_input("Mattina", value="08:00 - 14:00", key="kf_m")
    fes_p = st.text_input("Pomeriggio", value="14:00 - 20:00", key="kf_p")
    fes_n = st.text_input("Notte", value="20:00 - 08:00", key="kf_n")

# --- 6. GENERAZIONE ---
st.divider()
if st.button("🚀 GENERA / RIGENERA TURNI", type="primary", use_container_width=True):
    gg_m = calendar.monthrange(anno_sel, m_idx_v)[1]
    data_list = []
    ultimo_notte = None 
    giorni_sett = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]

    for d in range(1, gg_m + 1):
        dt = datetime(anno_sel, m_idx_v, d)
        wd = dt.weekday()
        is_festivo_nazionale = (d, m_idx_v) in festivita_anno
        tipo = "Feriale"
        if wd == 5 or (d == 24 and m_idx_v == 2): tipo = "Prefestivo"
        if wd == 6 or is_festivo_nazionale: tipo = "Festivo"
        
        nome_fest = f" ({festivita_anno[(d, m_idx_v)]})" if is_festivo_nazionale else ""
        disp_oggi = [m for m in st.session_state.medici if d not in st.session_state.assenze.get(m, [])]
        if not disp_oggi: disp_oggi = st.session_state.medici
        
        disp_senza_smonto = [m for m in disp_oggi if m != ultimo_notte]
        if not disp_senza_smonto: disp_senza_smonto = disp_oggi

        if tipo == "Festivo":
            mat_m = random.choice(disp_senza_smonto)
            rest_p = [m for m in disp_oggi if m != mat_m]
            pom_m = random.choice(rest_p) if rest_p else random.choice(disp_oggi)
            rest_n = [m for m in disp_senza_smonto if m != pom_m and m != mat_m]
            not_m = random.choice(rest_n) if rest_n else random.choice([m for m in disp_senza_smonto if m != pom_m])
            h_m, h_p, h_n = fes_m, fes_p, fes_n
        elif tipo == "Prefestivo":
            mat_m, h_m = "---", "---"
            pom_m = random.choice(disp_senza_smonto)
            rest_n = [m for m in disp_senza_smonto if m != pom_m]
            not_m = random.choice(rest_n) if rest_n else random.choice(disp_senza_smonto)
            h_p, h_n = p_p, p_n
        else:
            mat_m, h_m, pom_m, h_p = "---", "---", "---", "---"
            not_m, h_n = random.choice(disp_senza_smonto), f_n

        ultimo_notte = not_m
        data_list.append({"Data": f"{d} {giorni_sett[wd]}{nome_fest}", "Tipo": tipo, "Mattina": mat_m, "Pomeriggio": pom_m, "Notte": not_m, "H_M": h_m, "H_P": h_p, "H_N": h_n})
    st.session_state.db_turni = pd.DataFrame(data_list)

# --- 7. TAB E ANTEPRIMA ---
if not st.session_state.db_turni.empty:
    tab1, tab2 = st.tabs(["📝 Modifica Dati & Ore", "👁️ Anteprima Grafica PDF"])
    
    with tab1:
        st.subheader("Correzione Manuale Turni")
        lista_opzioni = ["---"] + st.session_state.medici
        st.session_state.db_turni = st.data_editor(st.session_state.db_turni, column_config={
            "Data": st.column_config.Column("Giorno", disabled=True),
            "Mattina": st.column_config.SelectboxColumn("☀️ Mattina", options=lista_opzioni),
            "Pomeriggio": st.column_config.SelectboxColumn("🌤️ Pomeriggio", options=lista_opzioni),
            "Notte": st.column_config.SelectboxColumn("🌙 Notte", options=lista_opzioni),
            "Tipo": None, "H_M": None, "H_P": None, "H_N": None,
        }, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("📊 Riepilogo Ore Mensili")
        ore_calc = {m: 0.0 for m in st.session_state.medici}
        ore_totali_mese_teoriche = 0.0
        for _, r in st.session_state.db_turni.iterrows():
            d_m, d_p, d_n = calcola_durata(r["H_M"]), calcola_durata(r["H_P"]), calcola_durata(r["H_N"])
            ore_totali_mese_teoriche += (d_m + d_p + d_n)
            if r["Mattina"] in ore_calc: ore_calc[r["Mattina"]] += d_m
            if r["Pomeriggio"] in ore_calc: ore_calc[r["Pomeriggio"]] += d_p
            if r["Notte"] in ore_calc: ore_calc[r["Notte"]] += d_n
        
        df_ore = pd.DataFrame([{"Medico": m, "Ore Totali": int(round(h, 0))} for m, h in ore_calc.items()])
        st.table(df_ore)
        st.markdown(f"**TOTALE ORE PREVISTE DA {mese_nome.upper()}: {int(round(ore_totali_mese_teoriche, 0))} ore**")

    with tab2:
        def genera_pdf():
            buf = io.BytesIO()
            doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=0.3*cm, bottomMargin=0.3*cm, leftMargin=0.4*cm, rightMargin=0.4*cm)
            styles = getSampleStyleSheet()
            title_style = styles['Title']
            title_style.fontSize = 14
            title_style.spaceAfter = 6
            elements = []
            elements.append(Paragraph(f"TURNI GUARDIA MEDICA - {mese_nome.upper()} {anno_sel}", title_style))
            
            data_pdf = [["GIORNO", "MATTINA", "POMERIGGIO", "NOTTE"]]
            t_styles = [
                ('GRID', (0,0), (-1,-1), 0.2, colors.grey),
                ('FONTSIZE', (0,0), (-1,-1), 7.5),
                ('LEADING', (0,0), (-1,-1), 8.5),
                ('BACKGROUND', (0,0), (-1,0), colors.cadetblue),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 1),
                ('TOPPADDING', (0,0), (-1,-1), 1),
            ]
            
            ore_teoriche_pdf = 0.0
            ore_medici_pdf = {m: 0.0 for m in st.session_state.medici}
            
            for i, r in enumerate(st.session_state.db_turni.to_dict('records')):
                row_idx = i + 1
                data_pdf.append([
                    r["Data"], 
                    f"{r['Mattina']}\n({r['H_M']})" if r['Mattina'] != "---" else "---",
                    f"{r['Pomeriggio']}\n({r['H_P']})" if r['Pomeriggio'] != "---" else "---",
                    f"{r['Notte']}\n({r['H_N']})" if r['Notte'] != "---" else "---"
                ])
                
                d_m, d_p, d_n = calcola_durata(r["H_M"]), calcola_durata(r["H_P"]), calcola_durata(r["H_N"])
                ore_teoriche_pdf += (d_m + d_p + d_n)
                if r["Mattina"] in ore_medici_pdf: ore_medici_pdf[r["Mattina"]] += d_m
                if r["Pomeriggio"] in ore_medici_pdf: ore_medici_pdf[r["Pomeriggio"]] += d_p
                if r["Notte"] in ore_medici_pdf: ore_medici_pdf[r["Notte"]] += d_n

                if r["Tipo"] == "Festivo": t_styles.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.lightpink))
                elif r["Tipo"] == "Prefestivo": t_styles.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.lightyellow))
            
            t_turni = Table(data_pdf, colWidths=[3.2*cm, 5.6*cm, 5.6*cm, 5.6*cm])
            t_turni.setStyle(TableStyle(t_styles))
            elements.append(t_turni)
            elements.append(Spacer(1, 8))
            
            h_style = styles['Heading3']
            h_style.fontSize = 10
            h_style.spaceAfter = 4
            elements.append(Paragraph("RIEPILOGO ORE MENSILI", h_style))
            
            data_ore = [["MEDICO", "ORE TOTALI"]]
            for m, h in ore_medici_pdf.items():
                data_ore.append([m, f"{int(round(h, 0))} h"])
            
            data_ore.append([f"TOTALE ORE PREVISTE DA {mese_nome.upper()}", f"{int(round(ore_teoriche_pdf, 0))} h"])
            
            t_ore = Table(data_ore, colWidths=[10*cm, 4*cm])
            t_ore.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.2, colors.grey),
                ('FONTSIZE', (0,0), (-1,-1), 8),
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('ALIGN', (1,0), (1,-1), 'CENTER'),
                ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                ('TOPPADDING', (0,0), (-1,-1), 2),
            ]))
            elements.append(t_ore)
            
            doc.build(elements)
            return buf.getvalue()
        
        st.download_button("📥 SCARICA PDF (SINGOLA PAGINA)", data=genera_pdf(), file_name=f"Turni_{mese_nome}_{anno_sel}.pdf", use_container_width=True, type="primary")
