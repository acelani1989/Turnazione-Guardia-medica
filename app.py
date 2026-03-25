import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="AMEDEO AI PERFORMANCE", layout="wide")

# Grafica Nutribook Style
st.markdown("""
    <style>
    .stApp { background-color: #0f172a; color: white; }
    .card { background: #1e293b; padding: 20px; border-radius: 15px; border: 1px solid #38bdf8; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

st.title("💎 AMEDEO AI SYSTEM")

# Inizializzazione Dati (Session State per il Cloud)
if 'pesi' not in st.session_state: st.session_state.pesi = []

tab1, tab2, tab3 = st.tabs(["📊 DASHBOARD AI", "🍎 DIETA DINAMICA", "🏋️ WORKOUT"])

with tab1:
    st.subheader("Modulo AI")
    p = st.number_input("Inserisci Peso Corporeo (kg)", step=0.1, format="%.1f")
    if st.button("SALVA PESATA"):
        st.session_state.pesi.append({"data": str(datetime.now().date()), "val": p})
        st.success("Dato archiviato nel Cloud!")
    
    if st.session_state.pesi:
        df = pd.DataFrame(st.session_state.pesi)
        st.line_chart(df.set_index('data'))

with tab2:
    st.subheader("Piano Alimentare Amazon")
    is_work = st.toggle("Oggi Turno Consegne 🚛")
    if is_work:
        st.info("PROTOCOLLO LAVORO: Carbo 10:30 e 13:30. Cena ZERO CARBO.")
    else:
        st.success("PROTOCOLLO RIPOSO: Solo Proteine e Verdure. Focus Definizione.")

with tab3:
    st.subheader("Attività Fisica")
    ex = st.selectbox("Esercizio", ["Squat", "Plank", "Pushups", "Lombari"])
    if st.button("REGISTRA SESSIONE"):
        st.balloons()
