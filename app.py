import streamlit as st
import datetime
import math

# Baza wydajności (minuty na 1 paletę)
wydajnosc = {
    "232": 70, "233": 60, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Planista Mleczarnia", page_icon="🥛", layout="wide")

st.title("🥛 Harmonogram Produkcji")

# Prosta inicjalizacja listy
if 'koszyk' not in st.session_state:
    st.session_state.koszyk = []

# PANEL BOCZNY - BEZ FORMULARZA (żeby działało od razu)
with st.sidebar:
    st.header("➕ Dodaj zamówienie")
    wybrany = st.selectbox("Artykuł:", list(wydajnosc.keys()))
    ile = st.number_input("Ilość palet:", min_value=1, value=5)
    termin = st.date_input("Termin oddania:", datetime.date.today() + datetime.timedelta(days=2))
    
    if st.button("DODAJ DO LISTY"):
        st.session_state.koszyk.append({
            "art": wybrany,
            "ile": ile,
            "deadline": termin
        })
        st.rerun()

    if st.button("WYCZYŚĆ LISTĘ"):
        st.session_state.koszyk = []
        st.rerun()

    st.write("---")
    st.write("**Twoja aktualna lista:**")
    for i, z in enumerate(st.session_state.koszyk):
        st.write(f"{i+1}. {z['art']} | {z['ile']} pal. | do {z['deadline'].strftime('%d.%m')}")

# GŁÓWNA SEKCJA
if len(st.session_state.koszyk) > 0:
    st.write("### 📅 Wygenerowany Plan")
    
    dni_planu = {}
    czas_dniowki = 840  # 14h
    aktualna_data = datetime.date.today()
    wolny_czas = czas_dniowki
    
    # Kopiujemy dane do obliczeń
    robocza_lista = [dict(x) for x in st.session_state.koszyk]
    
    while robocza_lista:
        d_key = aktualna_data.strftime("%Y-%m-%d")
        if d_key not in dni_planu:
            dni_planu[d_key] = {"data": aktualna_data, "produkcje": []}
        
        z = robocza_lista[0]
        wyd = wydajnosc[z["art"]]
        
        max_palet = wolny_czas // wyd
        ile_robimy = min(max_palet, z["ile"])
        
        if ile_robimy > 0:
            dni_planu[d_key]["produkcje"].append({
                "art": z["art"],
                "ile": int(ile_robimy),
                "spoznione": aktualna_data > z["deadline"]
            })
            z["ile"] -= ile_robimy
            wolny_czas -= (ile_robimy * wyd)
        
        if z["ile"] <= 0:
            robocza_lista.pop(0)
        
        # Przejście na następny dzień
        if wolny_czas < 52 or (not robocza_lista and ile_robimy == 0):
            aktualna_data += datetime.timedelta(days=1)
            wolny_czas = czas_dniowki
        
        if len(dni_planu) > 50: break

    # WYŚWIETLANIE KAFELKÓW
    kolumny = st.columns(5)
    for i, d_key in enumerate(sorted(dni_planu.keys())):
        dane = dni_planu[d_key]
        with kolumny[i % 5]:
            # Kolor nagłówka - czerwony jeśli spóźnione
            jest_brak = any(p["spoznione"] for p in dane["produkcje"])
            kolor = "#FF4B4B" if jest_brak else "#FFE600"
            
            st.markdown(f"""
                <div style="border:1px solid #ddd; border-radius:10px; padding:10px; margin-bottom:10px; background-color:white;">
                    <div style="background-color:{kolor}; padding:5px; border-radius:5px; text-align:center; font-weight:bold; color:black;">
                        {dane['data'].strftime('%d.%m %A')}
                    </div>
                    <div style="padding-top:10px;">
            """, unsafe_allow_html=True)
            
            for p in dane["produkcje"]:
                alert = " ⚠️" if p["spoznione"] else ""
                st.write(f"**{p['art']}**: {p['ile']} pal.{alert}")
            
            st.markdown("</div></div>", unsafe_allow_html=True)

else:
    st.info("Dodaj zamówienia w panelu bocznym po lewej, aby zobaczyć plan.")
