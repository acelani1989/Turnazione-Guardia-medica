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

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="Master Guardia Medica - Porto Empedocle", layout="wide")

st.markdown("""
    <style>
    .main-title { color: #1a365d; font-family: 'Helvetica', sans-serif; font-weight: 700; font-size: 2.3rem; border-bottom: 3px solid #63b3ed; padding-bottom: 10px; margin-bottom: 25px; }
    .settings-section { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNZIONI UTILI ---
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
if 'medici' not in st.session_state: 
    st.session_state.medici = ["Piscopo", "Celani", "Lombardo", "Siracusa"]
if 'assenze' not in st.session_state: 
    st.session_state.assenze = {m: [] for m in st.session_state.medici}
if 'db_turni' not in st.session_state: 
    st.session_state.db_turni = pd.DataFrame()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown("## 📅 Periodo")
    anno_sel = st.number_input("Anno:", min_value=2024, max_value=2030, value=2026)
    mesi_ita = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
    mese_nome = st.selectbox("Mese:", mesi_ita, index=1)
    m_idx_v = mesi_ita.index(mese_nome) + 1

    st.divider()
    st.markdown("## 👨‍⚕️ Staff")
    nuovo_m = st.text_input("Aggiungi Medico:")
    if st.button("AGGIUNGI"):
        if nuovo_m and nuovo_m not in st.session_state.medici:
            st.session_state.medici.append(nuovo_m)
            st.session_state.assenze[nuovo_m] = []
            st.rerun()

    for med in st.session_state.medici:
        c_n, c_d = st.columns([4, 1])
        c_n.write(f"**{med}**")
        if c_d.button("X", key=f"del_{med}"):
            st.session_state.medici.remove(med)
            st.rerun()
    
    st.divider()
    st.markdown("### 📅 Indisponibilità")
    m_sel = st.selectbox("Seleziona Medico:", st.session_state.medici)
    
    st.write("Segna tutti i:")
    giorni_sett = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
    cols_scor = st.columns(4)
    for i, g_nome in enumerate(giorni_sett):
        if cols_scor[i % 4].button(g_nome, key=f"btn_{g_nome}"):
            for d in range(1, 32):
                try:
                    if datetime(anno_sel, m_idx_v, d).weekday() == i:
                        if d not in st.session_state.assenze[m_sel]: st.session_state.assenze[m_sel].append(d)
                except: pass
            st.rerun()
    
    st.write("Seleziona date singole:")
    cal = calendar.monthcalendar(anno_sel, m_idx_v)
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day != 0:
                is_abs = day in st.session_state.assenze.get(m_sel, [])
                if cols[i].button(str(day), key=f"d_btn_{day}", type="primary" if is_abs else "secondary"):
                    if is_abs: st.session_state.assenze[m_sel].remove(day)
                    else: st.session_state.assenze[m_sel].append(day)
                    st.rerun()
    
    if st.button("🧹 Svuota Assenze " + m_sel, use_container_width=True):
        st.session_state.assenze[m_sel] = []
        st.rerun()

# --- 5. DASHBOARD ORARI ---
st.markdown(f"<div class='main-title'>Gestione Turni: {mese_nome} {anno_sel}</div>", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("<div class='settings-section'><b>🏠 FERIALI</b>", unsafe_allow_html=True)
    f_n = st.text_input("Notte", value="20:00 - 08:00", key="k_fer_n")
    st.markdown("</div>", unsafe_allow_html=True)
with col2:
    st.markdown("<div class='settings-section'><b>🕒 PREFESTIVI</b>", unsafe_allow_html=True)
    p_p = st.text_input("Pomeriggio", value="10:00 - 20:00", key="k_pre_p")
    p_n = st.text_input("Notte", value="20:00 - 08:00", key="k_pre_n")
    st.markdown("</div>", unsafe_allow_html=True)
with col3:
    st.markdown("<div class='settings-section'><b>🚩 FESTIVI</b>", unsafe_allow_html=True)
    div_f = st.toggle("Dividi Mattina", value=True)
    fes_m = st.text_input("Mattina", value="08:00 - 14:00", key="k_fes_m")
    fes_p = st.text_input("Pomeriggio", value="14:00 - 20:00", key="k_fes_p")
    fes_n = st.text_input("Notte", value="20:00 - 08:00", key="k_fes_n")
    st.markdown("</div>", unsafe_allow_html=True)

# --- 6. LOGICA GENERAZIONE ---
st.divider()
if st.button("🚀 GENERA PIANO TURNI", type="primary", use_container_width=True):
    gg_m = calendar.monthrange(anno_sel, m_idx_v)[1]
    data_list = []
    ultimo_notte = None 

    for d in range(1, gg_m + 1):
        dt = datetime(anno_sel, m_idx_v, d)
        wd = dt.weekday()
        tipo = "Feriale"
        if wd == 5: tipo = "Prefestivo"
        if wd == 6: tipo = "Festivo"
        
        disp_oggi = [m for m in st.session_state.medici if d not in st.session_state.assenze.get(m, [])]
        if not disp_oggi: disp_oggi = st.session_state.medici # Fallback se tutti sono assenti
        
        disp_notte = [m for m in disp_oggi if m != ultimo_notte]
        if not disp_notte: disp_notte = disp_oggi

        if tipo == "Festivo":
            m_mat_list = random.sample(disp_oggi, min(2, len(disp_oggi))) if div_f else [random.choice(disp_oggi)]
            mat_txt = " / ".join(m_mat_list)
            rest_p = [m for m in disp_oggi if m not in m_mat_list]
            pom_m = random.choice(rest_p) if rest_p else random.choice(disp_oggi)
            rest_n = [m for m in disp_notte if m != pom_m and m not in m_mat_list]
            not_m = random.choice(rest_n) if rest_n else random.choice(disp_notte)
            h_m, h_p, h_n = fes_m, fes_p, fes_n
        elif tipo == "Prefestivo":
            mat_txt, h_m = "---", "---"
            pom_m = random.choice(disp_oggi)
            rest_n = [m for m in disp_notte if m != pom_m]
            not_m = random.choice(rest_n) if rest_n else random.choice(disp_notte)
            h_p, h_n = p_p, p_n
        else:
            mat_txt, h_m = "---", "---"
            pom_m, h_p = "---", "---"
            not_m = random.choice(disp_notte)
            h_n = f_n

        ultimo_notte = not_m
        data_list.append({
            "Data": f"{d} {giorni_sett[wd]}", "Tipo": tipo, 
            "Mattina": mat_txt, "Pomeriggio": pom_m, "Notte": not_m,
            "H_M": h_m, "H_P": h_p, "H_N": h_n
        })
    st.session_state.db_turni = pd.DataFrame(data_list)

# --- 7. TABELLONE E RIEPILOGO ORE ---
if not st.session_state.db_turni.empty:
    st.markdown("### 📅 Tabellone Risultante")
    lista_opzioni = ["---"] + st.session_state.medici
    
    edited_db = st.data_editor(
        st.session_state.db_turni,
        column_config={
            "Data": st.column_config.Column("Giorno", width="small", disabled=True),
            "Mattina": st.column_config.SelectboxColumn("☀️ Mattina", options=lista_opzioni),
            "Pomeriggio": st.column_config.SelectboxColumn("🌤️ Pomeriggio", options=lista_opzioni),
            "Notte": st.column_config.SelectboxColumn("🌙 Notte", options=lista_opzioni),
            "Tipo": None, "H_M": None, "H_P": None, "H_N": None,
        },
        use_container_width=True,
        hide_index=True,
        key="main_table_editor"
    )
    
    st.session_state.db_turni = edited_db
    st.divider()
    
    col_rec, col_down = st.columns([2, 1])
    with col_rec:
        st.markdown("#### 📊 Riepilogo Ore Mensili")
        ore_calc = {m: 0.0 for m in st.session_state.medici}
        for _, r in st.session_state.db_turni.iterrows():
            if r["Pomeriggio"] in ore_calc: ore_calc[r["Pomeriggio"]] += calcola_durata(r["H_P"])
            if r["Notte"] in ore_calc: ore_calc[r["Notte"]] += calcola_durata(r["H_N"])
            if "/" in str(r["Mattina"]):
                for p in r["Mattina"].split("/"):
                    p_c = p.strip()
                    if p_c in ore_calc: ore_calc[p_c] += (calcola_durata(r["H_M"]) / 2)
            elif r["Mattina"] in ore_calc:
                ore_calc[r["Mattina"]] += calcola_durata(r["H_M"])

        df_ore = pd.DataFrame([{"Medico": m, "Ore Totali": f"{h:.1f}"} for m, h in ore_calc.items()])
        st.dataframe(df_ore, use_container_width=True, hide_index=True)

    with col_down:
        st.markdown("#### 📥 Esportazione")
        def genera_pdf():
            buf = io.BytesIO()
            doc = SimpleDocTemplate(buf, pagesize=landscape(A4))
            elements = [Paragraph(f"TURNI {mese_nome.upper()} {anno_sel}", getSampleStyleSheet()['Title']), Spacer(1, 15)]
            data_pdf = [["DATA", "TIPO", "MATTINA", "POMERIGGIO", "NOTTE"]]
            for _, r in st.session_state.db_turni.iterrows():
                data_pdf.append([r["Data"], r["Tipo"], r["Mattina"], r["Pomeriggio"], r["Notte"]])
            t = Table(data_pdf, colWidths=[80, 70, 180, 180, 180])
            t.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('BACKGROUND', (0,0), (-1,0), colors.cadetblue), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke), ('ALIGN', (0,0), (-1,-1), 'CENTER')]))
            elements.append(t)
            doc.build(elements)
            return buf.getvalue()

        st.download_button("SCARICA PDF", data=genera_pdf(), file_name=f"Turni_{mese_nome}.pdf", use_container_width=True)
