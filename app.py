import streamlit as st
import pandas as pd
import calendar
import json
from datetime import datetime, timedelta

# --- 1. LOGICA CALENDARIO E FESTIVITÀ ---
def get_festivita(anno):
    """Calcola le festività nazionali italiane e il Santo Patrono."""
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
        (1, 1): "Capodanno", (6, 1): "Epifania", 
        (25, 2): "S. Patrono", 
        (25, 4): "Liberazione", (1, 5): "Festa Lavoro", (2, 6): "Festa Repubblica", 
        (15, 8): "Ferragosto", (1, 11): "Ognissanti", (8, 12): "Immacolata", 
        (25, 12): "Natale", (26, 12): "S. Stefano", 
        (p.day, p.month): "Pasqua", (pp.day, pp.month): "Pasquetta"
    }

def is_festivo(dt, fest):
    return dt.weekday() == 6 or (dt.day, dt.month) in fest

def is_prefestivo(dt, fest):
    domani = dt + timedelta(days=1)
    return dt.weekday() == 5 or is_festivo(domani, fest)

def get_giorno_ita(dt):
    giorni = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
    return giorni[dt.weekday()]

# --- 2. CONFIGURAZIONE UI ---
st.set_page_config(page_title="Turni Guardia Medica", layout="wide")

if 'db_turni' not in st.session_state:
    st.session_state.db_turni = pd.DataFrame()
if 'medici' not in st.session_state:
    st.session_state.medici = ["Piscopo", "Celani", "Lombardo", "Siracusa"]

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Impostazioni")
    anno_sel = st.number_input("Anno", min_value=2020, max_value=2035, value=2026)
    mesi_ita = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", 
                "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
    mese_nome = st.selectbox("Mese", mesi_ita, index=2) # Default Marzo
    mese_idx = mesi_ita.index(mese_nome) + 1

    st.divider()
    st.write("**Legenda Orari:**")
    st.write("- **Festivo:** 08-14 / 14-20 / 20-08")
    st.write("- **Prefestivo:** 10-14 / 14-20 / 20-08")
    st.write("- **Feriale:** 20-08")

# --- 4. GENERAZIONE TURNI ---
st.title(f"Pianificazione Turni: {mese_nome} {anno_sel}")

if st.button("🚀 Genera Nuova Tabella Mensile", type="primary"):
    fest = get_festivita(anno_sel)
    gg_mese = calendar.monthrange(anno_sel, mese_idx)[1]
    rows = []

    for d in range(1, gg_mese + 1):
        dt = datetime(anno_sel, mese_idx, d)
        
        fest_label = fest.get((d, mese_idx))
        festivo = is_festivo(dt, fest)
        prefestivo = is_prefestivo(dt, fest)
        nome_giorno = get_giorno_ita(dt)
        
        if festivo:
            tipo = f"FESTIVO ({fest_label})" if fest_label else "DOMENICA"
            h_m, h_p, o_m, o_p = "08:00-14:00", "14:00-20:00", 6, 6
            m, p = "Libero", "Libero"
        elif prefestivo:
            tipo = "PREFESTIVO"
            h_m, h_p, o_m, o_p = "10:00-14:00", "14:00-20:00", 4, 6
            m, p = "Libero", "Libero"
        else:
            tipo = "FERIALE"
            h_m, h_p, o_m, o_p = "---", "---", 0, 0
            m, p = "---", "---"

        rows.append({
            "Giorno": d,
            "Data": f"{d} {nome_giorno}",
            "Tipo": tipo,
            "Mattina": m,
            "Pomeriggio": p,
            "Notte": "Libero",
            "OreM": o_m, "OreP": o_p, "OreN": 12
        })
    
    st.session_state.db_turni = pd.DataFrame(rows)

# --- 5. VISUALIZZAZIONE E EDITING ---
if not st.session_state.db_turni.empty:
    lista_m = st.session_state.medici + ["---", "SOSTITUTO"]
    
    # Editor della tabella
    edited_df = st.data_editor(
        st.session_state.db_turni,
        column_order=("Data", "Tipo", "Mattina", "Pomeriggio", "Notte"),
        column_config={
            "Data": st.column_config.TextColumn("Data e Giorno", width="medium", disabled=True),
            "Tipo": st.column_config.TextColumn("Stato Giorno", width="small", disabled=True),
            "Mattina": st.column_config.SelectboxColumn("Mattina (Diurna)", options=lista_m),
            "Pomeriggio": st.column_config.SelectboxColumn("Pomeriggio (Diurna)", options=lista_m),
            "Notte": st.column_config.SelectboxColumn("Notte (20:00-08:00)", options=lista_m),
        },
        use_container_width=True,
        hide_index=True
    )

    # Riepilogo Ore
    st.divider()
    st.subheader("📊 Calcolo Ore Totali del Mese")
    stats = []
    for med in st.session_state.medici:
        o_m = edited_df[edited_df["Mattina"] == med]["OreM"].sum()
        o_p = edited_df[edited_df["Pomeriggio"] == med]["OreP"].sum()
        o_n = edited_df[edited_df["Notte"] == med]["OreN"].sum()
        stats.append({"Medico": med, "Ore Totali": int(o_m + o_p + o_n)})
    
    st.table(pd.DataFrame(stats))
