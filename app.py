import streamlit as st
import pandas as pd
import calendar
import json
from datetime import datetime, timedelta

# --- 1. FUNZIONE PER LE FESTIVITÀ ITALIANE ---
def get_festivita(anno):
    """Calcola le festività fisse e mobili (Pasqua)"""
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
        (1, 1): "Capodanno", (6, 1): "Epifania", (25, 4): "Liberazione",
        (1, 5): "Festa Lavoro", (2, 6): "Festa Repubblica", (15, 8): "Ferragosto",
        (1, 11): "Ognissanti", (8, 12): "Immacolata", (25, 12): "Natale",
        (26, 12): "S. Stefano", (p.day, p.month): "Pasqua", (pp.day, pp.month): "Pasquetta"
    }

# --- 2. CONFIGURAZIONE E SESSION STATE ---
st.set_page_config(page_title="Turni Guardia Medica", layout="wide")

if 'medici' not in st.session_state:
    st.session_state.medici = ["Piscopo", "Celani", "Lombardo", "Siracusa"]
if 'db_turni' not in st.session_state:
    st.session_state.db_turni = pd.DataFrame()

# --- 3. SIDEBAR (IMPOSTAZIONI E BACKUP) ---
with st.sidebar:
    st.header("⚙️ Impostazioni")
    anno_sel = st.number_input("Anno", min_value=2024, max_value=2030, value=2026)
    mesi_ita = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", 
                "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
    mese_nome = st.selectbox("Mese", mesi_ita)
    mese_idx = mesi_ita.index(mese_nome) + 1

    st.divider()
    st.header("💾 Backup")
    backup_data = {"medici": st.session_state.medici}
    st.download_button("Scarica Backup JSON", json.dumps(backup_data), "backup.json")

# --- 4. LOGICA GENERAZIONE TURNI ---
st.title(f"📅 Turni {mese_nome} {anno_sel}")

if st.button("🚀 Genera Tabella Vuota", type="primary"):
    festivi = get_festivita(anno_sel)
    gg_mese = calendar.monthrange(anno_sel, mese_idx)[1]
    rows = []

    for d in range(1, gg_mese + 1):
        dt = datetime(anno_sel, mese_idx, d)
        wd = dt.weekday() # 5=Sabato, 6=Domenica
        nome_fest = festivi.get((d, mese_idx))
        
        is_sabato = (wd == 5)
        is_festivo = (wd == 6 or nome_fest is not None)
        
        tipo = nome_fest if nome_fest else ("Sabato" if is_sabato else ("Domenica" if wd == 6 else "Feriale"))
        
        # Inizializzazione celle
        m, p = "---", "---"
        ore_m, ore_p = 0, 0
        
        if is_festivo:
            m, p = "Libero", "Libero"
            ore_m, ore_p = 6, 6 # 08-14 e 14-20
        elif is_sabato:
            m, p = "Libero", "Libero"
            ore_m, ore_p = 4, 6 # 10-14 e 14-20

        rows.append({
            "Giorno": d, "Data": dt.strftime("%d/%m"), "Tipo": tipo,
            "Mattina": m, "Pomeriggio": p, "Notte": "Libero",
            "OreM": ore_m, "OreP": ore_p, "OreN": 12
        })
    
    st.session_state.db_turni = pd.DataFrame(rows)

# --- 5. EDITING E CALCOLO ---
if not st.session_state.db_turni.empty:
    lista_m = st.session_state.medici + ["---", "Sostituto"]
    
    # Editor della tabella
    edited_df = st.data_editor(
        st.session_state.db_turni,
        column_config={
            "Mattina": st.column_config.SelectboxColumn("Mattina", options=lista_m),
            "Pomeriggio": st.column_config.SelectboxColumn("Pomeriggio", options=lista_m),
            "Notte": st.column_config.SelectboxColumn("Notte", options=lista_m),
            "OreM": None, "OreP": None, "OreN": None # Nascondi colonne tecniche
        },
        use_container_width=True, hide_index=True
    )

    # Calcolo Ore
    st.subheader("📊 Riepilogo Ore Mensili")
    report = []
    for med in st.session_state.medici:
        o_m = edited_df[edited_df["Mattina"] == med]["OreM"].sum()
        o_p = edited_df[edited_df["Pomeriggio"] == med]["OreP"].sum()
        o_n = edited_df[edited_df["Notte"] == med]["OreN"].sum()
        report.append({"Medico": med, "Totale Ore": o_m + o_p + o_n})
    
    st.table(pd.DataFrame(report))
