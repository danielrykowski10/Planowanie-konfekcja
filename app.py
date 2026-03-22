import streamlit as st
import datetime

# 1. Baza wydajności (minuty na 1 paletę)
wydajnosc = {
    "232": 70, "233": 60, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Planista Mleczarnia", layout="wide")

# 2. Stylizacja wizualna
st.markdown("""
    <style>
    .day-box { border: 2px solid #eee; border-radius: 10px; padding: 10px; margin: 5px; background: white; min-height: 150px; }
    .header-yellow { background: #ffe600; padding: 5px; text-align: center; font-weight: bold; border-radius: 5px; color: black; }
    .header-red { background: #ff4b4b; padding: 5px; text-align: center; font-weight: bold; border-radius: 5px; color: white; }
    .item-row { border-bottom: 1px solid #f0f0f0; padding: 4px 0; font-size: 15px; }
    </style>
""", unsafe_allow_html=True)

st.title("🥛 Harmonogram Porcjowania Sera")

# 3. Inicjalizacja kolejki zamówień
if 'kolejka' not in st.session_state:
    st.session_state.kolejka = []

# --- PANEL BOCZNY ---
with st.sidebar:
    st.header("➕ Dodaj zamówienie")
    art = st.selectbox("Artykuł:", list(wydajnosc.keys()))
    ile = st.number_input("Ile palet:", min_value=1, value=10, step=1)
    d_start = st.date_input("Dzień rozpoczęcia:", datetime.date.today())
    d_koniec = st.date_input("Termin (Deadline):", datetime.date.today() + datetime.timedelta(days=3))
    
    if st.button("DODAJ DO PLANU"):
        st.session_state.kolejka.append({
            "art": art, 
            "ile": ile, 
            "start": d_start, 
            "termin": d_koniec
        })
        st.rerun()

    if st.button("🗑️ WYCZYŚĆ WSZYSTKO"):
        st.session_state.kolejka = []
        st.rerun()

    st.write("---")
    st.subheader("📋 Lista w kolejce:")
    for i, z in enumerate(st.session_state.kolejka):
        st.write(f"{i+1}. **{z['art']}**: {z['ile']} pal. (od {z['start'].strftime('%d.%m')})")

# --- GŁÓWNY PANEL OBLICZEŃ ---
if not st.session_state.kolejka:
    st.info("Dodaj pierwsze zamówienie w panelu bocznym po lewej.")
else:
    # Kopiujemy i sortujemy listę według daty startu
    zadania = sorted([dict(z) for z in st.session_state.kolejka], key=lambda x: x['start'])
    
    dni_planu = {}
    limit_minut = 840  # 14h (dwie zmiany po 7h netto)
    aktualna_data = min(z["start"] for z in zadania)
    wolny_czas_dzis = limit_minut

    while zadania:
        # Wybieramy tylko te zadania, które mogą się zacząć dzisiaj lub wcześniej
        dostepne = [z for z in zadania if z["start"] <= aktualna_data]
        
        if not dostepne:
            # Jeśli nic nie można robić dzisiaj, skaczemy do najbliższej daty startu dowolnego zadania
            aktualna_data = min(z["start"] for z in zadania)
            wolny_czas_dzis = limit_minut
            continue

        d_key = aktualna_data.strftime("%Y-%m-%d")
        if d_key not in dni_planu:
            dni_planu[d_key] = {"data": aktualna_data, "pozycje": []}

        # Bierzemy pierwsze dostępne zadanie
        zadanie = dostepne[0]
        wyd = wydajnosc.get(zadanie["art"], 70)
        
        mozliwe = wolny_czas_dzis // wyd
        ile_dzis = min(mozliwe, zadanie["ile"])

        if ile_dzis > 0:
            dni_planu[d_key]["pozycje"].append({
                "art": zadanie["art"],
                "ile": int(ile_dzis),
                "alert": aktualna_data > zadanie["termin"]
            })
            zadanie["ile"] -= ile_dzis
            wolny_czas_dzis -= (ile_dzis * wyd)

        # Jeśli zadanie skończone, usuń z listy
        if zadanie["ile"] <= 0:
            zadania.remove(zadanie)

        # Jeśli dzień się skończył lub brak dostępnych zadań w tej chwili - następny dzień
        if wolny_czas_dzis < 52 or not dostepne:
            aktualna_data += datetime.timedelta(days=1)
            wolny_czas_dzis = limit_minut
        
        if len(dni_planu) > 60: break # Bezpiecznik na 2 miesiące planu

    # --- RYSOWANIE KAFELKÓW ---
    st.subheader("📅 Harmonogram Produkcji")
    posortowane_daty = sorted(dni_planu.keys())
    
    # Wyświetlanie po 4 dni w rzędzie
    for i in range(0, len(posortowane_daty), 4):
        cols = st.columns(4)
        for j in range(4):
            if i + j < len(posortowane_daty):
                data_iso = posortowane_daty[i+j]
                d = dni_planu[data_iso]
                with cols[j]:
                    ma_alert = any(p["alert"] for p in d["pozycje"])
                    klasa = "header-red" if ma_alert else "header-yellow"
                    
                    st.markdown(f'<div class="day-box">', unsafe_allow_html=True)
                    st.markdown(f'<div class="{klasa}">{d["data"].strftime("%d.%m %A")}</div>', unsafe_allow_html=True)
                    
                    for p in d["pozycje"]:
                        wykrzyknik = " ⚠️" if p["alert"] else ""
                        st.markdown(f'<div class="item-row"><b>{p["art"]}</b>: {p["ile"]} pal.{wykrzyknik}</div>', unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
