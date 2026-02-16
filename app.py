import streamlit as st
import pandas as pd
import calendar
import io
from datetime import datetime, timedelta

# Importazione FPDF (ottimizzata per fpdf2)
try:
    from fpdf import FPDF
except ImportError:
    st.error("Libreria FPDF non trovata. Assicurati di avere 'fpdf2' nel file requirements.txt")

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

# --- 2. SETUP ---
st.set_page_config(page_title="Turni PCA Porto Empedocle", layout="wide")
st.markdown("### PRESIDIO DI CONTINUITA’ ASSISTENZIALE PORTO EMPEDOCLE")

if 'db' not in st.session_state:
    st.session_state.db = None
if 'medici_lista' not in st.session_state:
    st.session_state.medici_lista = ["Celani", "Piscopo", "Lombardo", "Siracusa"]

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ CONFIGURAZIONE")
    new_med = st.text_input("➕ Aggiungi nuovo medico")
    if st.button("Aggiungi alla lista"):
        if new_med and new_med not in st.session_state.medici_lista:
            st.session_state.medici_lista.append(new_med)
            st.rerun()
    
    anno_sel = st.number_input("Anno", 2024, 2030, 2026)
    mesi_ita = ["GENNAIO", "FEBBRAIO", "MARZO", "APRILE", "MAGGIO", "GIUGNO", "LUGLIO", "AGOSTO", "SETTEMBRE", "OTTOBRE", "NOVEMBRE", "DICEMBRE"]
    mese_sel = st.selectbox("Mese", mesi_ita, index=datetime.now().month - 1)
    idx_m = mesi_ita.index(mese_sel) + 1
    
    placeholder_sidebar = st.container()
    
    st.write("---")
    st.subheader("💾 Backup Excel")
    if st.session_state.db is not None:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_export = st.session_state.db.copy().replace(["None", "nan", "NaN", "0", 0], "")
            df_export.to_excel(writer, sheet_name='Turni', index=False)
            pd.DataFrame({"ListaMedici": st.session_state.medici_lista}).to_excel(writer, sheet_name='Anagrafica', index=False)
        st.download_button("📤 SCARICA BACKUP", buffer.getvalue(), f"backup_{mese_sel}.xlsx", use_container_width=True)

    uploaded_file = st.file_uploader("📥 IMPORTA BACKUP", type=["xlsx"])
    if uploaded_file:
        st.session_state.db = pd.read_excel(uploaded_file, sheet_name='Turni').fillna("")
        st.rerun()

# --- 4. LOGICA GENERAZIONE ---
if st.button("🚀 GENERA SCHEMA AUTOMATICO", type="primary", use_container_width=True):
    fest = get_festivita(anno_sel)
    gg = calendar.monthrange(anno_sel, idx_m)[1]
    rows = []
    ita_g = ["LUNEDÌ", "MARTEDÌ", "MERCOLEDÌ", "GIOVEDÌ", "VENERDÌ", "SABATO", "DOMENICA"]
    ven_count = 0
    
    for d in range(1, gg + 1):
        dt = datetime(anno_sel, idx_m, d)
        wd = dt.weekday()
        f_n = fest.get((d, idx_m), "")
        is_f = (wd == 6 or f_n != "")
        is_p = (wd == 5 or (not is_f and ((dt + timedelta(days=1)).weekday() == 6 or ((dt + timedelta(days=1)).day, (dt + timedelta(days=1)).month) in fest)))
        
        ass_notte = ""
        if wd in [0, 2]: ass_notte = "Celani"
        elif wd == 1: ass_notte = "Piscopo"
        elif wd == 3: ass_notte = "Lombardo"
        elif wd == 4: 
            ven_count += 1
            ass_notte = "Celani" if ven_count % 2 != 0 else "Piscopo"
        elif wd in [5, 6]: ass_notte = "Siracusa"
        
        ass_diurna = ass_notte if ((is_p or is_f) and ass_notte != "Lombardo") else ""
        
        rows.append({
            "GIORNO": f"{d} {ita_g[wd]} {f_n}",
            "P 10-14": ass_diurna if is_p else "", 
            "P 14-20": ass_diurna if is_p else "",
            "F 08-14": ass_diurna if is_f else "", 
            "F 14-20": ass_diurna if is_f else "",
            "NOTT 20-08": ass_notte,
            "TIPO": "FEST" if is_f else ("PREF" if is_p else "FER")
        })
    st.session_state.db = pd.DataFrame(rows).fillna("")

# --- 5. VISUALIZZAZIONE E PDF ---
if st.session_state.db is not None:
    # PULIZIA DRASTICA PER L'EDITOR
    st.session_state.db = st.session_state.db.replace(["None", "nan", "NaN", "0", 0, "0.0"], "")
    
    # 1. TASTO PDF IN ALTO
    pdf = FPDF('P', 'mm', 'A4')
    pdf.set_margins(7, 10, 7)
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 6, f"PCA PORTO EMPEDOCLE - {mese_sel} {anno_sel}", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    w_g, w_c = 42, 30
    pdf.set_font("helvetica", 'B', 7)
    cols = ["GIORNO", "PR 10-14", "PR 14-20", "FE 08-14", "FE 14-20", "NOT 20-08"]
    for i, c in enumerate(cols): pdf.cell(w_g if i==0 else w_c, 6, c, 1, 0, 'C')
    pdf.ln()

    pdf.set_font("helvetica", '', 6.5)
    for _, r in st.session_state.db.iterrows():
        pdf.cell(w_g, 5.2, str(r["GIORNO"]), 1)
        for k in ["P 10-14", "P 14-20", "F 08-14", "F 14-20", "NOTT 20-08"]:
            val = str(r[k]) if (pd.notna(r[k]) and str(r[k]).strip().lower() not in ["none", "nan", "", "0"]) else ""
            pdf.cell(w_c, 5.2, val, 1, 0, 'C')
        pdf.ln()

    st.download_button("💾 SCARICA PDF FINALE", bytes(pdf.output()), f"Turni_{mese_sel}.pdf", "application/pdf", use_container_width=True)

    # 2. TABELLA EDITABILE
    config = {k: st.column_config.SelectboxColumn(k, options=[""] + st.session_state.medici_lista) for k in ["P 10-14", "P 14-20", "F 08-14", "F 14-20", "NOTT 20-08"]}
    df_ed = st.data_editor(st.session_state.db, column_order=("GIORNO", "P 10-14", "P 14-20", "F 08-14", "F 14-20", "NOTT 20-08"),
                           column_config=config, hide_index=True, use_container_width=True)
    st.session_state.db = df_ed

    # Riepilogo Ore in Sidebar
    riepilogo = []
    for m in st.session_state.medici_lista:
        o = (df_ed[df_ed["P 10-14"]==m].shape[0]*4) + (df_ed[df_ed["F 08-14"]==m].shape[0]*6) + \
            (df_ed[df_ed["P 14-20"]==m].shape[0]*6) + (df_ed[df_ed["F 14-20"]==m].shape[0]*6) + \
            (df_ed[df_ed["NOTT 20-08"]==m].shape[0]*12)
        if o > 0: riepilogo.append(f"**{m}**: {int(o)} h")
    
    with placeholder_sidebar:
        st.subheader("📊 Ore Medici")
        for r in riepilogo: st.write(r)
