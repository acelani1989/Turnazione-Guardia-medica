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
        (1, 1): "Capod.", (6, 1): "Epif.", (25, 2): "Patr.",
        (25, 4): "Lib.", (1, 5): "Lav.", (2, 6): "Rep.",
        (15, 8): "Ferr.", (1, 11): "Ognis.", (8, 12): "Immac.",
        (25, 12): "Nat.", (26, 12): "Stef.", (p.day, p.month): "Pasqua", (pp.day, pp.month): "Pasqu."
    }

st.set_page_config(page_title="Turni Guardia Medica", layout="wide")
st.markdown("### PRESIDIO DI CONTINUITA’ ASSISTENZIALE PORTO EMPEDOCLE")

if 'db' not in st.session_state: st.session_state.db = pd.DataFrame()
medici = ["Piscopo", "Celani", "Lombardo", "Siracusa"]

with st.sidebar:
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
        g_str = f"{d} {ita_g[wd]}" + (f" - {f_name}" if f_name else "")
        rows.append({"GIORNO": g_str, "P 10-14": "", "P 14-20": "", "F 08-14": "", "F 14-20": "", "NOTT 20-08": "", "TIPO": "F" if is_f else ("P" if is_p else "N")})
    st.session_state.db = pd.DataFrame(rows)

if not st.session_state.db.empty:
    df_ed = st.data_editor(st.session_state.db, column_order=("GIORNO", "P 10-14", "P 14-20", "F 08-14", "F 14-20", "NOTT 20-08"), hide_index=True, use_container_width=True)

    # EXCEL
    buf_ex = io.BytesIO()
    with pd.ExcelWriter(buf_ex, engine='xlsxwriter') as writer:
        df_ed.drop(columns=["TIPO"]).to_excel(writer, index=False, sheet_name='Turni')
        wb, ws = writer.book, writer.sheets['Turni']
        f_f, f_p = wb.add_format({'bg_color': '#FFC7CE'}), wb.add_format({'bg_color': '#FFEB9C'})
        for i, t in enumerate(df_ed["TIPO"]):
            if t == "F": ws.set_row(i+1, None, f_f)
            elif t == "P": ws.set_row(i+1, None, f_p)

    c1, c2 = st.columns(2)
    with c1: st.download_button("📥 SCARICA EXCEL", buf_ex.getvalue(), f"Turni_{mese_sel}.xlsx", use_container_width=True)
    with c2:
        if pdf_ok and st.button("📄 GENERA PDF (PAGINA SINGOLA)", use_container_width=True):
            pdf = FPDF('L', 'mm', 'A4')
            pdf.set_margins(8, 5, 8)
            pdf.add_page()
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 7, "PRESIDIO DI CONTINUITA' ASSISTENZIALE PORTO EMPEDOCLE", 0, 1, 'C')
            pdf.cell(0, 7, f"TURNI {mese_sel} {anno_sel}", 0, 1, 'C')
            pdf.ln(1)
            pdf.set_font("Arial", 'B', 8)
            cols = ["GIORNO", "PREF 10-14", "PREF 14-20", "FEST 08-14", "FEST 14-20", "NOTT 20-08"]
            for c in cols: pdf.cell(46, 6, c, 1, 0, 'C')
            pdf.ln()
            pdf.set_font("Arial", '', 7.5)
            for _, r in df_ed.iterrows():
                if r["TIPO"] == "F": pdf.set_fill_color(255, 199, 206)
                elif r["TIPO"] == "P": pdf.set_fill_color(255, 235, 156)
                else: pdf.set_fill_color(255, 255, 255)
                pdf.cell(46, 5.5, str(r["GIORNO"]), 1, 0, 'L', True)
                for k in ["P 10-14", "P 14-20", "F 08-14", "F 14-20", "NOTT 20-08"]:
                    pdf.cell(46, 5.5, str(r[k]), 1, 0, 'C', True)
                pdf.ln()
            st.download_button("💾 SALVA PDF", pdf.output(dest='S').encode('latin-1'), "Turni.pdf", "application/pdf", use_container_width=True)
