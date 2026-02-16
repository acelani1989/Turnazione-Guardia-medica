import streamlit as st
import pandas as pd
import calendar
import io
from datetime import datetime, timedelta

# Gestione sicura della libreria PDF
try:
    from fpdf import FPDF
    pdf_pronto = True
except ImportError:
    pdf_pronto = False

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="Gestione Turni Porto Empedocle", layout="wide")
st.markdown("### PRESIDIO DI CONTINUITA’ ASSISTENZIALE PORTO EMPEDOCLE") [cite: 1]

if 'db_turni' not in st.session_state:
    st.session_state.db_turni = pd.DataFrame()

medici = ["Piscopo", "Celani", "Lombardo", "Siracusa"]

# --- 2. LOGICA FESTIVITÀ ---
def get_festivita(anno):
    def pasqua(y):
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
        return datetime(y, mese, giorno)
    
    p = pasqua(anno); pp = p + timedelta(days=1)
    return {
        (1, 1): "Capodanno", (6, 1): "Epifania", (25, 2): "S. Patrono",
        (25, 4): "Liberazione", (1, 5): "Festa Lavoro", (2, 6): "Festa Repubblica",
        (15, 8): "Ferragosto", (1, 11): "Ognissanti", (8, 12): "Immacolata",
        (25, 12): "Natale", (26, 12): "S. Stefano", (p.day, p.month): "Pasqua", (pp.day, pp.month): "Pasquetta"
    }

# --- 3. SIDEBAR E GENERAZIONE ---
with st.sidebar:
    st.header("IMPOSTAZIONI")
    anno_sel = st.number_input("Anno", 2024, 2030, 2026) [cite: 3]
    mesi_ita = ["GENNAIO", "FEBBRAIO", "MARZO", "APRILE", "MAGGIO", "GIUGNO", 
                "LUGLIO", "AGOSTO", "SETTEMBRE", "OTTOBRE", "NOVEMBRE", "DICEMBRE"]
    mese_sel = st.selectbox("Mese", mesi_ita, index=2) [cite: 2]
    idx_mese = mesi_ita.index(mese_sel) + 1

if st.button("🚀 GENERA SCHEMA MENSILE", type="primary", use_container_width=True):
    fest = get_festivita(anno_sel)
    gg = calendar.monthrange(anno_sel, idx_mese)[1]
    rows = []
    nomi_g = ["LUNEDÌ", "MARTEDÌ", "MERCOLEDÌ", "GIOVEDÌ", "VENERDÌ", "SABATO", "DOMENICA"]

    for d in range(1, gg + 1):
        dt = datetime(anno_sel, idx_mese, d)
        wd = dt.weekday()
        is_f = wd == 6 or (d, idx_mese) in fest
        is_p = wd == 5 or (not is_f and ((dt + timedelta(days=1)).weekday() == 6 or ((dt + timedelta(days=1)).day, (dt + timedelta(days=1)).month) in fest))
        
        # Struttura dati conforme allo schema 
        rows.append({
            "GIORNO": f"{d} {nomi_g[wd]}",
            "PREF 10-14": "---" if not is_p else "LIBERO",
            "PREF 14-20": "---" if not is_p else "LIBERO",
            "FEST 08-14": "---" if not is_f else "LIBERO",
            "FEST 14-20": "---" if not is_f else "LIBERO",
            "NOTT 20-08": "LIBERO",
            "hM": 4 if is_p else (6 if is_f else 0),
            "hP": 6 if (is_p or is_f) else 0,
            "hN": 12
        })
    st.session_state.db_turni = pd.DataFrame(rows)

# --- 4. DATA EDITOR E CALCOLO ORE ---
if not st.session_state.db_turni.empty:
    df_ed = st.data_editor(
        st.session_state.db_turni,
        column_order=("GIORNO", "PREF 10-14", "PREF 14-20", "FEST 08-14", "FEST 14-20", "NOTT 20-08"),
        column_config={
            "GIORNO": st.column_config.TextColumn("GIORNO", disabled=True),
            "PREF 10-14": st.column_config.SelectboxColumn("PREF. 10-14", options=medici), [cite: 8]
            "PREF 14-20": st.column_config.SelectboxColumn("PREF. 14-20", options=medici), [cite: 9]
            "FEST 08-14": st.column_config.SelectboxColumn("FEST. 08-14", options=medici), [cite: 10]
            "FEST 14-20": st.column_config.SelectboxColumn("FEST. 14-20", options=medici), [cite: 11]
            "NOTT 20-08": st.column_config.SelectboxColumn("NOTT. 20-08", options=medici) [cite: 12]
        },
        hide_index=True, use_container_width=True
    )

    # Conteggio ore per medico
    st.divider()
    res = []
    for m in medici:
        ore = df_ed[df_ed["PREF 10-14"]==m]["hM"].sum() + \
              df_ed[df_ed["FEST 08-14"]==m]["hM"].sum() + \
              df_ed[df_ed["PREF 14-20"]==m]["hP"].sum() + \
              df_ed[df_ed["FEST 14-20"]==m]["hP"].sum() + \
              df_ed[df_ed["NOTT 20-08"]==m]["hN"].sum()
        res.append({"Medico": m, "Ore Totali": int(ore)})
    
    st.table(pd.DataFrame(res))
    st.write(f"**TOTALE ORE PRESIDIO: {sum(r['Ore Totali'] for r in res)}**") [cite: 139, 140]

    # --- 5. EXPORT ---
    if pdf_pronto:
        if st.button("📄 SCARICA PDF"):
            pdf = FPDF('L', 'mm', 'A4')
            pdf.add_page()
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, "PRESIDIO DI CONTINUITA' ASSISTENZIALE PORTO EMPEDOCLE", 0, 1, 'C') [cite: 1]
            pdf.cell(0, 10, f"TURNI {mese_sel} {anno_sel}", 0, 1, 'C') [cite: 2, 3]
            pdf.ln(5)
            pdf.set_font("Arial", 'B', 8)
            h = ["GIORNO", "PREF 10-14", "PREF 14-20", "FEST 08-14", "FEST 14-20", "NOTT 20-08"] [cite: 4, 5, 6, 7]
            for col in h: pdf.cell(46, 10, col, 1, 0, 'C')
            pdf.ln()
            pdf.set_font("Arial", '', 8)
            for _, r in df_ed.iterrows():
                pdf.cell(46, 8, str(r["GIORNO"]), 1)
                pdf.cell(46, 8, str(r["PREF 10-14"]), 1, 0, 'C')
                pdf.cell(46, 8, str(r["PREF 14-20"]), 1, 0, 'C')
                pdf.cell(46, 8, str(r["FEST 08-14"]), 1, 0, 'C')
                pdf.cell(46, 8, str(r["FEST 14-20"]), 1, 0, 'C')
                pdf.cell(46, 8, str(r["NOTT 20-08"]), 1, 0, 'C')
                pdf.ln()
            st.download_button("Salva PDF", pdf.output(dest='S').encode('latin-1'), f"Turni_{mese_sel}.pdf", "application/pdf")
