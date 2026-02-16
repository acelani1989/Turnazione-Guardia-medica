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

# --- LOGICA CALCOLI ---
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

# --- GESTIONE MEDICI ---
if 'lista_medici' not in st.session_state:
    st.session_state.lista_medici = ["Celani", "Piscopo", "Lombardo", "Siracusa"]

with st.sidebar:
    st.header("⚙️ CONFIGURAZIONE")
    medici_attuali = st.multiselect("Medici in servizio", options=st.session_state.lista_medici, default=st.session_state.lista_medici)
    anno_sel = st.number_input("Anno", 2024, 2030, 2026)
    mesi_ita = ["GENNAIO", "FEBBRAIO", "MARZO", "APRILE", "MAGGIO", "GIUGNO", "LUGLIO", "AGOSTO", "SETTEMBRE", "OTTOBRE", "NOVEMBRE", "DICEMBRE"]
    mese_sel = st.selectbox("Mese", mesi_ita, index=datetime.now().month - 1)
    idx_m = mesi_ita.index(mese_sel) + 1

if st.button("🚀 GENERA SCHEMA AUTOMATICO", type="primary", use_container_width=True):
    fest = get_festivita(anno_sel)
    gg = calendar.monthrange(anno_sel, idx_m)[1]
    rows = []
    ita_g = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
    
    ven_count = 0 # Per gestire l'alternanza dei venerdì
    
    for d in range(1, gg + 1):
        dt = datetime(anno_sel, idx_m, d)
        wd = dt.weekday() # 0=Lun, 4=Ven, 5=Sab, 6=Dom
        f_n = fest.get((d, idx_m), "")
        is_f = wd == 6 or f_n != ""
        is_p = wd == 5 or (not is_f and ((dt + timedelta(days=1)).weekday() == 6 or ((dt + timedelta(days=1)).day, (dt + timedelta(days=1)).month) in fest))
        
        # --- APPLICAZIONE LOGICA DISPONIBILITÀ ---
        assegnato = ""
        if wd == 0: assegnato = "Celani"
        elif wd == 1: assegnato = "Piscopo"
        elif wd == 2: assegnato = "Celani"
        elif wd == 3: assegnato = "Lombardo"
        elif wd == 4: # Venerdì alternati (2 a testa)
            ven_count += 1
            assegnato = "Celani" if ven_count <= 2 else "Piscopo"
        elif wd == 5 or wd == 6: assegnato = "Siracusa"

        prefix = "** " if is_f else ("* " if is_p else "")
        label = f"{prefix}{d} {ita_g[wd]} {f_n}"
        
        # Riempimento automatico in base al tipo di turno
        rows.append({
            "GIORNO": label, 
            "P 10-14": assegnato if is_p else "", 
            "P 14-20": assegnato if is_p else "", 
            "F 08-14": assegnato if is_f else "", 
            "F 14-20": assegnato if is_f else "", 
            "NOTT 20-08": assegnato if not (is_p or is_f) else assegnato, 
            "hM": 4 if is_p else (6 if is_f else 0), 
            "hP": 6 if (is_p or is_f) else 0, 
            "hN": 12, 
            "TIPO": "E" if (is_f or is_p) else "N"
        })
    st.session_state.db = pd.DataFrame(rows)

if 'db' in st.session_state:
    # Definizione colonne con menu a tendina
    column_config = {
        "P 10-14": st.column_config.SelectboxColumn("P 10-14", options=medici_attuali),
        "P 14-20": st.column_config.SelectboxColumn("P 14-20", options=medici_attuali),
        "F 08-14": st.column_config.SelectboxColumn("F 08-14", options=medici_attuali),
        "F 14-20": st.column_config.SelectboxColumn("F 14-20", options=medici_attuali),
        "NOTT 20-08": st.column_config.SelectboxColumn("NOTT 20-08", options=medici_attuali),
    }

    df_ed = st.data_editor(st.session_state.db, 
                           column_order=("GIORNO", "P 10-14", "P 14-20", "F 08-14", "F 14-20", "NOTT 20-08"), 
                           column_config=column_config,
                           hide_index=True, use_container_width=True)

    # Calcolo Ore
    riepilogo = []
    for m in medici_attuali:
        ore = df_ed[df_ed["P 10-14"]==m]["hM"].sum() + df_ed[df_ed["F 08-14"]==m]["hM"].sum() + \
              df_ed[df_ed["P 14-20"]==m]["hP"].sum() + df_ed[df_ed["F 14-20"]==m]["hP"].sum() + \
              df_ed[df_ed["NOTT 20-08"]==m]["hN"].sum()
        riepilogo.append({"Medico": m, "Ore Totali": int(ore)})
    df_ore = pd.DataFrame(riepilogo)

    # Bottoni Export
    c1, c2 = st.columns(2)
    with c1:
        buf_ex = io.BytesIO()
        with pd.ExcelWriter(buf_ex, engine='xlsxwriter') as writer:
            df_ed.drop(columns=["hM","hP","hN","TIPO"]).to_excel(writer, index=False, sheet_name='Turni')
            df_ore.to_excel(writer, index=False, sheet_name='Ore')
        st.download_button("📥 EXCEL", buf_ex.getvalue(), "Turni.xlsx", use_container_width=True)

    with c2:
        if pdf_ok and st.button("📄 GENERA PDF", use_container_width=True):
            pdf = FPDF('P', 'mm', 'A4')
            pdf.set_margins(8, 8, 8)
            pdf.add_page()
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(0, 6, "PCA PORTO EMPEDOCLE - TURNI E ORE", 0, 1, 'C')
            pdf.cell(0, 6, f"{mese_sel} {anno_sel}", 0, 1, 'C')
            pdf.ln(2)
            
            w_g, w_c = 38, 31
            pdf.set_font("Arial", 'B', 7)
            h = ["GIORNO", "PR 10-14", "PR 14-20", "FE 08-14", "FE 14-20", "NOT 20-08"]
            for i, col in enumerate(h): pdf.cell(w_g if i==0 else w_c, 6, col, 1, 0, 'C')
            pdf.ln()
            
            pdf.set_font("Arial", '', 6.5)
            for _, r in df_ed.iterrows():
                pdf.set_fill_color(200, 200, 200) if r["TIPO"] == "E" else pdf.set_fill_color(255, 255, 255)
                pdf.cell(w_g, 5.2, str(r["GIORNO"]), 1, 0, 'L', True)
                for k in ["P 10-14", "P 14-20", "F 08-14", "F 14-20", "NOTT 20-08"]:
                    val = str(r[k]) if r[k] and str(r[k]) != "None" else ""
                    pdf.cell(w_c, 5.2, val, 1, 0, 'C', True)
                pdf.ln()
            
            pdf.ln(2)
            pdf.set_font("Arial", 'B', 8)
            pdf.cell(0, 5, "RIEPILOGO ORE E FIRME", 0, 1, 'L')
            pdf.set_font("Arial", 'B', 7)
            pdf.cell(50, 6, "MEDICO", 1, 0, 'C'); pdf.cell(30, 6, "ORE", 1, 0, 'C'); pdf.cell(60, 6, "FIRMA", 1, 1, 'C')
            for _, row_o in df_ore.iterrows():
                pdf.set_font("Arial", 'B', 7)
                pdf.cell(50, 8, str(row_o["Medico"]), 1, 0, 'C')
                pdf.set_font("Arial", '', 7)
                pdf.cell(30, 8, str(row_o["Ore Totali"]), 1, 0, 'C')
                pdf.cell(60, 8, "", 1, 1, 'C')
            
            st.download_button("💾 SALVA PDF", pdf.output(dest='S').encode('latin-1'), "Turni.pdf", "application/pdf", use_container_width=True)
