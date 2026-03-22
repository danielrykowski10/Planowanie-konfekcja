import streamlit as st
import datetime

# Baza wydajności (minuty na 1 paletę)
wydajnosc = {
    "232": 70, "233": 60, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Planista Mleczarnia", layout="wide")

# CSS dla tabeli i kafelków
st.markdown("""
    <style>
    .day-box { border: 2px solid #eee; border-radius: 8px; padding: 10px; margin: 5px; background: white; min-height: 180px; }
    .header-yellow { background: #ffe600; padding: 5px; text-align: center; font-weight: bold; border-radius: 4px; color: black; margin-bottom: 8px; }
    .header-red { background: #ff4b4b; padding: 5px; text-align: center; font-weight: bold; border-radius: 4px; color: white; margin-bottom: 8px; }
    .item-row { border-bottom: 1px solid #f0f0f0; padding: 2px 0; font-size: 14px; }
    </style>
""", unsafe_allow_html=True)

st.title("🥛 System Planowania Produkcji")

# Inicjalizacja kolejki
if 'kolejka' not in st.session_state:
    st.session_state.kolejka = []

# --- SIDEBAR ---
with st.sidebar:
    st.header("➕ Dodaj Artykuł")
    art = st.selectbox("Artykuł:", list(wydajnosc.keys()))
    ile = st.number_input("Liczba palet:", min_value=1, step=1, value=10)
    termin = st.date_input("Termin (Deadline):", datetime.date.today() + datetime.timedelta(days=3))
    
    if st.button("DODAJ DO PLANU"):
        st.session_state.kolejka.append({"art": art, "ile": ile, "termin": termin})
        st.rerun()

    if st.button("WYCZYŚĆ WSZYSTKO"):
        st.session_state.kolejka = []
        st.rerun()

    st.write("---")
    st.subheader("📋 Lista zamówień:")
    for i, z in enumerate(st.session_state.kolejka):
        st.write(f"{i+1}. {z['art']} | {z['ile']} pal. | do {z['termin'].strftime('%d.%m')}")

# --- GŁÓWNY PANEL ---
if not st.session_state.kolejka:
    st.info("Dodaj artykuły w panelu bocznym, aby wygenerować harmonogram.")
else:
    # OBLICZENIA
    dni_planu = {}
    limit_minut_dziennie = 840  # 14h (6-22)
    aktualna_data = datetime.date.today()
    wolny_czas_dzis = limit_minut_dziennie
    
    # Tworzymy kopię roboczą zadań
    zadania = []
    for z in st.session_state.kolejka:
        zadania.append({
            "art": z["art"], 
            "ile": z["ile"], 
            "minuty": z["ile"] * wydajnosc[z["art"]],
            "termin": z["termin"]
        })

    # Główna pętla rozdzielająca na dni
    while zadania:
        d_key = aktualna_data.strftime("%Y-%m-%d")
        if d_key not in dni_planu:
            dni_planu[d_key] = {"data": aktualna_data, "pozycje": []}
        
        current_job = zadania[0]
        czas_jednej = wydajnosc[current_job["art"]]
        
        # Ile palet wejdzie jeszcze dzisiaj?
        mozliwe_palety = wolny_czas_dzis // czas_jednej
        
        if mozliwe_palety > 0:
            robimy_teraz = min(mozliwe_palety, current_job["ile"])
            spoznione = aktualna_data > current_job["termin"]
            
            dni_planu[d_key]["pozycje"].append({
                "art": current_job["art"],
                "ile": int(robimy_teraz),
                "alert": spoznione
            })
            
            current_job["ile"] -= robimy_teraz
            wolny_czas_dzis -= (robimy_teraz * czas_jednej)
        
        # Jeśli artykuł skończony, usuń go z listy zadań
        if current_job["ile"] <= 0:
            zadania.pop(0)
            
        # Jeśli dzień pełny lub brak zadań, przeskocz do jutra
        if wolny_czas_dzis < 52 or (not zadania and mozliwe_palety == 0):
            aktualna_data += datetime.timedelta(days=1)
            wolny_czas_dzis = limit_minut_dziennie
        
        if len(dni_planu) > 100: break # Bezpiecznik

    # RYSOWANIE
    st.subheader("📅 Harmonogram Dzienny")
    posortowane_daty = sorted(dni_planu.keys())
    
    # Wyświetlanie po 4 dni w rzędzie (lepiej wygląda na mniejszych ekranach)
    for i in range(0, len(posortowane_daty), 4):
        cols = st.columns(4)
        for j in range(4):
            if i + j < len(posortowane_daty):
                data_iso = posortowane_daty[i+j]
                dane = dni_planu[data_iso]
                with cols[j]:
                    ma_alert = any(p["alert"] for p in dane["pozycje"])
                    klasa_naglowka = "header-red" if ma_alert else "header-yellow"
                    
                    st.markdown(f'<div class="day-box">', unsafe_allow_html=True)
                    st.markdown(f'<div class="{klasa_naglowka}">{dane["data"].strftime("%d.%m %A")}</div>', unsafe_allow_html=True)
                    
                    for p in dane["pozycje"]:
                        wykrzyknik = " ⚠️" if p["alert"] else ""
                        st.markdown(f'<div class="item-row"><b>{p["art"]}</b>: {p["ile"]} pal.{wykrzyknik}</div>', unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
