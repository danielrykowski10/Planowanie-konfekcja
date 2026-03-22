import streamlit as st
import datetime
import pandas as pd

# 1. Baza wydajności
wydajnosc = {
    "232": 70, "233": 60, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Planista Mleczarnia", layout="wide")

# 2. Stylizacja (CSS)
st.markdown("""
    <style>
    .day-box { border: 2px solid #eee; border-radius: 8px; padding: 10px; margin: 5px; background: white; min-height: 150px; }
    .header-yellow { background: #ffe600; padding: 5px; text-align: center; font-weight: bold; border-radius: 4px; color: black; }
    .header-red { background: #ff4b4b; padding: 5px; text-align: center; font-weight: bold; border-radius: 4px; color: white; }
    .item-row { border-bottom: 1px solid #f0f0f0; padding: 2px 0; font-size: 14px; }
    </style>
""", unsafe_allow_html=True)

st.title("🥛 Planista Produkcji - Wersja Stabilna")

# 3. Inicjalizacja danych
if 'kolejka' not in st.session_state:
    st.session_state.kolejka = []

# 4. PANEL BOCZNY
with st.sidebar:
    st.header("📂 Importuj z Excel/CSV")
    plik = st.file_uploader("Wgraj plik", type=['xlsx', 'csv'])
    
    if plik:
        try:
            df = pd.read_excel(plik) if plik.name.endswith('.xlsx') else pd.read_csv(plik)
            if st.button("📥 Dodaj dane z pliku"):
                for _, row in df.iterrows():
                    st.session_state.kolejka.append({
                        "art": str(row['art']),
                        "ile": int(row['ile']),
                        "start": pd.to_datetime(row['start']).date(),
                        "termin": pd.to_datetime(row['termin']).date()
                    })
                st
