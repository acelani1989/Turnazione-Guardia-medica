import streamlit as st
import pandas as pd
import calendar
import io
from datetime import datetime, timedelta

try:
    from fpdf import FPDF
    pdf_ok = True
except ImportError:
    pdf_ok = False

# --- LOGICA FESTIVITÀ ---
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
    # Nomi abbreviati per stare in tabella
    return {
        (1, 1): "Capod.", (6, 1): "Epif.", (25, 2): "Patr.",
        (25, 4): "Lib.", (1, 5): "Lav.", (2, 6): "Rep.",
        (15, 8): "Ferr.", (1, 11): "Ognis.", (8, 12): "Immac.",
        (25, 12): "Nat.", (26, 12): "Stef.", 
        (p.day, p.month): "Pasqua", (pp.day, pp.month): "Pasqu."
    }

st.set_page_config(page_title="Turni Porto Empedocle", layout="wide")
st.markdown("### PRESIDIO DI CONTINUITA’ ASSISTENZIALE PORTO EMPEDOCLE")

if 'db' not in st.session_state: st.session_state.db = pd.DataFrame()
medici = ["Piscopo", "Celani", "Lombardo", "Siracusa"]

with st.sidebar:
    st.header("⚙️ IMPOSTAZIONI")
    anno_sel = st.number_input("Anno", 2024, 2030, 2026)
    mesi_ita = ["GENNAIO", "FEBBRAIO", "MARZO", "APRILE", "MAGGIO", "GIUGNO", "LUGLIO", "AGOSTO", "SETTEMBRE", "OTTOBRE", "NOVEMBRE", "DICEMBRE"]
    mese_sel = st.selectbox("Mese", mesi_ita, index=2)
    idx_m = mesi_ita.index(mese_sel) + 1

if st.button("🚀 GENERA SCHEMA", type="primary", use_container_width=True):
    fest = get_festivita(anno_sel)
    gg = calendar.monthrange(anno_sel, idx_m)[1]
    rows = []
    ita_g = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
    
    for d in range(1, gg + 1):
        dt = datetime(anno_sel, idx_m, d)
        wd = dt.weekday()
        f_name = fest.get((d, idx_m), "")
        
        is_f = wd == 6 or f_name != ""
        is_p = wd == 5 or (not is_f and ((dt + timedelta(days=1)).weekday() == 6 or ((dt + timedelta(days=1)).day, (dt + timedelta(days=1)).month) in fest))
        
        # Formato Giorno: "1 DOM - Capod."
        label_giorno = f"{d} {ita_g[wd]}"
        if f_name: label_giorno += f" - {f_name}"
        
        rows.append({
            "GIORNO": label_giorno, 
            "PREF 10-14": "---", "PREF 14-20": "---", 
            "FEST 08-14": "---", "FEST 14-20": "---", 
            "NOTT 20-08": "---",
            "TIPO": "F" if is_f else ("P" if is_p else "N")
        })
    st.session_state.db = pd.DataFrame(rows)

if not st.session_state.db.empty:
    df_ed = st.data_editor(st.session_state.db, 
        column_order=("GIORNO", "PREF 10-14", "PREF 14-20", "FEST 08-14", "FEST 14-20", "NOTT 20-08"),
        column_config={
            "GIORNO": st.column_config.TextColumn("GIORNO", disabled=True, width="medium"),
            "PREF 10-14": st.column_config.SelectboxColumn("PREF 10-14", options=medici),
            "PREF 14-20": st.column_config.SelectboxColumn("PREF 14-20", options=medici),
            "FEST 08-14": st.column_config.SelectboxColumn("FEST 08-14", options=medici),
            "FEST 14-20": st.column_config.SelectboxColumn("FEST 14-20", options=medici),
            "NOTT 20-08": st.column_config.SelectboxColumn("NOTT 20-08", options=medici)
        }, hide_index=True, use_container_width=True)

    # EXCEL
    buffer_ex = io.BytesIO()
    with pd.ExcelWriter(buffer_ex, engine='xlsxwriter') as writer:
        df_ex = df_ed[[c for c in df_ed.columns if c != "TIPO"]]
        df_ex.to_excel(writer, index=False, sheet_name='Turni')
        workbook, worksheet = writer.book, writer.sheets['Turni']
        fmt_f = workbook.add_format({'bg_color': '#FFC7CE'})
        fmt_p = workbook.add_format({'bg_color': '#FFEB9C'})
        for i, tipo in enumerate(df_ed["TIPO"]):
            if tipo == "F": worksheet.set_row(i + 1, None, fmt_f)
            elif tipo == "P": worksheet.set_row(i + 1, None, fmt_p)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button("📥 EXCEL COLORATO", buffer_ex.getvalue(), f"Turni_{mese_sel}.xlsx", use_container_width=True)

    with col2:
        if pdf_ok and st.button("📄 PDF PAGINA SINGOLA", use_container_width=True):
            pdf = FPDF('L', 'mm', 'A4')
            pdf.set_margins(8, 8, 8)
            pdf.add_page()
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 7, "PRESIDIO DI CONTINUITA' ASSISTENZIALE PORTO EMPEDOCLE", 0, 1, 'C')
            pdf.cell(0, 7, f"TURNI {mese_sel} {anno_sel}", 0, 1, 'C')
            pdf.ln(1)
            
            # Header
            pdf.set_font("Arial", 'B', 8)
            cols = ["GIORNO", "PREF 10-14", "PREF 14-20", "FEST 08-14", "FEST 14-20", "NOTT 20-08"]
            for c in cols: pdf.cell(46, 7, c, 1, 0, 'C')
            pdf.ln()
            
            # Righe (Altezza ridotta per stare in 1 pagina)
            pdf.set_font("Arial", '', 7)
            for _, r in df_ed.iterrows():
                if r["TIPO"] == "F": pdf.set_fill_color(255, 199, 206)
                elif r["TIPO"] == "P": pdf.set_fill_color(255, 235, 156)
                else: pdf.set_fill_color(255, 255, 255)
                
                pdf.cell(46, 5.8, str(r["GIORNO"]), 1, 0, 'L', True)
                pdf.cell(46, 5.8, str(r["PREF 10-14"]), 1, 0, 'C', True)
                pdf.cell(46, 5.8, str(r["PREF 14-20"]), 1, 0, 'C', True)
                pdf.cell(46, 5.8, str(r["FEST 08-14"]), 1, 0, 'C', True)
                pdf.cell(46, 5.8, str(r["FEST 14-20"]), 1, 0, 'C', True)
                pdf.cell(46, 5.8, str(r["NOTT 20-08"]), 1, 0, 'C', True)
                pdf.ln()
            
            st.download_button("💾 SALVA PDF", pdf.output(dest='S').encode('latin-1'), f"Turni_{mese_sel}.pdf", "application/pdf", use_container_width=True)
