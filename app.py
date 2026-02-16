import streamlit as st
import pandas as pd
import calendar
import io
import base64
from datetime import datetime, timedelta

# Importazione FPDF (gestisce sia fpdf che fpdf2)
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

# --- 2. SETUP E SESSION STATE ---
st.set_page_config(page_title="Turni PCA Porto Empedocle", layout="wide")
st.markdown("### PRESIDIO DI CONTINUITA’ ASSISTENZIALE PORTO EMPEDOCLE")

if 'db' not in st.session_state:
    st.session_state.db = None
if 'medici_lista' not in st.session_state:
    st.session_state.medici_lista = ["Celani", "Piscopo", "Lombardo", "Siracusa"]

# --- 3. SIDEBAR: MEDICI E BACKUP ---
with st.sidebar:
    st.header("⚙️ CONFIGURAZIONE")
    new_med = st.text_input("➕ Aggiungi nuovo medico")
    if st.button("Aggiungi alla lista"):
        if new_med and new_med not in st.session_state.medici_lista:
            st.session_state.medici_lista.append(new_med)
            st.rerun()
    
    st.write("---")
    medici_attuali = st.multiselect("Medici in servizio", options=st.session_state.medici_lista, default=st.session_state.medici_lista)
    
    anno_sel = st.number_input("Anno", 2024, 2030, 2026)
    mesi_ita = ["GENNAIO", "FEBBRAIO", "MARZO", "APRILE", "MAGGIO", "GIUGNO", "LUGLIO", "AGOSTO", "SETTEMBRE", "OTTOBRE", "NOVEMBRE", "DICEMBRE"]
    mese_sel = st.selectbox("Mese", mesi_ita, index=datetime.now().month - 1)
    idx_m = mesi_ita.index(mese_sel) + 1
    
    st.write("---")
    placeholder_sidebar = st.container() # Spazio per il riepilogo ore
    
    st.write("---")
    st.subheader("💾 Backup Dati (Excel)")
    
    # PULSANTE SCARICA BACKUP (ESPORTA)
    if st.session_state.db is not None:
        buffer = io.BytesIO()
        try:
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                st.session_state.db.to_excel(writer, sheet_name='Turni', index=False)
                pd.DataFrame({"ListaMedici": st.session_state.medici_lista}).to_excel(writer, sheet_name='Anagrafica', index=False)
            
            st.download_button(
                label="📤 SCARICA BACKUP", 
                data=buffer.getvalue(), 
                file_name=f"backup_turni_{mese_sel}_{anno_sel}.xlsx", 
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Errore creazione backup: {e}")
    
    # CARICA BACKUP (IMPORTA)
    uploaded_file = st.file_uploader("📥 IMPORTA BACKUP", type=["xlsx"], label_visibility="collapsed")
    if uploaded_file is not None:
        try:
            st.session_state.db = pd.read_excel(uploaded_file, sheet_name='Turni')
            df_medici = pd.read_excel(uploaded_file, sheet_name='Anagrafica')
            st.session_state.medici_lista = df_medici["ListaMedici"].tolist()
            st.success("Backup caricato con successo!")
            st.rerun()
        except Exception as e:
            st.error("Errore: assicurati che il file sia un backup valido.")

# --- 4. LOGICA GENERAZIONE TURNI ---
if st.button("🚀 GENERA SCHEMA AUTOMATICO", type="primary", use_container_width=True):
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
        
        # Regole Assegnazione Notturna
        ass_notte = ""
        if wd in [0, 2]: ass_notte = "Celani"
        elif wd == 1: ass_notte = "Piscopo"
        elif wd == 3: ass_notte = "Lombardo"
        elif wd == 4: 
            ven_count += 1
            ass_notte = "Celani" if ven_count % 2 != 0 else "Piscopo"
        elif wd in [5, 6]: ass_notte = "Siracusa"
        
        # Diurni: Solo se Prefestivo/Festivo E se NON è Lombardo
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
    st.session_state.db = pd.DataFrame(rows).replace([None, "nan", "0"], "")

# --- 5. EDITOR E CALCOLO ORE ---
if st.session_state.db is not None:
    config = {k: st.column_config.SelectboxColumn(k, options=[""] + st.session_state.medici_lista) for k in ["P 10-14", "P 14-20", "F 08-14", "F 14-20", "NOTT 20-08"]}
    df_ed = st.data_editor(st.session_state.db, column_order=("GIORNO", "P 10-14", "P 14-20", "F 08-14", "F 14-20", "NOTT 20-08"),
                           column_config=config, hide_index=True, use_container_width=True)
    st.session_state.db = df_ed

    riepilogo = []
    for m in st.session_state.medici_lista:
        o_pref = df_ed[(df_ed["P 10-14"] == m) & (df_ed["TIPO"] == "PREF")].shape[0] * 4
        o_fest = df_ed[(df_ed["F 08-14"] == m) & (df_ed["TIPO"] == "FEST")].shape[0] * 6
        o_pom = (df_ed[df_ed["P 14-20"] == m].shape[0] * 6) + (df_ed[df_ed["F 14-20"] == m].shape[0] * 6)
        o_not = df_ed[df_ed["NOTT 20-08"] == m].shape[0] * 12
        tot = int(o_pref + o_fest + o_pom + o_not)
        if tot > 0: riepilogo.append({"Medico": m, "Ore": tot})
    
    df_ore = pd.DataFrame(riepilogo)
    tot_mensile = df_ore['Ore'].sum() if not df_ore.empty else 0

    with placeholder_sidebar:
        st.subheader("📊 Ore Medici")
        for _, r in df_ore.iterrows(): st.write(f"**{r['Medico']}**: {r['Ore']} h")
        st.markdown(f'<div style="background-color:#1E3A8A;padding:10px;border-radius:8px;text-align:center;"><p style="color:white;font-size:22px;font-weight:bold;margin:0;">{tot_mensile} h</p></div>', unsafe_allow_html=True)

    # --- 6. PDF ---
    st.write("---")
    col1, col2 = st.columns(2)
    
    pdf = FPDF('P', 'mm', 'A4')
    pdf.set_margins(7, 10, 7)
    pdf.add_page()
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 6, f"PCA PORTO EMPEDOCLE - {mese_sel} {anno_sel}", 0, 1, 'C')
    pdf.ln(2)

    w_g, w_c = 42, 30
    pdf.set_font("Arial", 'B', 7)
    h_p = ["GIORNO", "PR 10-14", "PR 14-20", "FE 08-14", "FE 14-20", "NOT 20-08"]
    for i, txt in enumerate(h_p): pdf.cell(w_g if i==0 else w_c, 6, txt, 1, 0, 'C')
    pdf.ln()

    pdf.set_font("Arial", '', 6.5)
    for _, r in df_ed.iterrows():
        fill = "*" in str(r["GIORNO"])
        pdf.set_fill_color(235, 235, 235) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.cell(w_g, 5.2, str(r["GIORNO"]), 1, 0, 'L', True)
        for k in ["P 10-14", "P 14-20", "F 08-14", "F 14-20", "NOTT 20-08"]:
            val = str(r[k]).strip() if str(r[k]) not in ["None", "nan", ""] else ""
            pdf.cell(w_c, 5.2, val, 1, 0, 'C', True)
        pdf.ln()

    pdf.ln(4); pdf.set_font("Arial", 'B', 8); pdf.cell(0, 5, "RIEPILOGO ORE E FIRME", 0, 1, 'L')
    for _, ro in df_ore.iterrows():
        pdf.set_font("Arial", 'B', 7)
        pdf.cell(45, 7, str(ro["Medico"]), 1, 0, 'C')
        pdf.cell(25, 7, f"{ro['Ore']} h", 1, 0, 'C')
        pdf.cell(65, 7, " Firma: ________________", 1, 1, 'L')
    
    pdf.set_font("Arial", 'B', 8); pdf.set_fill_color(230, 230, 250)
    pdf.cell(45, 7, "TOTALE MENSILE", 1, 0, 'C', True)
    pdf.cell(25, 7, f"{tot_mensile} h", 1, 0, 'C', True); pdf.cell(65, 7, "", 1, 1, 'L', True)

    pdf_out = pdf.output(dest='S').encode('latin-1')
    with col1:
        if st.button("👁️ ANTEPRIMA PDF", use_container_width=True):
            b64 = base64.b64encode(pdf_out).decode('utf-8')
            st.markdown(f'<object data="data:application/pdf;base64,{b64}" type="application/pdf" width="100%" height="800px"></object>', unsafe_allow_html=True)
    with col2:
        st.download_button("💾 SCARICA PDF", pdf_out, f"Turni_{mese_sel}.pdf", "application/pdf", use_container_width=True)
