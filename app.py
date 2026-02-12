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

# --- 1. DESIGN ---
st.set_page_config(page_title="Master Guardia Medica Pro", layout="wide")

st.markdown("""
    <style>
    .stApp {
        background-image: linear-gradient(rgba(255, 255, 255, 0.85), rgba(255, 255, 255, 0.85)), 
        url("https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?ixlib=rb-4.0.3&auto=format&fit=crop&w=1600&q=80");
        background-size: cover;
        background-attachment: fixed;
    }
    .main-title { color: #2c5282; font-weight: 800; font-size: 2.5rem; text-align: center; margin-bottom: 20px; }
    .settings-section { background-color: rgba(255, 255, 255, 0.95); padding: 15px; border-radius: 10px; border-left: 5px solid #4299e1; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 15px; }
    .sidebar-header { color: #2b6cb0; font-weight: 700; border-bottom: 2px solid #bee3f8; padding-bottom: 5px; margin-bottom: 10px; }
    div[data-baseweb="select"] *, div[data-baseweb="input"] * { color: #000000 !important; }
    [data-testid="stSidebar"] label p { color: #1a365d !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGICA TURNI E ORE ---
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
    mese_nome = st.selectbox("Mese:", mesi_ita, index=1)
    m_idx_v = mesi_ita.index(mese_nome) + 1
    
    st.divider()
    st.markdown("<div class='sidebar-header'>👨‍⚕️ STAFF</div>", unsafe_allow_html=True)
    nuovo_m = st.text_input("Aggiungi Medico:")
    if st.button("➕ AGGIUNGI"):
        if nuovo_m and nuovo_m not in st.session_state.medici:
            st.session_state.medici.append(nuovo_m); st.session_state.assenze[nuovo_m] = []; st.rerun()
    
    for med in st.session_state.medici:
        c_n, c_d = st.columns([4, 1])
        c_n.write(f"**{med}**")
        if c_d.button("🗑️", key=f"del_{med}"):
            st.session_state.medici.remove(med); st.rerun()

    st.divider()
    st.markdown("<div class='sidebar-header'>📅 ASSENZE</div>", unsafe_allow_html=True)
    m_sel = st.selectbox("Seleziona Medico:", st.session_state.medici)
    g_short = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
    cal_data = calendar.monthcalendar(anno_sel, m_idx_v)
    cols_sh = st.columns(7)
    for i, label in enumerate(g_short):
        if cols_sh[i].button(label, key=f"sh_{label}"):
            g_da_c = [sett[i] for sett in cal_data if sett[i] != 0]
            curr = st.session_state.assenze.get(m_sel, [])
            st.session_state.assenze[m_sel] = [d for d in curr if d not in g_da_c] if all(d in curr for d in g_da_c) else list(set(curr + g_da_c))
            st.rerun()

    for week in cal_data:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day != 0:
                is_abs = day in st.session_state.assenze.get(m_sel, [])
                if cols[i].button(str(day), key=f"d_{day}", type="primary" if is_abs else "secondary"):
                    if is_abs: st.session_state.assenze[m_sel].remove(day)
                    else: st.session_state.assenze[m_sel].append(day)
                    st.rerun()

    st.divider()
    st.download_button("📥 Scarica Backup", json.dumps({"medici": st.session_state.medici, "assenze": st.session_state.assenze}), f"backup_{mese_nome}.json", use_container_width=True)
    up = st.file_uploader("📤 Carica Backup", type="json")
    if up:
        data = json.load(up); st.session_state.medici, st.session_state.assenze = data["medici"], data["assenze"]; st.rerun()

# --- 5. INTERFACCIA PRINCIPALE ---
st.markdown(f"<div class='main-title'>Turni: {mese_nome} {anno_sel}</div>", unsafe_allow_html=True)

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
    for d in range(1, gg_m + 1):
        dt = datetime(anno_sel, m_idx_v, d)
        wd = dt.weekday()
        nome_f = festivita_anno.get((d, m_idx_v), "")
        tipo = "Festivo" if (wd == 6 or (d, m_idx_v) in fest) else ("Prefestivo" if (wd == 5 or (d==24 and m_idx_v==2)) else "Feriale")
        disp = [m for m in st.session_state.medici if d not in st.session_state.assenze.get(m, [])]
        if not disp: disp = st.session_state.medici
        cand = [m for m in disp if m != u_n] or disp
        
        m_m, p_m, n_m, h_m, h_p, h_n = "---", "---", "---", "---", "---", "---"
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
        res.append({"Data": f"{d} {g_short[wd]}", "Info": fest.get((d, m_idx_v), ""), "Tipo": tipo, "Mattina": m_m, "Pomeriggio": p_m, "Notte": n_m, "H_M": h_m, "H_P": h_p, "H_N": h_n})
    st.session_state.db_turni = pd.DataFrame(res)

# --- 6. RIEPILOGO E PDF ---
if not st.session_state.db_turni.empty:
    t1, t2 = st.tabs(["📝 MODIFICA & ORE", "👁️ ANTEPRIMA PDF"])
    with t1:
        st.session_state.db_turni = st.data_editor(st.session_state.db_turni, column_config={
            "Data": st.column_config.Column(disabled=True),
            "Info": st.column_config.Column("Festività", disabled=True),
            "Tipo": st.column_config.Column(disabled=True),
            "Mattina": st.column_config.SelectboxColumn(options=["---"] + st.session_state.medici),
            "Pomeriggio": st.column_config.SelectboxColumn(options=["---"] + st.session_state.medici),
            "Notte": st.column_config.SelectboxColumn(options=["---"] + st.session_state.medici),
            "H_M": None, "H_P": None, "H_N": None
        }, use_container_width=True, hide_index=True)
        
        ore_m = {m: 0.0 for m in st.session_state.medici}
        tot_mese = 0.0
        for _, r in st.session_state.db_turni.iterrows():
            d1, d2, d3 = calcola_durata(r["H_M"]), calcola_durata(r["H_P"]), calcola_durata(r["H_N"])
            tot_mese += (d1 + d2 + d3)
            if r["Mattina"] in ore_m: ore_m[r["Mattina"]] += d1
            if r["Pomeriggio"] in ore_m: ore_m[r["Pomeriggio"]] += d2
            if r["Notte"] in ore_m: ore_m[r["Notte"]] += d3
        
        st.markdown(f"### 📊 Ore Totali {mese_nome}: **{int(tot_mese)} h**")
        st.table(pd.DataFrame([{"Medico": m, f"Ore {mese_nome}": f"{int(h)} h"} for m, h in ore_m.items()]))

    with t2:
        st.dataframe(st.session_state.db_turni[["Data", "Info", "Tipo", "Mattina", "Pomeriggio", "Notte"]], use_container_width=True, hide_index=True)
        
        def genera_pdf():
            buf = io.BytesIO()
            doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=0.4*cm, bottomMargin=0.4*cm, leftMargin=0.4*cm, rightMargin=0.4*cm)
            elements = []
            styles = getSampleStyleSheet()
            elements.append(Paragraph(f"TURNI GUARDIA MEDICA - {mese_nome.upper()} {anno_sel}", styles['Title']))
            
            # Tabella Turni con Orari e Tipologia
            data = [["GIORNO", "TIPO", "MATTINA", "POMERIGGIO", "NOTTE"]]
            t_styles = [('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('ALIGN', (0,0), (-1,-1), 'CENTER'), 
                        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('FONTSIZE', (0,0), (-1,-1), 7), 
                        ('BACKGROUND', (0,0), (-1,0), colors.cadetblue), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke)]
            
            for i, r in enumerate(st.session_state.db_turni.to_dict('records')):
                row_idx = i + 1
                fest_str = f"\n({r['Info']})" if r['Info'] else ""
                data.append([
                    f"{r['Data']}{fest_str}", 
                    r["Tipo"],
                    f"{r['Mattina']}\n{r['H_M']}" if r['Mattina'] != "---" else "---",
                    f"{r['Pomeriggio']}\n{r['H_P']}" if r['Pomeriggio'] != "---" else "---",
                    f"{r['Notte']}\n{r['H_N']}" if r['Notte'] != "---" else "---"
                ])
                if r["Tipo"] == "Festivo": t_styles.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.lightpink))
                elif r["Tipo"] == "Prefestivo": t_styles.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.lightyellow))
            
            t = Table(data, colWidths=[3.2*cm, 2.5*cm, 4.8*cm, 4.8*cm, 4.8*cm])
            t.setStyle(TableStyle(t_styles))
            elements.append(t)
            
            # Riepilogo Ore
            elements.append(Spacer(1, 10))
            elements.append(Paragraph(f"RIEPILOGO ORE {mese_nome.upper()}", styles['Heading4']))
            data_ore = [[m, f"{int(h)} h"] for m, h in ore_m.items()]
            data_ore.append([f"TOTALE {mese_nome.upper()}", f"{int(tot_mese)} h"])
            t_ore = Table(data_ore, colWidths=[10*cm, 4*cm])
            t_ore.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('FONTSIZE', (0,0), (-1,-1), 8), ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold')]))
            elements.append(t_ore)
            
            doc.build(elements)
            return buf.getvalue()
            
        st.download_button(f"📥 SCARICA PDF COMPLETO {mese_nome.upper()}", genera_pdf(), f"Turni_{mese_nome}.pdf", "application/pdf", use_container_width=True, type="primary")
