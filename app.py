import streamlit as st
import pandas as pd
import calendar
import io
from datetime import datetime, timedelta
# Nota: Per il PDF è necessaria la libreria fpdf (pip install fpdf)
from fpdf import FPDF

# --- 1. LOGICA CALENDARIO E FESTIVITÀ ---
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
        return datetime(y, mese, giorno)

    p = calcola_pasqua(anno)
    pp = p + timedelta(days=1)
    return {
        (1, 1): "Capodanno", (6, 1): "Epifania", (25, 2): "S. Patrono",
        (25, 4): "Liberazione", (1, 5): "Festa Lavoro", (2, 6): "Festa Repubblica",
        (15, 8): "Ferragosto", (1, 11): "Ognissanti", (8, 12): "Immacolata",
        (25, 12): "Natale", (26, 12): "S. Stefano", (p.day, p.month): "Pasqua", (pp.day, pp.month): "Pasquetta"
    }

def is_festivo(dt, fest):
    return dt.weekday() == 6 or (dt.day, dt.month) in fest

def is_prefestivo(dt, fest):
    domani = dt + timedelta(days=1)
    return dt.weekday() == 5 or is_festivo(domani, fest)

def get_giorno_ita(dt):
    return ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"][dt.weekday()]

# --- 2. CONFIGURAZIONE UI ---
st.set_page_config(page_title="Generatore Turni C.A.", layout="wide")
st.title("⚕️ Generatore Turni Porto Empedocle")

if 'db_turni' not in st.session_state:
    st.session_state.db_turni = pd.DataFrame()
if 'medici' not in st.session_state:
    st.session_state.medici = ["Piscopo", "Celani", "Lombardo", "Siracusa"]

with st.sidebar:
    st.header("⚙️ Parametri")
    anno_sel = st.number_input("Anno", min_value=2020, max_value=2035, value=2026)
    mesi_ita = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", 
                "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
    mese_nome = st.selectbox("Mese", mesi_ita, index=2)
    mese_idx = mesi_ita.index(mese_nome) + 1

# --- 3. GENERAZIONE SECONDO SCHEMA ALLEGATO ---
if st.button("🚀 Genera Schema Turni", type="primary"):
    fest = get_festivita(anno_sel)
    gg_mese = calendar.monthrange(anno_sel, mese_idx)[1]
    rows = []

    for d in range(1, gg_mese + 1):
        dt = datetime(anno_sel, mese_idx, d)
        festivo = is_festivo(dt, fest)
        prefestivo = is_prefestivo(dt, fest)
        
        # Inizializzazione colonne come da schema 
        m_10_14, p_14_20, m_08_14, f_14_20, n_20_08 = "---", "---", "---", "---", "Libero"
        om, op, on = 0, 0, 12

        if festivo:
            m_08_14, f_14_20 = "Libero", "Libero"
            om, op = 6, 6
        elif prefestivo:
            m_10_14, p_14_20 = "Libero", "Libero"
            om, op = 4, 6

        rows.append({
            "GIORNO": f"{d} {get_giorno_ita(dt).upper()}",
            "PREFESTIVO 10-14": m_10_14,
            "PREFESTIVO 14-20": p_14_20,
            "FESTIVO 08-14": m_08_14,
            "FESTIVO 14-20": f_14_20,
            "NOTTURNO 20-08": n_20_08,
            "OreM": om, "OreP": op, "OreN": on
        })
    st.session_state.db_turni = pd.DataFrame(rows)

# --- 4. EDITING E EXPORT ---
if not st.session_state.db_turni.empty:
    lista_m = st.session_state.medici + ["---"]
    
    edited_df = st.data_editor(
        st.session_state.db_turni,
        column_order=("GIORNO", "PREFESTIVO 10-14", "PREFESTIVO 14-20", "FESTIVO 08-14", "FESTIVO 14-20", "NOTTURNO 20-08"),
        column_config={
            "GIORNO": st.column_config.TextColumn("GIORNO", width="medium", disabled=True),
            "PREFESTIVO 10-14": st.column_config.SelectboxColumn("10-14", options=lista_m),
            "PREFESTIVO 14-20": st.column_config.SelectboxColumn("14-20", options=lista_m),
            "FESTIVO 08-14": st.column_config.SelectboxColumn("08-14", options=lista_m),
            "FESTIVO 14-20": st.column_config.SelectboxColumn("14-20", options=lista_m),
            "NOTTURNO 20-08": st.column_config.SelectboxColumn("20-08", options=lista_m),
        },
        use_container_width=True, hide_index=True
    )

    # --- DOWNLOAD EXCEL ---
    buffer_excel = io.BytesIO()
    with pd.ExcelWriter(buffer_excel, engine='xlsxwriter') as writer:
        edited_df.drop(columns=["OreM", "OreP", "OreN"]).to_excel(writer, index=False, sheet_name='Turni')
    st.download_button("📥 Scarica in EXCEL", buffer_excel.getvalue(), f"Turni_{mese_nome}.xlsx")

    # --- GENERAZIONE PDF ---
    if st.button("📄 Genera PDF"):
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f"PRESIDIO DI CONTINUITA' ASSISTENZIALE PORTO EMPEDOCLE - {mese_nome.upper()} {anno_sel}", ln=True, align='C')
        pdf.set_font("Arial", 'B', 8)
        
        # Intestazioni 
        cols = ["GIORNO", "PREF 10-14", "PREF 14-20", "FEST 08-14", "FEST 14-20", "NOTT 20-08"]
        col_widths = [45, 45, 45, 45, 45, 45]
        for i, col in enumerate(cols):
            pdf.cell(col_widths[i], 10, col, border=1, align='C')
        pdf.ln()
        
        pdf.set_font("Arial", '', 8)
        for _, row in edited_df.iterrows():
            pdf.cell(col_widths[0], 8, str(row["GIORNO"]), border=1)
            pdf.cell(col_widths[1], 8, str(row["PREFESTIVO 10-14"]), border=1, align='C')
            pdf.cell(col_widths[2], 8, str(row["PREFESTIVO 14-20"]), border=1, align='C')
            pdf.cell(col_widths[3], 8, str(row["FESTIVO 08-14"]), border=1, align='C')
            pdf.cell(col_widths[4], 8, str(row["FESTIVO 14-20"]), border=1, align='C')
            pdf.cell(col_widths[5], 8, str(row["NOTTURNO 20-08"]), border=1, align='C')
            pdf.ln()
            
        pdf_output = pdf.output(dest='S').encode('latin-1')
        st.download_button("📥 Scarica in PDF", pdf_output, f"Turni_{mese_nome}.pdf", "application/pdf")
