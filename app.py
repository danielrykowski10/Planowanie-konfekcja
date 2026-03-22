import streamlit as st
import datetime

# Baza wydajności
wydajnosc = {
    "232": 70, "233": 60, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Planista", layout="wide")
st.title("🥛 Planista Produkcji - Reset")

if 'kolejka' not in st.session_state:
    st.session_state.kolejka = []

# PANEL BOCZNY
with st.sidebar:
    st.header("➕ Dodaj")
    art = st.selectbox("Artykuł:", list(wydajnosc.keys()))
    ile = st.number_input("Ile palet:", min_value=1, value=10)
    d_start = st.date_input("Start:", datetime.date.today())
    d_koniec = st.date_input("Termin:", datetime.date.today() + datetime.timedelta(days=3))
    
    if st.button("DODAJ"):
        st.session_state.kolejka.append({"art": art, "ile": ile, "start": d_start, "termin": d_koniec})
        st.rerun()

    if st.button("WYCZYŚĆ"):
        st.session_state.kolejka = []
        st.rerun()

# OBLICZENIA I WIDOK
if not st.session_state.kolejka:
    st.info("Dodaj zamówienie po lewej.")
else:
    # Sortowanie i prosta logika
    zadania = sorted([dict(z) for z in st.session_state.kolejka], key=lambda x: x['start'])
    aktualna_data = min(z["start"] for z in zadania)
    wolny_czas = 840
    dni_planu = {}

    while zadania:
        d_key = aktualna_data.strftime("%Y-%m-%d")
        if d_key not in dni_planu:
            dni_planu[d_key] = {"data": aktualna_data, "p": []}
        
        dostepne = [z for z in zadania if z["start"] <= aktualna_data]
        if not dostepne:
            aktualna_data = min(z["start"] for z in zadania)
            continue
            
        z = dostepne[0]
        wyd = wydajnosc.get(z["art"], 70)
        ile_dzis = min(wolny_czas // wyd, z["ile"])
        
        if ile_dzis > 0:
            dni_planu[d_key]["p"].append({"art": z["art"], "ile": int(ile_dzis)})
            z["ile"] -= ile_dzis
            wolny_czas -= (ile_dzis * wyd)
        
        if z["ile"] <= 0: zadania.remove(z)
        if wolny_czas < 52 or not dostepne:
            aktualna_data += datetime.timedelta(days=1)
            wolny_czas = 840
        if len(dni_planu) > 50: break

    # Rysowanie kafelków
    cols = st.columns(4)
    for i, dk in enumerate(sorted(dni_planu.keys())):
        with cols[i % 4]:
            st.warning(f"**{dni_planu[dk]['data'].strftime('%d.%m %A')}**")
            for p in dni_planu[dk]["p"]:
                st.write(f"{p['art']}: {p['ile']} pal.")
