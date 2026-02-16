import streamlit as st
import pandas as pd
import calendar
import io
from datetime import datetime, timedelta

# Gestione librerie esterne
try:
    from fpdf import FPDF
    pdf_lib_ok = True
except ImportError:
    pdf_lib_ok = False

# --- 1. CONFIGURAZIONE E LOGICA ---
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
    p = pasqua(anno); pp = p + timedelta(days=1)
    return {(1,1):"Capodanno",(6,1):"Epifania",(25,2):"S. Patrono",(25,4):"Liberazione",(1,5):"Festa Lavoro",
            (2,6):"Festa Repubblica",(15,8):"Ferragosto",(1,11):"Ognissanti",(8,12):"Immacolata",
            (25,12):"Natale",(26,12):"S. Stefano",(p.day,p.month):"Pasqua",(pp.day,pp.month):"Pasquetta"}

st.set_page_config(page_title="Gestione Turni Calvagna", layout="wide")

if 'db' not in st.session_state: st.session_state.db = pd.DataFrame()
medici = ["Piscopo", "Celani", "Lombardo", "Siracusa"]

# --- 2. INTERFACCIA ---
st.markdown("### PRESIDIO DI CONTINUITA’ ASSISTENZIALE PORTO EMPEDOCLE") [cite: 1]

with st.sidebar:
    anno = st.number_input("Anno", 2024, 2030, 2026) [cite: 3]
    mesi = ["GENNAIO", "FEBBRAIO", "MARZO", "APRILE", "MAGGIO", "GIUGNO", "LUGLIO", "AGOSTO", "SETTEMBRE", "OTTOBRE", "NOVEMBRE", "DICEMBRE"] [cite: 2]
    mese_n = st.selectbox("Mese", mesi, index=2)
    idx = mesi.index(mese_n) + 1

if st.button("🚀 GENERA SCHEMA", type="primary", use_container_width=True):
    fest = get_festivita(anno)
    days = calendar.monthrange(anno, idx)[1]
    rows = []
    ita_g = ["LUNEDÌ", "MARTEDÌ", "MERCOLEDÌ", "GIOVEDÌ", "VENERDÌ", "SABATO", "DOMENICA"]
    
    for d in range(1, days + 1):
        dt = datetime(anno, idx, d)
        wd = dt.weekday()
        is_f = wd == 6 or (d, idx) in fest
        is_p = wd == 5 or (not is_f and ((dt+timedelta(days=1)).weekday()==6 or ((dt+timedelta(days=1)).day, (dt+timedelta(days=1)).month) in fest))
        
        row = {"GIORNO": f"{d} {ita_g[wd]}", "P 10-14": "---", "P 14-20": "---", "F 08-14": "---", "F 14-20": "---", "NOTT": "---", "hM":0, "hP":0, "hN":12}
        if is_f: row["F 08-14"], row["F 14-20"], row["hM"], row["hP"] = "---", "---", 6, 6
        elif is_p: row["P 10-14"], row["P 14-20"], row["hM"], row["hP"] = "---", "---", 4, 6
        rows.append(row)
    st.session_state.db = pd.DataFrame(rows)

# --- 3. TABELLA E EXPORT ---
if not st.session_state.db.empty:
    df_ed = st.data_editor(st.session_state.db, 
        column_order=("GIORNO", "P 10-14", "P 14-20", "F 08-14", "F 14-20", "NOTT"),
        column_config={
            "GIORNO": st.column_config.TextColumn("GIORNO", disabled=True),
            "P 10-14": st.column_config.SelectboxColumn("PREF 10-14", options=medici), [cite: 5, 8]
            "P 14-20": st.column_config.SelectboxColumn("PREF 14-20", options=medici), [cite: 5, 9]
            "F 08-14": st.column_config.SelectboxColumn("FEST 08-14", options=medici), [cite: 6, 10]
            "F 14-20": st.column_config.SelectboxColumn("FEST 14-20", options=medici), [cite: 6, 11]
            "NOTT": st.column_config.SelectboxColumn("NOTT 20-08", options=medici)}, [cite: 7, 12]
        hide_index=True, use_container_width=True)

    # Calcolo Ore
    tot_ore = 0
    for m in medici:
        h = df_ed[df_ed["P 10-14"]==m]["hM"].sum() + df_ed[df_ed["F 08-14"]==m]["hM"].sum() + \
            df_ed[df_ed["P 14-20"]==m]["hP"].sum() + df_ed[df_ed["F 14-20"]==m]["hP"].sum() + \
            df_ed[df_ed["NOTT"]==m]["hN"].sum()
        tot_ore += h
    st.write(f"**TOTALE ORE: {tot_ore}**") [cite: 139, 140]

    # Export PDF Professionale
    if pdf_lib_ok and st.button("📄 SCARICA PDF STILE CALVAGNA"):
        pdf = FPDF('L', 'mm', 'A4')
        pdf.add_page()
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "PRESIDIO DI CONTINUITA' ASSISTENZIALE PORTO EMPEDOCLE", 0, 1, 'C') [cite: 1]
        pdf.cell(0, 10, f"TURNI {mese_n} {anno}", 0, 1, 'C') [cite: 2, 3]
        pdf.set_font("Arial", 'B', 8)
        cols = ["GIORNO", "PREF 10-14", "PREF 14-20", "FEST 08-14", "FEST 14-20", "NOTT 20-08"] [cite: 4, 5, 6, 7]
        for c in cols: pdf.cell(46, 10, c, 1, 0, 'C')
        pdf.ln()
        pdf.set_font("Arial", '', 8)
        for _, r in df_ed.iterrows():
            pdf.cell(46, 8, str(r["GIORNO"]), 1)
            for c in ["P 10-14", "P 14-20", "F 08-14", "F 14-20", "NOTT"]:
                pdf.cell(46, 8, str(r[c]), 1, 0, 'C')
            pdf.ln()
        st.download_button("Clicca qui per il PDF", pdf.output(dest='S').encode('latin-1'), f"Turni_{mese_n}.pdf", "application/pdf")
