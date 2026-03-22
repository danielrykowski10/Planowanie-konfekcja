import streamlit as st
import datetime
import pandas as pd
import math

# Baza wydajności (minuty na 1 paletę)
wydajnosc = {
    "232": 70, "233": 60, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Planista Mleczarnia PRO", layout="wide")

st.markdown("""
    <style>
    .day-box { border: 2px solid #eee; border-radius: 8px; padding: 10px; margin: 5px; background: white; min-height: 180px; }
    .header-yellow { background: #ffe600; padding: 5px; text-align: center; font-weight: bold; border-radius: 4px; color: black; margin-bottom: 8px; }
    .header-red { background: #ff4b4b; padding: 5px; text-align: center; font-weight: bold; border-radius: 4px; color: white; margin-bottom: 8px; }
    .item-row { border-bottom: 1px solid #f0f0f0; padding: 2px 0; font-size: 14px; }
    .stDataFrame { font-size: 12px; }
    </style>
""", unsafe_allow_html=True)

st.title("🥛 Planista Produkcji v4 (Import & Daty)")

if 'kolejka' not in st.session_state:
    st.session_state.kolejka = []

# --- SIDEBAR: IMPORT I DODAWANIE ---
with st.sidebar:
    st.header("📂 Importuj zamówienia")
    uploaded_file = st.file_uploader("Wgraj plik Excel lub CSV", type=['xlsx', 'csv'])
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.write("Podgląd pliku:")
            st.dataframe(df.head(), use_container_width=True)
            
            if st.button("✅ DODAJ WSZYSTKO Z PLIKU"):
                for _, row in df.iterrows():
                    st.session_state.kolejka.append({
                        "art": str(row['art']),
                        "ile": int(row['ile']),
                        "termin": pd.to_datetime(row['termin']).date(),
                        "start": pd.to_datetime(row['start']).date()
                    })
                st.success("Dodano zamówienia!")
                st.rerun()
        except Exception as e:
            st.error(f"Błąd pliku! Upewnij się, że masz kolumny: art, ile, termin, start. Błąd: {e}")

    st.write("---")
    st.header("➕ Dodaj ręcznie")
    art = st.selectbox("Artykuł:", list(wydajnosc.keys()))
    ile = st.number_input("Liczba palet:", min_value=1, value=10)
    data_start = st.date_input("Kiedy zacząć?", datetime.date.today())
    data_koniec = st.date_input("Termin (Deadline):", datetime.date.today() + datetime.timedelta(days=3))
    
    if st.button("➕ DODAJ DO PLANU"):
        st.session_state.kolejka.append({
            "art": art, "ile": ile, "termin": data_koniec, "start": data_start
        })
        st.rerun()

    if st.button("🗑️ WYCZYŚĆ WSZYSTKO"):
        st.session_state.kolejka = []
        st.rerun()

# --- LOGIKA PLANOWANIA ---
if not st.session_state.kolejka:
    st.info("Lista jest pusta. Wgraj plik lub dodaj artykuły ręcznie.")
else:
    # Sortujemy kolejkę według daty startu, żeby robot wiedział co robić najpierw
    kolejka_sort = sorted(st.session_state.kolejka, key=lambda x: x['start'])
    
    dni_planu = {}
    limit_minut = 840  # 14h
    
    # Kopia robocza zadań
    zadania = []
    for z in kolejka_sort:
        zadania.append({
            "art": z["art"], 
            "ile": z["ile"], 
            "termin": z["termin"],
            "start": z["start"]
        })

    # Startujemy od najwcześniejszej daty w zamówieniach
    aktualna_data = min(z["start"] for z in zadania)
    wolny_czas_dzis = limit_minut

    while zadania:
        d_key = aktualna_data.strftime("%Y-%m-%d")
        
        # Filtrujemy zadania, które MOGĄ się zacząć dzisiaj lub wcześniej
        dostepne_zadania = [z for z in zadania if z["start"] <= aktualna_data]
        
        if not dostepne_zadania:
            # Jeśli nic nie można robić dzisiaj, skaczemy do najbliższej daty startu
            aktualna_data = min(z["start"] for z in zadania)
            wolny_czas_dzis = limit_minut
            continue

        if d_key not in dni_planu:
            dni_planu[d_key] = {"data": aktualna_data, "pozycje": []}
            
        current_job = dostepne_zadania[0]
        wyd = wydajnosc.get(current_job["art"], 70) # Domyślnie 70 jeśli błąd w indeksie
        
        mozliwe_palety = wolny_czas_dzis // wyd
        robimy_teraz = min(mozliwe_palety, current_job["ile"])
        
        if robimy_teraz > 0:
            dni_planu[d_key]["pozycje"].append({
                "art": current_job["art"],
                "ile": int(robimy_teraz),
                "alert": aktualna_data > current_job["termin"]
            })
            current_job["ile"] -= robimy_teraz
            wolny_czas_dzis -= (robimy_teraz * wyd)

        # Usuwamy skończone zadania
        if current_job["ile"] <= 0:
            zadania.remove(current_job)

        # Jeśli brak czasu lub brak dostępnych zadań w tej chwili - następny dzień
        if wolny_czas_dzis < 52 or not dostepne_zadania:
            aktualna_data += datetime.timedelta(days=1)
            wolny_czas_dzis = limit_minut
        
        if len(dni_planu) > 150: break

    # --- WYŚWIETLANIE ---
    st.subheader("📅 Harmonogram Produkcji")
    posortowane_daty = sorted(dni_planu.keys())
    
    for i in range(0, len(posortowane_daty), 4):
        cols = st.columns(4)
        for j in range(4):
            if i + j < len(posortowane_daty):
                data_iso = posortowane_daty[i+j]
                dane = dni_planu[data_iso]
                with cols[j]:
                    ma_alert = any(p["alert"] for p in dane["pozycje"])
                    klasa = "header-red" if ma_alert else "header-yellow"
                    st.markdown(f'<div class="day-box"><div class="{klasa}">{dane["data"].strftime("%d.%m %A")}</div>', unsafe_allow_html=True)
                    for p in dane["pozycje"]:
                        st.markdown(f'<div class="item-row"><b>{p["art"]}</b>: {p["ile"]} pal. {"⚠️" if p["alert"] else ""}</div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
