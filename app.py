import streamlit as st
import pandas as pd
import calendar
import json
from datetime import datetime, timedelta

# --- 1. FUNZIONI LOGICHE ---
def get_festivita_italiane(anno):
    """Calcola le festività nazionali italiane e la Pasqua."""
    def pasqua(y):
        a, b, c = y % 19, y // 100, y % 100
        d, e = b // 4, b % 4
        g = (b + 8) // 25
        h = (b - g + 1) // 3
        i = (19 * a + b - d - h + 15) % 30
        j, k = c // 4, c % 4
        l = (32 + 2 * e + 2 * j - i - k) % 7
        m = (a + 11 * i + 22 * l) // 451
        mese = (i + l - 7 * m + 114) // 31
        giorno = ((i + l - 7 * m + 114) % 31) + 1
        return datetime(y, mese, giorno)

    p = pasqua(anno)
    lunedi_pasqua = p + timedelta(days=1)
    
    return {
        (1, 1): "Capodanno", (6, 1): "Epifania", (25, 4): "Liberazione",
        (1, 5): "Festa Lavoro", (2, 6): "Festa Repubblica", (15, 8): "Ferragosto",
        (1, 11): "Ognissanti", (8, 12): "Immacolata", (25, 12): "Natale",
        (26, 12): "S. Stefano", (p.day, p.month): "Pasqua",
        (lunedi_pasqua.day, lunedi_pasqua.month): "Pasquetta"
    }

# --- 2. CONFIGURAZIONE UI ---
st.set_page_config(page_title="Gestione Turni C.A.", layout="wide")
st.title("⚕️ Sistema Gestione Turni Continuità Assistenziale")

if 'medici' not in st.session_state:
    st.session_state.medici = ["Piscopo", "Celani", "Lombardo", "Siracusa"] [cite: 15, 17, 21, 30]
if 'assenze' not in st.session_state:
    st.session_state.assenze = {m: [] for m in st.session_state.medici}

# --- 3. SIDEBAR - IMPOSTAZIONI ---
with st.sidebar:
    st.header("⚙️ Configurazione")
    anno = st.number_input("Anno", min_value=2024, max_value=2030, value=2026) [cite: 3]
    mesi = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", 
            "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
    mese_nome = st.selectbox("Mese", mesi, index=2) [cite: 2]
    mese_idx = mesi.index(mese_nome) + 1

    st.divider()
    st.header("💾 Backup")
    backup = {"assenze": st.session_state.assenze, "medici": st.session_state.medici}
    st.download_button("Esporta Dati JSON", json.dumps(backup), "backup_turni.json")

# --- 4. GENERAZIONE TABELLA ---
festivi = get_festivita_italiane(anno)
giorni_nel_mese = calendar.monthrange(anno, mese_idx)[1]

turni_data = []

for giorno in range(1, giorni_nel_mese + 1):
    dt = datetime(anno, mese_idx, giorno)
    wd = dt.weekday() # 5=Sabato, 6=Domenica
    festivo_nome = festivi.get((giorno, mese_idx))
    
    # Logica orari e ore
    is_sabato = (wd == 5) [cite: 35]
    is_festivo = (wd == 6 or festivo_nome is not None) [cite: 6, 14, 40]
    
    # Inizializzazione righe
    tipo = festivo_nome if festivo_nome else ("Prefestivo" if is_sabato else ("Festivo" if is_festivo else "Feriale"))
    
    # Definizione fasce attive
    mattina = "---"
    pomeriggio = "---"
    notte = "Libero"
    
    if is_festivo:
        mattina = "Libero" # 08-14 [cite: 10]
        pomeriggio = "Libero" # 14-20 [cite: 11]
    elif is_sabato:
        mattina = "Libero" # 10-14 
        pomeriggio = "Libero" # 14-20 [cite: 9]
        
    turni_data.append({
        "Giorno": giorno,
        "Data": dt.strftime("%d/%m/%Y"),
        "Settimana": dt.strftime("%A"),
        "Tipo": tipo,
        "Mattina": mattina,
        "Pomeriggio" : pomeriggio,
        "Notte": "Libero" # 20-08 sempre attiva [cite: 7, 12]
    })

df_turni = pd.DataFrame(turni_data)

# --- 5. INTERFACCIA DI EDITING ---
st.subheader(f"Pianificazione Turni: {mese_nome} {anno}")
st.info("💡 Usa i menu a tendina nelle celle per assegnare i medici ai turni attivi.")

# Opzioni per il menu a tendina
opzioni_medici = st.session_state.medici + ["---", "Sostituto"]

edited_df = st.data_editor(
    df_turni,
    column_config={
        "Mattina": st.column_config.SelectboxColumn("Mattina", options=opzioni_medici),
        "Pomeriggio": st.column_config.SelectboxColumn("Pomeriggio", options=opzioni_medici),
        "Notte": st.column_config.SelectboxColumn("Notte", options=opzioni_medici),
        "Giorno": st.column_config.NumberColumn(disabled=True),
        "Data": st.column_config.TextColumn(disabled=True),
        "Settimana": st.column_config.TextColumn(disabled=True),
        "Tipo": st.column_config.TextColumn(disabled=True),
    },
    hide_index=True,
    use_container_width=True
)

# --- 6. RIEPILOGO ORE ---
st.divider()
st.subheader("📊 Calcolo Totale Ore Mensili")

ore_report = []
for medico in st.session_state.medici:
    ore_tot = 0
    # Conteggio ore Mattina
    m_fest = edited_df[(edited_df['Mattina'] == medico) & (edited_df['Tipo'].str.contains("Festivo|Pasqua|Natale|Capodanno|Ognissanti|Immacolata|Liberazione|Lavoro|Repubblica|Ferragosto|Stefano|Epifania"))].shape[0] * 6
    m_pre = edited_df[(edited_df['Mattina'] == medico) & (edited_df['Tipo'] == "Prefestivo")].shape[0] * 4
    # Conteggio ore Pomeriggio (Sempre 6h)
    p_tot = edited_df[edited_df['Pomeriggio'] == medico].shape[0] * 6
    # Conteggio ore Notte (Sempre 12h)
    n_tot = edited_df[edited_df['Notte'] == medico].shape[0] * 12
    
    ore_tot = m_fest + m_pre + p_tot + n_tot
    ore_report.append({"Medico": medico, "Ore Totali": ore_tot})

st.table(pd.DataFrame(ore_report))
