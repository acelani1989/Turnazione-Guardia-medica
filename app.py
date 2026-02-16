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

# --- LOGICA CALCOLI FESTIVITÀ ---
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
    return {(1,1):"Capod.",(6,1):"Epif.",(25,2):"Patr.",(25,4):"Lib.",(1,5):"Lav.",(2,6):"Rep.",(15,8):"Ferr.",(1,11):"Ognis.",(8,12):"Immac.",(25,12):"Nat.",(26,12):"Stef.",(p.day,p.month):"Pasqua",(pp.day,pp.month):"Pasqu."}

st.set_page_config(page_title="Turni PCA Porto Empedocle", layout="wide")
st.markdown("### PRESIDIO DI CONTINUITA’ ASSISTENZIALE PORTO EMPEDOCLE")

if 'lista_medici' not in st.session_state:
    st.session_state.lista_medici = ["Celani", "Piscopo", "Lombardo", "Siracusa"]

with st.sidebar:
    st.header("⚙️ CONFIGURAZIONE")
    # Aggiungiamo un'opzione vuota all'inizio della lista per permettere di sbiancare le celle
    opzioni_medici = [""] + st.session_state.lista_medici
    anno_sel = st.number_input("Anno", 2024, 2030, 2026)
    mesi_ita = ["GENNAIO", "FEBBRAIO", "MARZO", "APRILE", "MAGGIO", "GIUGNO", "LUGLIO", "AGOSTO", "SETTEMBRE", "OTTOBRE", "NOVEMBRE", "DICEMBRE"]
    mese_sel = st.selectbox("Mese", mesi_ita, index=datetime.now().month - 1)
    idx_m = mesi_ita.index(mese_sel) + 1

if st.button("🚀 GENERA SCHEMA AUTOMATICO", type="primary", use_container_width=True):
    fest = get_festivita(anno_sel)
    gg = calendar.monthrange(anno_sel, idx_m)[1]
    rows = []
    ita_g = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
    ven_count = 0
    
    for d in range(1, gg + 1):
        dt = datetime(anno_sel, idx_m, d)
        wd = dt.weekday()
        f_n = fest.get((d, idx_m), "")
        is_f = wd == 6 or f_n != ""
        is_p = wd == 5 or (not is_f and ((dt + timedelta(days=1)).weekday() == 6 or ((dt + timedelta(days=1)).day, (dt + timedelta(days=1)).month) in fest))
        
        assegnato = ""
        if wd == 0 or wd == 2: assegnato = "Celani"
        elif wd == 1: assegnato = "Piscopo"
        elif wd == 3: assegnato = "Lombardo"
        elif wd == 4:
            ven_count += 1
            assegnato = "Celani" if ven_count % 2 != 0 else "Piscopo"
        elif wd == 5 or wd == 6: assegnato = "Siracusa"

        prefix = "** " if is_f else ("* " if is_p else "")
        label = f"{prefix}{d} {ita_g[wd]} {f_n}"
        
        # Inizializziamo tutto come stringa vuota invece di None
        rows.append({
            "GIORNO": str(label), 
            "P 10-14": str(assegnato) if is_p else "", 
            "P 14-20": str(assegnato) if is_p else "",
            "F 08-14": str(assegnato) if is_f else "", 
            "F 14-20": str(assegnato) if is_f else "", 
            "NOTT 20-08": str(assegnato) if assegnato else "",
            "hM": 4 if is_p else (6 if is_f else 0), 
            "hP": 6 if (is_p or is_f) else 0, 
            "hN": 12, 
            "TIPO": "E" if (is_f or is_p) else "N"
        })
    st.session_state.db = pd.DataFrame(rows)

if 'db' in st.session_state:
    # Configuriamo le colonne in modo che il default sia "" e non None
    column_config = {
        k: st.column_config.SelectboxColumn(k, options=opzioni_medici, width="medium") 
        for k in ["P 10-14", "P 14-20", "F 08-14", "F 14-20", "NOTT 20-08"]
    }

    # Pulizia forzata prima della visualizzazione
    df_visual = st.session_state.db.copy().fillna("").astype(str)
    df_visual = df_visual.replace(["None", "nan", "NaN", "None"], "")

    df_ed = st.data_editor(
        df_visual, 
        column_order=("GIORNO", "P 10-14", "P 14-20", "F 08-14", "F 14-20", "NOTT 20-08"), 
        column_config=column_config,
        hide_index=True, 
        use_container_width=True
    )

    # Ricalcolo Ore Reattivo
    riepilogo = []
    medici_reali = [m for m in st.session_state.lista_medici if m != ""]
    for m in medici_reali:
        ore = (df_ed[df_ed["P 10-14"]==m]["hM"].astype(float).sum() + 
               df_ed[df_ed["F 08-14"]==m]["hM"].astype(float).sum() +
               df_ed[df_ed["P 14-20"]==m]["hP"].astype(float).sum() + 
               df_ed[df_ed["F 14-20"]==m]["hP"].astype(float).sum() + 
               df_ed[df_ed["NOTT 20-08"]==m]["hN"].astype(float).sum())
        riepilogo.append({"Medico": m, "Ore Totali": int(ore)})
    df_ore = pd.DataFrame(riepilogo)

    # Pulsanti Download
    c1, c2 = st.columns(2)
    with c1:
        buf_ex = io.BytesIO()
        with pd.ExcelWriter(buf_ex, engine='xlsxwriter') as writer:
            df_ed.drop(columns=["hM","hP","hN","TIPO"]).to_excel(writer, index=False)
        st.download_button("📥 SCARICA EXCEL", buf_ex.getvalue(), "Turni.xlsx", use_container_width=True)

    with c2:
        if pdf_ok and st.button("📄 SCARICA PDF", use_container_width=True):
            pdf = FPDF('P', 'mm', 'A4')
            pdf.set_margins(8, 8, 8); pdf.add_page(); pdf.set_font("Arial", 'B', 10)
            pdf.cell(0, 6, "PCA PORTO EMPEDOCLE", 0, 1, 'C')
            pdf.cell(0, 6, f"{mese_sel} {anno_sel}", 0, 1, 'C'); pdf.ln(2)
            
            w_g, w_c = 38, 31
            pdf.set_font("Arial", 'B', 7)
            h_list = ["GIORNO", "PR 10-14", "PR 14-20", "FE 08-14", "FE 14-20", "NOT 20-08"]
            for i, h in enumerate(h_list): pdf.cell(w_g if i==0 else w_c, 6, h, 1, 0, 'C')
            pdf.ln()
            
            pdf.set_font("Arial", '', 6.5)
            for _, r in df_ed.iterrows():
                pdf.set_fill_color(220, 220, 220) if r["TIPO"] == "E" else pdf.set_fill_color(255, 255, 255)
                pdf.cell(w_g, 5.5, str(r["GIORNO"]), 1, 0, 'L', True)
                for k in ["P 10-14", "P 14-20", "F 08-14", "F 14-20", "NOTT 20-08"]:
                    # FILTRO ANTI-NONE DEFINITIVO
                    val = str(r[k]).replace("None", "").replace("nan", "").strip()
                    pdf.cell(w_c, 5.5, val, 1, 0, 'C', True)
                pdf.ln()
            
            pdf.ln(5); pdf.set_font("Arial", 'B', 8); pdf.cell(0, 5, "RIEPILOGO ORE E FIRME", 0, 1, 'L')
            pdf.set_font("Arial", '', 7)
            for _, row_o in df_ore.iterrows():
                pdf.cell(50, 8, f"{row_o['Medico']}: {row_o['Ore Totali']} ore", 1, 0, 'L')
                pdf.cell(70, 8, " Firma: __________________________", 1, 1, 'L')
            
            st.download_button("💾 SALVA PDF", pdf.output(dest='S').encode('latin-1'), "Turni.pdf", "application/pdf", use_container_width=True)

    # Riepilogo Ore Ingrandito
    st.write("---")
    tot_h = df_ore['Ore Totali'].sum()
    st.markdown(f"""
        <div style="background-color:#003049; padding:25px; border-radius:15px; text-align:center; border: 3px solid #669bbc;">
            <p style="color:#669bbc; font-size:22px; font-weight:bold; margin-bottom:0;">TOTALE ORE MENSILI</p>
            <p style="color:white; font-size:90px; font-weight:bold; margin:0;">{tot_h} <span style="font-size:35px;">ore</span></p>
        </div>
    """, unsafe_allow_html=True)
