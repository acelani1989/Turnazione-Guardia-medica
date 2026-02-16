import streamlit as st
import pandas as pd
import calendar
import io
from datetime import datetime, timedelta
from fpdf import FPDF

# --- 1. FUNZIONE FESTIVITÀ ITALIANE ---
def get_festivita(anno):
    def pasqua(y):
        a, b, c = y % 19, y // 100, y % 100
        d, e = b // 4, b % 4
        f, g = (b + 8) // 25, (b - (b + 8) // 25 + 1) // 3
        h = (19 * a + b - d - g + 15) % 30
        i, k = c // 4, c % 4
        l = (32 + 2 * e + 2 * i - h - k) % 7
        m = (a + 11 * h + 22 * l) // 451
        mese = (h + l - 7 * m + 114) // 31
        giorno = ((h + l - 7 * m + 114) % 31) + 1
        return datetime(y, mese, giorno)
    
    p = pasqua(anno)
    pp = p + timedelta(days=1)
    return {
        (1, 1): "Capodanno", (6, 1): "Epifania", (25, 2): "Patrono",
        (25, 4): "Liberazione", (1, 5): "Lavoro", (2, 6): "Repubblica",
        (15, 8): "Ferragosto", (1, 11): "Ognissanti", (8, 12): "Immacolata",
        (25, 12): "Natale", (26, 12): "S.Stefano",
        (p.day, p.month): "Pasqua", (pp.day, pp.month): "Pasquetta"
    }

# --- 2. SETUP E STILE ---
st.set_page_config(page_title="Turni PCA Porto Empedocle", layout="wide")

st.markdown("""
    <style>
    div.stButton > button:first-child {
        background-color: #ff4b4b !important;
        color: white !important;
        font-weight: bold !important;
    }
    footer {visibility: hidden;}
    [data-testid="stElementToolbar"] {display: none;}
    .st-emotion-cache-1ghh6y0, .st-emotion-cache-1wivap2 { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("### PRESIDIO DI CONTINUITA’ ASSISTENZIALE PORTO EMPEDOCLE")

if 'db' not in st.session_state:
    st.session_state.db = None
if 'medici_lista' not in st.session_state:
    st.session_state.medici_lista = ["Celani", "Piscopo", "Lombardo", "Siracusa"]

# --- 3. SIDEBAR: GESTIONE E BACKUP ---
with st.sidebar:
    st.header("⚙️ CONFIGURAZIONE")
    new_med = st.text_input("➕ Aggiungi nuovo medico")
    if st.button("Aggiungi"):
        if new_med and new_med not in st.session_state.medici_lista:
            st.session_state.medici_lista.append(new_med)
            st.rerun()
    
    medici_attivi = st.multiselect("Medici attivi per il mese:", options=st.session_state.medici_lista, default=st.session_state.medici_lista)
    
    with st.expander("🗑️ Gestione Anagrafica"):
        for m in st.session_state.medici_lista:
            if st.button(f"Elimina {m}", key=f"del_{m}"):
                st.session_state.medici_lista.remove(m)
                st.rerun()

    st.write("---")
    anno_sel = st.number_input("Anno", 2024, 2030, 2025)
    mesi_ita = ["GENNAIO", "FEBBRAIO", "MARZO", "APRILE", "MAGGIO", "GIUGNO", "LUGLIO", "AGOSTO", "SETTEMBRE", "OTTOBRE", "NOVEMBRE", "DICEMBRE"]
    mese_sel = st.selectbox("Mese", mesi_ita, index=datetime.now().month - 1)
    idx_m = mesi_ita.index(mese_sel) + 1
    
    placeholder_ore_side = st.empty()

    st.write("---")
    st.subheader("💾 Backup")
    if st.session_state.db is not None:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            st.session_state.db.to_excel(writer, sheet_name='Turni', index=False)
            pd.DataFrame(st.session_state.medici_lista, columns=['Medici']).to_excel(writer, sheet_name='Medici', index=False)
        st.download_button("📥 Scarica Backup", data=buf.getvalue(), file_name=f"Backup_{mese_sel}.xlsx", use_container_width=True)

    up_file = st.file_uploader("📂 Carica Backup", type="xlsx")
    if up_file:
        try:
            st.session_state.db = pd.read_excel(up_file, sheet_name='Turni').fillna("")
            st.session_state.medici_lista = pd.read_excel(up_file, sheet_name='Medici')['Medici'].tolist()
            st.rerun()
        except: st.error("Errore file")

# --- 4. CALCOLO ORE ---
def calcola_riepilogo(df):
    riepilogo = []
    totale_mese = 0
    for m in st.session_state.medici_lista:
        # Ore Prefestive (4h)
        ore_pref = (df["P 10-14"] == m).sum() * 4
        # Ore Festive Diurne (6h)
        ore_fest_d = ((df["F 08-14"] == m).sum() * 6) + ((df["F 14-20"] == m).sum() * 6) + ((df["P 14-20"] == m).sum() * 6)
        # Ore Notturne (12h)
        ore_notte = (df["NOTT 20-08"] == m).sum() * 12
        
        tot_m = ore_pref + ore_fest_d + ore_notte
        if tot_m > 0:
            riepilogo.append({"Medico": m, "Ore": int(tot_m)})
            totale_mese += tot_m
    return riepilogo, int(totale_mese)

# --- 5. SCHEMA E PDF IN ALTO ---
if st.session_state.db is not None:
    df_clean = st.session_state.db.fillna("").replace(["None", "nan", 0, "0.0"], "")
    riepilogo, totale_mese = calcola_riepilogo(df_clean)

    # Visualizzazione Ore
    col_ore1, col_ore2 = st.columns([2, 1])
    with col_ore1:
        st.markdown(f"**Riepilogo Ore {mese_sel}**: " + " | ".join([f"{r['Medico']}: {r['Ore']}h" for r in riepilogo]))
    with col_ore2:
        st.markdown(f"**TOTALE MESE: {totale_mese}h**")

    with placeholder_ore_side.container():
        st.write(f"**Totale: {totale_mese}h**")
        for r in riepilogo: st.write(f"{r['Medico']}: {r['Ore']}h")

    # --- GENERAZIONE PDF ---
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, f"PCA PORTO EMPEDOCLE - {mese_sel} {anno_sel}", ln=True, align='C')
    pdf.ln(5)

    # Tabella Turni nel PDF
    pdf.set_font("Helvetica", 'B', 8)
    w_g, w_c = 45, 29
    cols = ["GIORNO", "PR 10-14", "PR 14-20", "FE 08-14", "FE 14-20", "NOTTE"]
    for i, c in enumerate(cols): pdf.cell(w_g if i==0 else w_c, 7, c, 1, 0, 'C')
    pdf.ln()

    pdf.set_font("Helvetica", '', 7)
    for _, r in df_clean.iterrows():
        fill = "*" in str(r["GIORNO"])
        pdf.set_fill_color(230, 230, 230) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.cell(w_g, 6, str(r["GIORNO"]), 1, 0, 'L', fill=True)
        for k in ["P 10-14", "P 14-20", "F 08-14", "F 14-20", "NOTT 20-08"]:
            pdf.cell(w_c, 6, str(r[k]), 1, 0, 'C', fill=True)
        pdf.ln()

    # Riepilogo e Firme nel PDF
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(0, 10, f"RIEPILOGO ORE E FIRME - TOTALE MESE: {totale_mese}h", ln=True)
    pdf.ln(5)
    for r in riepilogo:
        pdf.set_font("Helvetica", 'B', 9)
        pdf.cell(50, 10, f"Dott. {r['Medico']}", 1, 0, 'L')
        pdf.cell(30, 10, f"Ore: {r['Ore']}", 1, 0, 'C')
        pdf.cell(100, 10, " Firma: ___________________________", 1, 1, 'L')

    st.download_button("💾 SCARICA PDF FINALE", data=bytes(pdf.output()), file_name=f"Turni_{mese_sel}.pdf", mime="application/pdf", use_container_width=True)

    # Editor Tabella
    config = {k: st.column_config.SelectboxColumn(k, options=[""] + st.session_state.medici_lista) for k in ["P 10-14", "P 14-20", "F 08-14", "F 14-20", "NOTT 20-08"]}
    df_ed = st.data_editor(df_clean, hide_index=True, use_container_width=True, column_config=config)
    st.session_state.db = df_ed

# --- 6. TASTO ROSSO GENERA (IN FONDO) ---
st.write("---")
if st.button("🚀 GENERA SCHEMA AUTOMATICO", use_container_width=True):
    fest = get_festivita(anno_sel); gg = calendar.monthrange(anno_sel, idx_m)[1]
    rows = []; ven_count = 0
    ita_g = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
    
    for d in range(1, gg + 1):
        dt = datetime(anno_sel, idx_m, d); wd = dt.weekday(); f_n = fest.get((d, idx_m), "")
        is_f = (wd == 6 or f_n != ""); is_p = (wd == 5 or (not is_f and ((dt + timedelta(days=1)).weekday() == 6 or ((dt + timedelta(days=1)).day, (dt + timedelta(days=1)).month) in fest)))
        
        def get_m(name, fallback_idx):
            return name if name in medici_attivi else (medici_attivi[fallback_idx % len(medici_attivi)] if medici_attivi else "")

        ass_notte = ""
        if wd in [0, 2]: ass_notte = get_m("Celani", 0)
        elif wd == 1: ass_notte = get_m("Piscopo", 1)
        elif wd == 3: ass_notte = get_m("Lombardo", 2)
        elif wd == 4: 
            ven_count += 1
            ass_notte = get_m("Celani", 0) if ven_count % 2 != 0 else get_m("Piscopo", 1)
        elif wd in [5, 6]: ass_notte = get_m("Siracusa", 3)
        
        ass_diurna = ass_notte if ((is_p or is_f) and ass_notte != "Lombardo") else ""
        prefix = "** " if is_f else ("* " if is_p else "  ")
        
        rows.append({
            "GIORNO": f"{prefix}{d} {ita_g[wd]} {f_n}",
            "P 10-14": ass_diurna if is_p else "", "P 14-20": ass_diurna if is_p else "",
            "F 08-14": ass_diurna if is_f else "", "F 14-20": ass_diurna if is_f else "",
            "NOTT 20-08": ass_notte
        })
    st.session_state.db = pd.DataFrame(rows)
    st.rerun()
