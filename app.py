import streamlit as st
import pandas as pd
import calendar
import io
from datetime import datetime, timedelta

# Gestione sicura delle librerie esterne
try:
    from fpdf import FPDF
    pdf_ok = True
except ImportError:
    pdf_ok = False

# --- LOGICA CALENDARIO ---
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

# --- INTERFACCIA ---
st.set_page_config(page_title="Turni Porto Empedocle", layout="wide")
st.markdown("### PRESIDIO DI CONTINUITA’ ASSISTENZIALE PORTO EMPEDOCLE")

if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame()

medici = ["Piscopo", "Celani", "Lombardo", "Siracusa"]

with st.sidebar:
    st.header("IMPOSTAZIONI")
    anno_sel = st.number_input("Anno", 2024, 2030, 2026)
    mesi_ita = ["GENNAIO", "FEBBRAIO", "MARZO", "APRILE", "MAGGIO", "GIUGNO", 
                "LUGLIO", "AGOSTO", "SETTEMBRE", "OTTOBRE", "NOVEMBRE", "DICEMBRE"]
    mese_sel = st.selectbox("Mese", mesi_ita, index=2)
    idx_m = mesi_ita.index(mese_sel) + 1

# --- GENERAZIONE ---
if st.button("🚀 GENERA SCHEMA", type="primary", use_container_width=True):
    fest = get_festivita(anno_sel)
    gg = calendar.monthrange(anno_sel, idx_m)[1]
    rows = []
    ita_g = ["LUNEDÌ", "MARTEDÌ", "MERCOLEDÌ", "GIOVEDÌ", "VENERDÌ", "SABATO", "DOMENICA"]

    for d in range(1, gg + 1):
        dt = datetime(anno_sel, idx_m, d)
        wd = dt.weekday()
        is_f = wd == 6 or (d, idx_m) in fest
        is_p = wd == 5 or (not is_f and ((dt + timedelta(days=1)).weekday() == 6 or ((dt + timedelta(days=1)).day, (dt + timedelta(days=1)).month) in fest))
        
        rows.append({
            "GIORNO": f"{d} {ita_g[wd]}",
            "P 10-14": "---" if not is_p else "Libero",
            "P 14-20": "---" if not is_p else "Libero",
            "F 08-14": "---" if not is_f else "Libero",
            "F 14-20": "---" if not is_f else "Libero",
            "NOTT 20-08": "Libero",
            "hM": 4 if is_p else (6 if is_f else 0),
            "hP": 6 if (is_p or is_f) else 0,
            "hN": 12
        })
    st.session_state.db = pd.DataFrame(rows)

# --- EDITOR E DOWNLOAD ---
if not st.session_state.db.empty:
    df_ed = st.data_editor(
        st.session_state.db,
        column_order=("GIORNO", "P 10-14", "P 14-20", "F 08-14", "F 14-20", "NOTT 20-08"),
        column_config={
            "GIORNO": st.column_config.TextColumn("GIORNO", disabled=True),
            "P 10-14": st.column_config.SelectboxColumn("PREF 10-14", options=medici),
            "P 14-20": st.column_config.SelectboxColumn("PREF 14-20", options=medici),
            "F 08-14": st.column_config.SelectboxColumn("FEST 08-14", options=medici),
            "F 14-20": st.column_config.SelectboxColumn("FEST 14-20", options=medici),
            "NOTT 20-08": st.column_config.SelectboxColumn("NOTT 20-08", options=medici)
        },
        hide_index=True, use_container_width=True
    )

    # Conteggio ore
    res = []
    for m in medici:
        ore = df_ed[df_ed["P 10-14"]==m]["hM"].sum() + \
              df_ed[df_ed["F 08-14"]==m]["hM"].sum() + \
              df_ed[df_ed["P 14-20"]==m]["hP"].sum() + \
              df_ed[df_ed["F 14-20"]==m]["hP"].sum() + \
              df_ed[df_ed["NOTT 20-08"]==m]["hN"].sum()
        res.append({"Medico": m, "Ore": int(ore)})
    
    st.divider()
    st.table(pd.DataFrame(res))
    st.write(f"**TOTALE ORE COMPLESSIVE: {sum(r['Ore'] for r in res)}**")

    # PULSANTI EXPORT
    col1, col2 = st.columns(2)

    with col1:
        # EXCEL
        buffer_ex = io.BytesIO()
        with pd.ExcelWriter(buffer_ex, engine='xlsxwriter') as writer:
            df_ed.drop(columns=["hM","hP","hN"]).to_excel(writer, index=False, sheet_name='Turni')
        st.download_button("📥 SCARICA EXCEL", buffer_ex.getvalue(), f"Turni_{mese_sel}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    with col2:
        # PDF
        if pdf_ok:
            if st.button("📄 GENERA PDF", use_container_width=True):
                pdf = FPDF('L', 'mm', 'A4')
                pdf.add_page()
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 10, "PRESIDIO DI CONTINUITA' ASSISTENZIALE PORTO EMPEDOCLE", 0, 1, 'C')
                pdf.cell(0, 10, f"TURNI {mese_sel} {anno_sel}", 0, 1, 'C')
                pdf.ln(5)
                pdf.set_font("Arial", 'B', 8)
                header = ["GIORNO", "PREF 10-14", "PREF 14-20", "FEST 08-14", "FEST 14-20", "NOTT 20-08"]
                for col in header: pdf.cell(46, 10, col, 1, 0, 'C')
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
                st.download_button("💾 SALVA PDF", pdf.output(dest='S').encode('latin-1'), f"Turni_{mese_sel}.pdf", "application/pdf", use_container_width=True)
        else:
            st.error("Libreria PDF non trovata nel requirements.txt")
