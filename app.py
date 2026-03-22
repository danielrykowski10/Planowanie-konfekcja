import streamlit as st
import datetime

# Baza wydajności (minuty na 1 paletę)
wydajnosc = {
    "232": 70, "233": 60, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Planista Produkcji", layout="wide")

st.title("🥛 System Kolejkowania Zamówień")

# Inicjalizacja listy zamówień
if 'kolejka' not in st.session_state:
    st.session_state.kolejka = []

# --- PANEL BOCZNY (WPROWADZANIE) ---
with st.sidebar:
    st.header("🛒 Nowe Zamówienie")
    art = st.selectbox("Wybierz artykuł:", list(wydajnosc.keys()))
    ile = st.number_input("Ile palet:", min_value=1, step=1, value=5)
    termin = st.date_input("Termin (Deadline):", datetime.date.today() + datetime.timedelta(days=2))
    
    if st.button("➕ DODAJ DO KOLEJKI"):
        st.session_state.kolejka.append({
            "art": art,
            "ile": ile,
            "termin": termin
        })
        st.rerun()

    if st.button("🗑️ WYCZYŚĆ WSZYSTKO"):
        st.session_state.kolejka = []
        st.rerun()

    st.write("---")
    st.subheader("📋 Twoja Lista:")
    for i, z in enumerate(st.session_state.kolejka):
        st.write(f"{i+1}. **{z['art']}** | {z['ile']} pal. | do {z['termin'].strftime('%d.%m')}")

# --- GŁÓWNE OKNO (OBLICZENIA I WIDOK) ---
if not st.session_state.kolejka:
    st.info("Dodaj pierwsze zamówienie po lewej stronie, aby robot mógł przygotować rozpiskę.")
else:
    st.subheader("📅 Harmonogram Pracy (6:00 - 22:00)")
    
    # Parametry robota
    dni_planu = {}
    czas_zmian = 840  # 14h pracy dziennie (2 zmiany po 7h netto)
    aktualna_data = datetime.date.today()
    wolny_czas_dzis = czas_zmian
    
    # Kopia kolejki do przeliczenia
    do_zrobienia = [dict(z) for z in st.session_state.kolejka]
    
    while do_zrobienia:
        d_key = aktualna_data.strftime("%Y-%m-%d")
        if d_key not in dni_planu:
            dni_planu[d_key] = {"data": aktualna_data, "zadania": []}
            
        zadanie = do_zrobienia[0]
        czas_jednej = wydajnosc[zadanie["art"]]
        
        # Ile palet wejdzie jeszcze dzisiaj?
        mozliwe_dzis = wolny_czas_dzis // czas_jednej
        ile_faktycznie = min(mozliwe_dzis, zadanie["ile"])
        
        if ile_faktycznie > 0:
            spoznione = aktualna_data > zadanie["termin"]
            dni_planu[d_key]["zadania"].append({
                "art": zadanie["art"],
                "ile": int(ile_faktycznie),
                "alert": spoznione
            })
            zadanie["ile"] -= ile_faktycznie
            wolny_czas_dzis -= (ile_faktycznie * czas_jednej)
            
        # Jeśli skończyliśmy to zamówienie, bierzemy następne z kolejki
        if zadanie["ile"] <= 0:
            do_zrobienia.pop(0)
            
        # Jeśli dzień się skończył (lub nie wejdzie już żadna paleta) - następny dzień
        if wolny_czas_dzis < 52 or (not do_zrobienia and ile_faktycznie == 0):
            aktualna_data += datetime.timedelta(days=1)
            wolny_czas_dzis = czas_zmian
            
        if len(dni_planu) > 40: break # Zabezpieczenie przed pętlą

    # Wyświetlanie kafelków (5 w rzędzie)
    dni_posortowane = sorted(dni_planu.keys())
    for i in range(0, len(dni_posortowane), 5):
        cols = st.columns(5)
        for j in range(5):
            if i + j < len(dni_posortowane):
                data_iso = dni_posortowane[i+j]
                dzien = dni_planu[data_iso]
                with cols[j]:
                    # Czerwony nagłówek jeśli spóźnienie
                    ma_alert = any(z["alert"] for z in dzien["zadania"])
                    kolor = "#FF4B4B" if ma_alert else "#FFE600"
                    
                    st.markdown(f"""
                        <div style="border:2px solid #ddd; border-radius:10px; padding:10px; background-color:white; min-height:150px;">
                            <div style="background-color:{kolor}; color:black; text-align:center; font-weight:bold; border-radius:5px;">
                                {dzien['data'].strftime('%d.%m %A')}
                            </div>
                            <div style="margin-top:10px;">
                    """, unsafe_allow_html=True)
                    
                    for z in dzien["zadania"]:
                        wykrzyknik = " ⚠️" if z["alert"] else ""
                        st.write(f"**{z['art']}**: {z['ile']} pal.{wykrzyknik}")
                        
                    st.markdown("</div></div>", unsafe_allow_html=True)
