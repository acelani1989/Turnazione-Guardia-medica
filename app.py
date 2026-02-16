import streamlit as st
import pandas as pd
import calendar
import io
from datetime import datetime, timedelta
from fpdf import FPDF

# --- 1. FUNZIONE FESTIVITÀ ---
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
    return {(1, 1): "Capodanno", (6, 1): "Epifania", (25, 2): "Patrono", (25, 4): "Liberazione", (1, 5): "Lavoro", (2, 6): "Repubblica", (15, 8): "Ferragosto", (1, 11): "Ognissanti", (8, 12): "Immacolata", (25, 12): "Natale", (26, 12): "S.Stefano", (p.day, p.month): "Pasqua", (pp.day, pp.month): "Pasquetta"}

# --- 2. SETUP E STILE ---
st.set_page_config(page_title="Turni PCA Porto Empedocle", layout="wide")
st.markdown("""
    <style>
    div.stButton > button:first-child { background-color: #ff4b4b !important; color: white !important; font-weight: bold !important; }
    footer {visibility: hidden;}
    [data-testid="stElementToolbar"] {display: none;}
    .st-emotion-cache-1ghh6y0, .st-emotion-cache-1wivap2 { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("### PRESIDIO DI CONTINUITA’ ASSISTENZIALE PORTO EMPEDOCLE")

if 'db' not in st.session_state: st.session_state.db = None
if 'medici_lista' not in st.session_state: st.session_state.medici_lista = ["Celani", "Piscopo", "Lombardo", "Siracusa"]

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ CONFIGURAZIONE")
    new_med = st.text_input("➕ Aggiungi medico")
    if st.button("Aggiungi"):
        if new_med and new_med not in st.session_state.medici_lista:
            st.session_state.medici_lista.append(new_med); st.rerun()
    
    medici_attivi = st.multiselect("Medici attivi:", options=st.session_state.medici_lista, default=st.session_state.medici_lista)
    
    with st.expander("🗑️ Gestione Anagrafica"):
        for m in st.session_state.medici_lista:
            if st.button(f"Elimina {m}", key=f"del_{m}"):
                st.session_state.medici_lista.remove(m); st.rerun()

    anno_sel = st.number_input("Anno", 2024, 2030, 2025)
    mesi_ita = ["GENNAIO", "FEBBRAIO", "MARZO", "APRILE", "MAGGIO", "GIUGNO", "LUGLIO", "AGOSTO", "SETTEMBRE", "OTTOBRE", "NOVEMBRE", "DICEMBRE"]
    mese_sel = st.selectbox("Mese", mesi_ita, index=datetime.now().month - 1)
    idx_m = mesi_ita.index(mese_sel) + 1
    
    st.write("---")
    st.subheader("💾 Backup")
    if st.session_state.db is not None:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            st.session_state.db.to_excel(writer, sheet_name='Turni', index=False)
            pd.DataFrame(st.session_state.medici_lista, columns=['Medici']).to_excel(writer, sheet_name='Medici', index=False)
        st.download_button("📥 Scarica Backup", data=buf.getvalue(), file_name=f"Backup_{mese_sel}.xlsx", use_container_width=True)

# --- 4. LOGICA ORE ---
def calcola_riepilogo(df):
    riepilogo = []; totale_mese = 0
    for m in st.session_state.medici_lista:
        o_pref = (df["P 10-14"] == m).sum() * 4
        o_fest = ((df["F 08-14"] == m).sum() * 6) + ((df["F 14-20"] == m).sum() * 6) + ((df["P 14-20"] == m).sum() * 6)
        o_notte = (df["NOTT 20-08"] == m).sum() * 12
        tot = o_pref + o_fest + o_notte
        if tot > 0: riepilogo.append({"Medico": m, "Ore": int(tot)}); totale_mese += tot
    return riepilogo, int(totale_mese)

# --- 5. VISUALIZZAZIONE IN ALTO ---
if st.session_state.db is not None:
    df_clean = st.session_state.db.fillna("").replace(["None", "nan", 0, "0.0"], "")
    riepilogo, totale_mese = calcola_riepilogo(df_clean)

    # Info Ore sopra lo schema
    st.markdown(f"**Totale Mese: {totale_mese}h** | " + " - ".join([f"{r['Medico']}: {r['Ore']}h" for r in riepilogo]))

    # --- GENERAZIONE PDF (SINGOLA PAGINA) ---
    pdf = FPDF(); pdf.set_auto_page_break(auto=False); pdf.add_page(); pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(0, 8, f"PCA PORTO EMPEDOCLE - {mese_sel} {anno_sel}", ln=True, align='C')
    
    # Tabella compattata
    pdf.set_font("Helvetica", 'B', 7)
    w_g, w_c = 40, 30
    cols = ["GIORNO", "PR 10-14", "PR 14-20", "FE 08-14", "FE 14-20", "NOTTE"]
    for i, c in enumerate(cols): pdf.cell(w_g if i==0 else w_c, 5, c, 1, 0, 'C')
    pdf.ln()

    pdf.set_font("Helvetica", '', 6.5)
    for _, r in df_clean.iterrows():
        fill = "*" in str(r["GIORNO"])
        pdf.set_fill_color(235, 235, 235) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.cell(w_g, 4.8, str(r["GIORNO"]), 1, 0, 'L', fill=True)
        for k in ["P 10-14", "P 14-20", "F 08-14", "F 14-20", "NOTT 20-08"]:
            pdf.cell(w_c, 4.8, str(r[k]), 1, 0, 'C', fill=True)
        pdf.ln()

    # Riepilogo Firme Sotto la Tabella (Stessa Pagina)
    pdf.ln(3); pdf.set_font("Helvetica", 'B', 8)
    pdf.cell(0, 5, f"RIEPILOGO ORE - TOTALE: {totale_mese}h", ln=True)
    for r in riepilogo:
        pdf.cell(40, 6, f"Dott. {r['Medico']}", 1, 0, 'L')
        pdf.cell(20, 6, f"{r['Ore']} h", 1, 0, 'C')
        pdf.cell(70, 6, " Firma: _________________________", 1, 1, 'L')

    st.download_button("💾 SCARICA PDF FINALE", data=bytes(pdf.output()), file_name=f"Turni_{mese_sel}.pdf", mime="application/pdf", use_container_width=True)

    config = {k: st.column_config.SelectboxColumn(k, options=[""] + st.session_state.medici_lista) for k in ["P 10-14", "P 14-20", "F 08-14", "F 14-20", "NOTT 20-08"]}
    df_ed = st.data_editor(df_clean, hide_index=True, use_container_width=True, column_config=config)
    st.session_state.db = df_ed

# --- 6. TASTO ROSSO GENERA (SOTTO) ---
st.write("---")
if st.button("🚀 GENERA SCHEMA AUTOMATICO", use_container_width=True):
    fest = get_festivita(anno_sel); gg = calendar.monthrange(anno_sel, idx_m)[1]
    rows = []; ven_count = 0; ita_g = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
    for d in range(1, gg + 1):
        dt = datetime(anno_sel, idx_m, d); wd = dt.weekday(); f_n = fest.get((d, idx_m), "")
        is_f = (wd == 6 or f_n != ""); is_p = (wd == 5 or (not is_f and ((dt + timedelta(days=1)).weekday() == 6 or ((dt + timedelta(days=1)).day, (dt + timedelta(days=1)).month) in fest)))
        def get_m(name, fallback_idx): return name if name in medici_attivi else (medici_attivi[fallback_idx % len(medici_attivi)] if medici_attivi else "")
        ass_notte = ""
        if wd in [0, 2]: ass_notte = get_m("Celani", 0)
        elif wd == 1: ass_notte = get_m("Piscopo", 1)
        elif wd == 3: ass_notte = get_m("Lombardo", 2)
        elif wd == 4: ven_count += 1; ass_notte = get_m("Celani", 0) if ven_count % 2 != 0 else get_m("Piscopo", 1)
        elif wd in [5, 6]: ass_notte = get_m("Siracusa", 3)
        ass_diurna = ass_notte if ((is_p or is_f) and ass_notte != "Lombardo") else ""
        rows.append({"GIORNO": f"{'**' if is_f else ('*' if is_p else '')} {d} {ita_g[wd]} {f_n}", "P 10-14": ass_diurna if is_p else "", "P 14-20": ass_diurna if is_p else "", "F 08-14": ass_diurna if is_f else "", "F 14-20": ass_diurna if is_f else "", "NOTT 20-08": ass_notte})
    st.session_state.db = pd.DataFrame(rows); st.rerun()
