import streamlit as st
import pandas as pd
import calendar
import io
from datetime import datetime, timedelta

# Importazione FPDF
try:
    from fpdf import FPDF
except ImportError:
    st.error("Libreria FPDF non trovata. Aggiungi 'fpdf2' al file requirements.txt")

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
    /* Rende il tasto GENERA rosso */
    div.stButton > button:first-child {
        background-color: #ff4b4b;
        color: white;
        border: none;
    }
    /* Nasconde eventuali scritte residue di Streamlit in fondo alle tabelle */
    .st-emotion-cache-1ghh6y0, .st-emotion-cache-1wivap2 {
        display: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("### PRESIDIO DI CONTINUITA’ ASSISTENZIALE PORTO EMPEDOCLE")

if 'db' not in st.session_state:
    st.session_state.db = None
if 'medici_lista' not in st.session_state:
    st.session_state.medici_lista = ["Celani", "Piscopo", "Lombardo", "Siracusa"]

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ CONFIGURAZIONE")
    new_med = st.text_input("➕ Aggiungi nuovo medico")
    if st.button("Aggiungi"):
        if new_med and new_med not in st.session_state.medici_lista:
            st.session_state.medici_lista.append(new_med)
            st.rerun()
    
    st.subheader("👨‍⚕️ Medici in Servizio")
    medici_attivi = st.multiselect("Medici attivi:", options=st.session_state.medici_lista, default=st.session_state.medici_lista)
    
    with st.expander("🗑️ Rimuovi medici"):
        for m in st.session_state.medici_lista:
            if st.button(f"Elimina {m}", key=f"del_{m}"):
                st.session_state.medici_lista.remove(m)
                st.rerun()

    st.write("---")
    anno_sel = st.number_input("Anno", 2024, 2030, 2026)
    mesi_ita = ["GENNAIO", "FEBBRAIO", "MARZO", "APRILE", "MAGGIO", "GIUGNO", "LUGLIO", "AGOSTO", "SETTEMBRE", "OTTOBRE", "NOVEMBRE", "DICEMBRE"]
    mese_sel = st.selectbox("Mese", mesi_ita, index=datetime.now().month - 1)
    idx_m = mesi_ita.index(mese_sel) + 1
    placeholder_ore = st.empty()

# --- 4. TASTO ROSSO GENERA ---
if st.button("🚀 GENERA SCHEMA AUTOMATICO", use_container_width=True):
    if not medici_attivi:
        st.warning("Seleziona i medici dalla sidebar!")
    else:
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
                "P 10-14": ass_diurna if is_p else "", 
                "P 14-20": ass_diurna if is_p else "",
                "F 08-14": ass_diurna if is_f else "", 
                "F 14-20": ass_diurna if is_f else "",
                "NOTT 20-08": ass_notte,
                "TIPO": "FEST" if is_f else ("PREF" if is_p else "FER")
            })
        st.session_state.db = pd.DataFrame(rows)

# --- 5. VISUALIZZAZIONE ---
if st.session_state.db is not None:
    # PULIZIA DRACONIANA: Trasforma ogni None o valore nullo in stringa vuota ""
    st.session_state.db = st.session_state.db.fillna("").replace(["None", "nan", "NaN", "0", 0, 0.0, "0.0"], "")

    # Calcolo Ore
    riepilogo_medici = []
    tot_ore_mese = 0
    for m in st.session_state.medici_lista:
        db = st.session_state.db
        o = (db[db["P 10-14"]==m].shape[0]*4) + (db[db["F 08-14"]==m].shape[0]*6) + \
            (db[db["P 14-20"]==m].shape[0]*6) + (db[db["F 14-20"]==m].shape[0]*6) + \
            (db[db["NOTT 20-08"]==m].shape[0]*12)
        if o > 0:
            riepilogo_medici.append((m, int(o)))
            tot_ore_mese += int(o)

    with placeholder_ore.container():
        st.subheader("📊 Ore Medici")
        for m, o in riepilogo_medici: st.write(f"**{m}**: {o} h")
        st.markdown(f'<div style="background-color:#1E3A8A;padding:10px;border-radius:8px;text-align:center;"><p style="color:white;font-size:20px;font-weight:bold;margin:0;">TOT: {tot_ore_mese} h</p></div>', unsafe_allow_html=True)

    # Preparazione PDF
    pdf = FPDF('P', 'mm', 'A4')
    pdf.set_margins(7, 10, 7)
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 6, f"PCA PORTO EMPEDOCLE - {mese_sel} {anno_sel}", align='C', ln=1)
    pdf.ln(2)
    w_g, w_c = 42, 30
    pdf.set_font("helvetica", 'B', 7)
    for i, col_name in enumerate(["GIORNO", "PR 10-14", "PR 14-20", "FE 08-14", "FE 14-20", "NOT 20-08"]):
        pdf.cell(w_g if i==0 else w_c, 6, col_name, 1, 0, 'C')
    pdf.ln()
    pdf.set_font("helvetica", '', 6.5)
    for _, r in st.session_state.db.iterrows():
        fill = "*" in str(r["GIORNO"])
        pdf.set_fill_color(240, 240, 240) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.cell(w_g, 5.2, str(r["GIORNO"]), 1, 0, 'L', fill=True)
        for k in ["P 10-14", "P 14-20", "F 08-14", "F 14-20", "NOTT 20-08"]:
            val = str(r[k]) if str(r[k]).strip() != "" else ""
            pdf.cell(w_c, 5.2, val, 1, 0, 'C', fill=True)
        pdf.ln()
    pdf.ln(5); pdf.set_font("helvetica", 'B', 8); pdf.cell(0, 6, "RIEPILOGO ORE E FIRME", ln=1)
    for m, o in riepilogo_medici:
        pdf.set_font("helvetica", 'B', 7); pdf.cell(45, 7, str(m), 1, 0, 'C')
        pdf.cell(20, 7, f"{o} h", 1, 0, 'C'); pdf.cell(70, 7, " Firma: ________________", 1, 1, 'L')

    # DOWNLOAD E TABELLA SOTTO TASTO ROSSO
    st.write("---")
    st.download_button("💾 SCARICA PDF FINALE", bytes(pdf.output()), f"Turni_{mese_sel}.pdf", use_container_width=True)

    # Configurazione editor per eliminare scritte "None" verdi
    config = {k: st.column_config.SelectboxColumn(k, options=[""] + st.session_state.medici_lista, required=False) for k in ["P 10-14", "P 14-20", "F 08-14", "F 14-20", "NOTT 20-08"]}
    
    # L'editor ora riceve un DF dove ogni None è già "" (stringa vuota)
    df_ed = st.data_editor(
        st.session_state.db, 
        column_order=("GIORNO", "P 10-14", "P 14-20", "F 08-14", "F 14-20", "NOTT 20-08"),
        column_config=config, 
        hide_index=True, 
        use_container_width=True,
        key="editor_fina"
    )
    st.session_state.db = df_ed
