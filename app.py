import streamlit as st
import datetime
import math

# Baza wydajności (minuty na 1 paletę)
wydajnosc = {
    "232": 70, "233": 60, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Planista Mleczarnia PRO", page_icon="🥛", layout="wide")

st.markdown("""
    <style>
    .day-card { border: 2px solid #e6e9ef; border-radius: 10px; padding: 10px; background-color: #ffffff; margin-bottom: 10px; min-height: 150px; }
    .day-header { background-color: #ffe600; font-weight: bold; text-align: center; padding: 5px; border-radius: 5px; margin-bottom: 10px; color: black; }
    .art-row { display: flex; justify-content: space-between; border-bottom: 1px solid #f0f0f0; padding: 3px 0; font-size: 0.9em; }
    .deadline-ok { color: green; font-size: 0.8em; }
    .deadline-late { color: white; background-color: red; padding: 2px; border-radius: 3px; font-size: 0.8em; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🥛 Harmonogram Produkcji z Terminami")

# Zarządzanie listą zamówień w sesji
if 'lista_zamowien' not in st.session_state:
    st.session_state.lista_zamowien = []

with st.sidebar:
    st.header("➕ Dodaj Partię")
    nowy_art = st.selectbox("Artykuł:", list(wydajnosc.keys()))
    nowa_ilosc = st.number_input("Ilość palet:", min_value=1, step=1)
    nowy_termin = st.date_input("Termin oddania (Data):", datetime.date.today() + datetime.timedelta(days=3))
    
    if st.button("Dodaj do planu"):
        st.session_state.lista_zamowien.append({
            "art": nowy_art,
            "ile": nowa_ilosc,
            "termin": nowy_termin
        })

    if st.button("Wyczyść listę"):
        st.session_state.lista_zamowien = []
        st.rerun()

    st.write("---")
    st.write("**Lista do zaplanowania:**")
    for i, z in enumerate(st.session_state.lista_zamowien):
        st.write(f"{i+1}. {z['art']} - {z['ile']} pal. (do {z['termin']})")

# Logika generowania planu
if st.button("🚀 Generuj Harmonogram"):
    if not st.session_state.lista_zamowien:
        st.warning("Lista zamówień jest pusta!")
    else:
        dni_planu = {}
        czas_dniowki = 840  # 14h
        data_startu = datetime.date.today()
        
        aktualny_dzien = data_startu
        wolny_czas_dzis = czas_dniowki
        
        # Kopia zamówień do obróbki
        kolejka = [dict(z) for z in st.session_state.lista_zamowien]
        
        while kolejka:
            dzien_key = aktualny_dzien.strftime("%Y-%m-%d")
            if dzien_key not in dni_planu:
                dni_planu[dzien_key] = {"data": aktualny_dzien, "produkcje": []}
            
            zadanie = kolejka[0]
            wyd = wydajnosc[zadanie["art"]]
            
            # Ile palet wejdzie dziś
            możliwe_dzis = wolny_czas_dzis // wyd
            do_zrobienia = zadanie["ile"]
            
            ile_robimy = min(możliwe_dzis, do_zrobienia)
            
            if ile_robimy > 0:
                # Sprawdzamy czy termin nie minął
                status = "ok" if aktualny_dzien <= zadanie["termin"] else "late"
                
                dni_planu[dzien_key]["produkcje"].append({
                    "art": zadanie["art"],
                    "ile": int(ile_robimy),
                    "termin": zadanie["termin"],
                    "status": status
                })
                
                zadanie["ile"] -= ile_robimy
                wolny_czas_dzis -= (ile_robimy * wyd)
