import streamlit as st
import pandas as pd
import calendar
import io
from datetime import datetime, timedelta
from fpdf import FPDF

# --- CONFIGURAZIONE INTERFACCIA ---
st.set_page_config(page_title="Gestione Turni PCA", layout="wide")

# CSS DRACONIANO: Elimina definitivamente ogni scritta automatica "None" o alert
st.markdown("""
    <style>
    header, footer, .stDeployButton, .stException {display: none !important;}
    [data-testid="stElementToolbar"] {display: none !important;}
    .stAlert, .st-emotion-cache-1ghh6y0, .st-emotion-cache-1wivap2, 
    .st-emotion-cache-zt5igj, .st-emotion-cache-1kyx7g1, .st-emotion-cache-1v0649j {
        display: none !important;
    }
    div.stButton > button:first-child { 
        background-color: #ff4b4b !important; 
        color: white !important; 
        font-weight: bold !important; 
        height: 3em;
        width: 100%; 
    }
    .stDataFrame { margin-top: -20px; }
    </style>
    """, unsafe_allow_html=True)

# --- STATO DELL'APPLICAZIONE ---
if 'db' not in st.session_state: st.session_state.db = None
if 'medici' not in st.session_state: st.session_state.medici = ["Celani", "Piscopo", "Lombardo", "Siracusa"]

# --- SIDEBAR ---
with st.sidebar:
    st.header("IMPOSTAZIONI")
    anno = st.number_input("Anno", 2024, 2030, 2025)
    mesi = ["GENNAIO", "FEBBRAIO", "MARZO", "APRILE", "MAGGIO", "GIUGNO", "LUGLIO", "AGOSTO", "SETTEMBRE", "OTTOBRE", "NOVEMBRE", "DICEMBRE"]
    mese = st.selectbox("Mese", mesi, index=datetime.now().month - 1)
    idx_m = mesi.index(mese) + 1
    
    st.write("---")
    new_m = st.text_input("Aggiungi Medico")
    if st.button("Inserisci"):
        if new_m and new_m not in st.session_state.medici:
            st.session_state.medici.append(new_m)
            st.rerun()

# --- FUNZIONI TECNICHE ---
def get_festivi(y):
    def p(y):
        a,b,c=y%19,y//100,y%100; d,e=b//4,b%4; f,g=(b+8)//25,(b-(b+8)//25+1)//3; h=(19*a+b-d-g+15)%30; i,k=c//4,c%4; l=(32+2*e+2*i-h-k)%7; m=(a+11*h+22*l)//451
        mese=(h+l-7*m+114)//31; giorno=((h+l-7*m+114)%31)+1
        return datetime(y, mese, giorno)
    pas = p(y); pasq = pas + timedelta(days=1)
    return {(1,1):"Capodanno",(6,1):"Epifania",(25,2):"Patrono",(25,4):"Liberazione",(1,5):"Lavoro",(2,6):"Repubblica",(15,8):"Ferragosto",(1,11):"Ognissanti",(8,12):"Immacolata",(25,12):"Natale",(26,12):"S.Stefano",(pas.day,pas.month):"Pasqua",(pasq.day,pasq.month):"Pasquetta"}

def calcola_ore(df):
    res = []; tot = 0
    for m in st.session_state.medici:
        o_p = (df["P 10-14"] == m).sum() * 4
        o_f = ((df["F 08-14"] == m).sum() * 6) + ((df["F 14-20"] == m).sum() * 6) + ((df["P 14-20"] == m).sum() * 6)
        o_n = (df["NOTTE"] == m).sum() * 12
        t = o_p + o_f + o_n
        if t > 0: res.append(f"**{m}**: {int(t)}h"); tot += t
    return " | ".join(res), int(tot)

# --- LAYOUT PRINCIPALE ---
st.title(f"PCA PORTO EMPEDOCLE - {mese} {anno}")

# 1. TASTO GENERA
if st.button("🚀 GENERA SCHEMA TURNI"):
    f_list = get_festivi(anno); gg = calendar.monthrange(anno, idx_m)[1]
    rows = []; ven_c = 0; ita_g = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
    for d in range(1, gg + 1):
        dt = datetime(anno, idx_m, d); wd = dt.weekday(); f_n = f_list.get((d, idx_m), "")
        is_f = (wd == 6 or f_n != ""); is_p = (wd == 5 or (not is_f and ((dt + timedelta(days=1)).weekday() == 6 or ((dt + timedelta(days=1)).day, (dt + timedelta(days=1)).month) in f_list)))
        def g_m(name, alt): return name if name in st.session_state.medici else (st.session_state.medici[alt % len(st.session_state.medici)] if st.session_state.medici else "")
        nott = ""
        if wd in [0, 2]: nott = g_m("Celani", 0)
        elif wd == 1: nott = g_m("Piscopo", 1)
        elif wd == 3: nott = g_m("Lombardo", 2)
        elif wd == 4: ven_c += 1; nott = g_m("Celani", 0) if ven_c % 2 != 0 else g_m("Piscopo", 1)
        elif wd in [5, 6]: nott = g_m("Siracusa", 3)
        diu = nott if ((is_p or is_f) and nott != "Lombardo") else ""
        rows.append({"GIORNO": f"{'**' if is_f else ('*' if is_p else '')} {d} {ita_g[wd]} {f_n}", "P 10-14": diu if is_p else "", "P 14-20": diu if is_p else "", "F 08-14": diu if is_f else "", "F 14-20": diu if is_f else "", "NOTTE": nott})
    st.session_state.db = pd.DataFrame(rows)
    st.rerun()

# 2. SEZIONE PDF E TABELLA
if st.session_state.db is not None:
    df_c = st.session_state.db.fillna("").replace(["None", "nan", 0, "0.0"], "")
    ore_testo, ore_tot = calcola_ore(df_c)

    # Creazione PDF (Interna)
    pdf = FPDF(); pdf.set_auto_page_break(False); pdf.add_page(); pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(0, 8, f"PCA PORTO EMPEDOCLE - {mese} {anno}", ln=True, align='C')
    pdf.set_font("Helvetica", 'B', 7); w_g, w_c = 38, 30
    header = ["GIORNO", "PR 10-14", "PR 14-20", "FE 08-14", "FE 14-20", "NOTTE"]
    for i, h in enumerate(header): pdf.cell(w_g if i==0 else w_c, 5, h, 1, 0, 'C')
    pdf.ln()
    pdf.set_font("Helvetica", '', 6)
    for _, r in df_c.iterrows():
        f = "*" in str(r["GIORNO"]); pdf.set_fill_color(240, 240, 240) if f else pdf.set_fill_color(255, 255, 255)
        pdf.cell(w_g, 4.6, str(r["GIORNO"]), 1, 0, 'L', fill=True)
        for k in ["P 10-14", "P 14-20", "F 08-14", "F 14-20", "NOTTE"]: pdf.cell(w_c, 4.6, str(r[k]), 1, 0, 'C', fill=True)
        pdf.ln()
    pdf.ln(2); pdf.set_font("Helvetica", 'B', 8); pdf.cell(0, 5, f"RIEPILOGO E FIRME - TOTALE: {ore_tot}h", ln=True)
    for m_info in ore_testo.split(" | "):
        pdf.cell(50, 6, m_info.replace("**",""), 1, 0, 'L'); pdf.cell(80, 6, " Firma: ________________________", 1, 1, 'L')

    # TASTO DOWNLOAD
    st.download_button("💾 SCARICA PDF FINALE", data=bytes(pdf.output()), file_name=f"Turni_{mese}.pdf", mime="application/pdf")

    # TABELLA EDITOR
    cfg = {k: st.column_config.SelectboxColumn(k, options=[""] + st.session_state.medici) for k in ["P 10-14", "P 14-20", "F 08-14", "F 14-20", "NOTTE"]}
    st.session_state.db = st.data_editor(df_c, hide_index=True, use_container_width=True, column_config=cfg, key="editor_v3")

    # 3. RIEPILOGO ORE (IN BASSO)
    st.write("---")
    st.markdown(f"### **TOTALE ORE: {ore_tot}h**")
    st.markdown(ore_testo)
