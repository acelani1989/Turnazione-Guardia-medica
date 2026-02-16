import streamlit as st
import pandas as pd
import calendar
import io
from datetime import datetime, timedelta

# Gestione libreria PDF per evitare crash se manca nel sistema
try:
    from fpdf import FPDF
    pdf_lib_ok = True
except ImportError:
    pdf_lib_ok = False

# --- 1. LOGICA FESTIVITÀ E SANTO PATRONO ---
def get_festivita(anno):
    def calcola_pasqua(y):
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
    
    p = calcola_pasqua(anno); pp = p + timedelta(days=1)
    return {
        (1, 1): "Capodanno", (6, 1): "Epifania", (25, 2): "S. Patrono",
        (25, 4): "Liberazione", (1, 5): "Festa Lavoro", (2, 6): "Festa Repubblica",
        (15, 8): "Ferragosto", (1, 11): "Ognissanti", (8, 12): "Immacolata",
        (25, 12): "Natale", (26, 12): "S. Stefano", 
        (p.day, p.month): "Pasqua", (pp.day, pp.month): "Pasquetta"
    }

# --- 2. CONFIGURAZIONE UI ---
st.set_page_config(page_title="Gestione Turni Calvagna", layout="wide")
st.markdown("### PRESIDIO DI CONTINUITA’ ASSISTENZIALE PORTO EMPEDOCLE") [cite: 1]

if 'db' not in st.session_state: 
    st.session_state.db = pd.DataFrame()

medici_list = ["Piscopo", "Celani", "Lombardo", "Siracusa"] [cite: 17, 21, 30, 36]

with st.sidebar:
    st.header("IMPOSTAZIONI")
    anno_sel = st.number_input("Anno", 2024, 2030, 2026) [cite: 3]
    mesi_ita = ["GENNAIO", "FEBBRAIO", "MARZO", "APRILE", "MAGGIO", "GIUGNO", 
                "LUGLIO", "AGOSTO", "SETTEMBRE", "OTTOBRE", "NOVEMBRE", "DICEMBRE"]
    mese_n = st.selectbox("Mese", mesi_ita, index=2) [cite: 2]
    idx = mesi_ita.index(mese_n) + 1

# --- 3. GENERAZIONE SCHEMA (Secondo File Calvagna) ---
if st.button("🚀 GENERA SCHEMA TURNI", type="primary", use_container_width=True):
    fest = get_festivita(anno_sel)
    days = calendar.monthrange(anno_sel, idx)[1]
    rows = []
    ita_g = ["LUNEDÌ", "MARTEDÌ", "MERCOLEDÌ", "GIOVEDÌ", "VENERDÌ", "SABATO", "DOMENICA"]
    
    for d in range(1, days + 1):
        dt = datetime(anno_sel, idx, d)
        wd = dt.weekday()
        # Identificazione Festivo/Prefestivo
        is_f = wd == 6 or (d, idx) in fest
        is_p = wd == 5 or (not is_f and ((dt + timedelta(days=1)).weekday() == 6 or ((dt + timedelta(days=1)).day, (dt + timedelta(days=1)).month) in fest))
        
        row = {
            "GIORNO": f"{d} {ita_g[wd]}", [cite: 4]
            "P 10-14": "---", "P 14-20": "---", [cite: 5, 8, 9]
            "F 08-14": "---", "F 14-20": "---", [cite: 6, 10, 11]
            "NOTT 20-08": "---", [cite: 7, 12]
            "hM": 0, "hP": 0, "hN": 12
        }
        
        if is_f:
            row["F 08-14"], row["F 14-20"], row["hM"], row["hP"] = "Libero", "Libero", 6, 6
        elif is_p:
            row["P 10-14"], row["P 14-20"], row["hM"], row["hP"] = "Libero", "Libero", 4, 6
        
        rows.append(row)
    st.session_state.db = pd.DataFrame(rows)

# --- 4. EDITOR TABELLA ---
if not st.session_state.db.empty:
    df_ed = st.data_editor(
        st.session_state.db, 
        column_order=("GIORNO", "P 10-14", "P 14-20", "F 08-14", "F 14-20", "NOTT 20-08"),
        column_config={
            "GIORNO": st.column_config.TextColumn("GIORNO", disabled=True), [cite: 4]
            "P 10-14": st.column_config.SelectboxColumn("PREFESTIVO 10-14", options=medici_list), [cite: 5, 8]
            "P 14-20": st.column_config.SelectboxColumn("PREFESTIVO 14-20", options=medici_list), [cite: 5, 9]
            "F 08-14": st.column_config.SelectboxColumn("FESTIVO 08-14", options=medici_list), [cite: 6, 10]
            "F 14-20": st.column_config.SelectboxColumn("FESTIVO 14-20", options=medici_list), [cite: 6, 11]
            "NOTT 20-08": st.column_config.SelectboxColumn("NOTTURNO 20-08", options=medici_list) [cite: 7, 12]
        },
        hide_index=True, 
        use_container_width=True
    )

    # --- 5. RIEPILOGO ORE E EXPORT ---
    st.divider()
    stats = []
    for m in medici_list:
        h = df_ed[df_ed["P 10-14"]==m]["hM"].sum() + \
            df_ed[df_ed["F 08-14"]==m]["hM"].sum() + \
            df_ed[df_ed["P 14-20"]==m]["hP"].sum() + \
            df_ed[df_ed["F 14-20"]==m]["hP"].sum() + \
            df_ed[df_ed["NOTT 20-08"]==m]["hN"].sum()
        stats.append({"Medico": m, "Ore": int(h)})
    
    st.table(pd.DataFrame(stats))
    st.write(f"**TOTALE ORE PRESIDIO: {sum(s['Ore'] for s in stats)}**") [cite: 139-140]

    # Download Excel
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_ed.drop(columns=["hM","hP","hN"]).to_excel(writer, index=False)
    st.download_button("📥 SCARICA EXCEL", buffer.getvalue(), f"Turni_{mese_n}.xlsx", use_container_width=True)

    # Download PDF (Stile Calvagna)
    if pdf_lib_ok:
        if st.button("📄 SCARICA PDF UFFICIALE", use_container_width=True):
            pdf = FPDF('L', 'mm', 'A4')
            pdf.add_page()
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, "PRESIDIO DI CONTINUITA' ASSISTENZIALE PORTO EMPEDOCLE", 0, 1, 'C') [cite: 1]
            pdf.cell(0, 10, f"TURNI {mese_n} {anno_sel}", 0, 1, 'C') [cite: 2-3]
            pdf.ln(5)
            
            pdf.set_font("Arial", 'B', 8)
            headers = ["GIORNO", "PREF 10-14", "PREF 14-20", "FEST 08-14", "FEST 14-20", "NOTT 20-08"] [cite: 4-7]
            for h in headers: pdf.cell(46, 10, h, 1, 0, 'C')
            pdf.ln()
            
            pdf.set_font("Arial", '', 8)
            for _, r in df_ed.iterrows():
                pdf.cell(46, 8, str(r["GIORNO"]), 1)
                pdf.cell(46, 8, str(r["P 10-14"]), 1, 0, 'C')
                pdf.cell(46, 8, str(r["P 14-20"]), 1, 0, 'C')
                pdf.cell(46, 8, str(r["F 08-14"]), 1, 0, 'C')
                pdf.cell(46, 8, str(r["F 14-20"]), 1, 0, 'C')
                pdf.cell(46, 8, str(r["NOTT 20-08"]), 1, 0, 'C')
                pdf.ln()
            
            st.download_button("Clicca per il PDF", pdf.output(dest='S').encode('latin-1'), f"Turni_{mese_n}.pdf", "application/pdf")
