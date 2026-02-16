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

with st.sidebar:
    st.header("⚙️ CONFIGURAZIONE")
    medici_base = ["Celani", "Piscopo", "Lombardo", "Siracusa"]
    medici_attuali = st.multiselect("Medici in servizio", options=medici_base, default=medici_base)
    anno_sel = st.number_input("Anno", 2024, 2030, 2026)
    mesi_ita = ["GENNAIO", "FEBBRAIO", "MARZO", "APRILE", "MAGGIO", "GIUGNO", "LUGLIO", "AGOSTO", "SETTEMBRE", "OTTOBRE", "NOVEMBRE", "DICEMBRE"]
    mese_sel = st.selectbox("Mese", mesi_ita, index=datetime.now().month - 1)
    idx_m = mesi_ita.index(mese_sel) + 1
    
    st.write("---")
    st.subheader("📊 Riepilogo Ore")
    placeholder_sidebar = st.container()

# Generazione automatica silenziosa per i dati
fest = get_festivita(anno_sel)
gg = calendar.monthrange(anno_sel, idx_m)[1]
rows = []
ita_g = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]; v_c = 0

for d in range(1, gg + 1):
    dt = datetime(anno_sel, idx_m, d); wd = dt.weekday()
    f_n = fest.get((d, idx_m), ""); is_f = wd == 6 or f_n != ""
    is_p = wd == 5 or (not is_f and ((dt + timedelta(days=1)).weekday() == 6 or ((dt + timedelta(days=1)).day, (dt + timedelta(days=1)).month) in fest))
    
    ass = ""
    if wd in [0, 2]: ass = "Celani"
    elif wd == 1: ass = "Piscopo"
    elif wd == 3: ass = "Lombardo"
    elif wd == 4: v_c += 1; ass = "Celani" if v_c % 2 != 0 else "Piscopo"
    elif wd in [5, 6]: ass = "Siracusa"
    
    prefix = "** " if is_f else ("* " if is_p else "")
    rows.append({
        "GIORNO": f"{prefix}{d} {ita_g[wd]} {f_n}",
        "P 10-14": ass if is_p else "", 
        "P 14-20": ass if is_p else "",
        "F 08-14": ass if is_f else "", 
        "F 14-20": ass if is_f else "", 
        "NOTT 20-08": ass, 
        "hM": 4 if is_p else (6 if is_f else 0),
        "hP": 6 if (is_p or is_f) else 0, 
        "hN": 12, 
        "FESTIVO": is_f or is_p
    })

db_base = pd.DataFrame(rows)

# Editor Tabella
config = {k: st.column_config.SelectboxColumn(k, options=[""] + medici_attuali) for k in ["P 10-14", "P 14-20", "F 08-14", "F 14-20", "NOTT 20-08"]}
df_ed = st.data_editor(db_base, 
                       column_order=("GIORNO", "P 10-14", "P 14-20", "F 08-14", "F 14-20", "NOTT 20-08"),
                       column_config=config, hide_index=True, use_container_width=True).fillna("")

# Calcolo Ore Sidebar
riepilogo = []
for m in medici_attuali:
    if m == "": continue
    o = df_ed[df_ed["P 10-14"]==m]["hM"].sum() + df_ed[df_ed["F 08-14"]==m]["hM"].sum() + \
        df_ed[df_ed["P 14-20"]==m]["hP"].sum() + df_ed[df_ed["F 14-20"]==m]["hP"].sum() + \
        df_ed[df_ed["NOTT 20-08"]==m]["hN"].sum()
    riepilogo.append({"M": m, "O": int(o)})
df_ore = pd.DataFrame(riepilogo); tot = df_ore["O"].sum() if not df_ore.empty else 0

with placeholder_sidebar:
    for _, r in df_ore.iterrows(): st.write(f"**{r['M']}**: {r['O']} h")
    st.markdown(f'<div style="background-color:#1E3A8A;padding:10px;border-radius:8px;text-align:center;"><p style="color:white;font-size:20px;font-weight:bold;margin:0;">{tot} h</p></div>', unsafe_allow_html=True)

# Unico pulsante: SCARICA PDF
if pdf_ok:
    st.write("---")
    pdf = FPDF('P', 'mm', 'A4'); pdf.set_margins(8, 8, 8); pdf.add_page()
    pdf.set_font("Arial", 'B', 10); pdf.cell(0, 6, f"PCA PORTO EMPEDOCLE - {mese_sel} {anno_sel}", 0, 1, 'C'); pdf.ln(2)
    
    w_g, w_c = 38, 31; pdf.set_font("Arial", 'B', 7)
    h_pdf = ["GIORNO", "PR 10-14", "PR 14-20", "FE 08-14", "FE 14-20", "NOT 20-08"]
    for i, head in enumerate(h_pdf): pdf.cell(w_g if i==0 else w_c, 6, head, 1, 0, 'C')
    pdf.ln()

    pdf.set_font("Arial", '', 6.5)
    for _, r in df_ed.iterrows():
        pdf.set_fill_color(235, 235, 235) if r["FESTIVO"] else pdf.set_fill_color(255, 255, 255)
        pdf.cell(w_g, 5.2, str(r["GIORNO"]), 1, 0, 'L', True)
        for k in ["P 10-14", "P 14-20", "F 08-14", "F 14-20", "NOTT 20-08"]:
            val = str(r[k]).strip()
            if val.lower() in ["none", "nan", "0", ""] or val not in medici_attuali: val = ""
            pdf.cell(w_c, 5.2, val, 1, 0, 'C', True)
        pdf.ln()

    pdf.ln(3); pdf.set_font("Arial", 'B', 8); pdf.cell(0, 5, "RIEPILOGO ORE E FIRME", 0, 1, 'L')
    for _, ro in df_ore.iterrows():
        pdf.set_font("Arial", 'B', 7); pdf.cell(50, 7, str(ro["M"]), 1, 0, 'C')
        pdf.cell(30, 7, f"{ro['O']} h", 1, 0, 'C'); pdf.cell(60, 7, " Firma: ________________", 1, 1, 'L')
    
    pdf.set_font("Arial", 'B', 8); pdf.cell(50, 7, "TOTALE MENSILE", 1, 0, 'C')
    pdf.cell(30, 7, f"{tot} h", 1, 0, 'C'); pdf.cell(60, 7, "", 1, 1, 'C')
    
    st.download_button("📄 SCARICA IL PDF DEI TURNI", pdf.output(dest='S').encode('latin-1'), f"Turni_{mese_sel}.pdf", "application/pdf", use_container_width=True)
