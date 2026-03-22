import streamlit as st
import datetime
import math

# Baza wydajności (minuty na 1 paletę)
wydajnosc = {
    "232": 70, "233": 60, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Harmonogram Mleczarnia", page_icon="🥛", layout="wide")

st.markdown("""
    <style>
    .day-card {
        border: 2px solid #e6e9ef;
        border-radius: 10px;
        padding: 15px;
        background-color: #ffffff;
        margin-bottom: 20px;
        min-height: 200px;
    }
    .day-header {
        background-color: #ffe600;
        font-weight: bold;
        text-align: center;
        padding: 8px;
        border-radius: 5px;
        margin-bottom: 12px;
        color: black;
        font-size: 1.1em;
    }
    .art-row {
        display: flex;
        justify-content: space-between;
        border-bottom: 1px solid #f0f0f0;
        padding: 5px 0;
        font-family: monospace;
    }
    .luz-row {
        color: #999;
        font-size: 0.85em;
        font-style: italic;
        margin-top: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🥛 Harmonogram Porcjowania - Pełne Palety")

with st.sidebar:
    st.header("⚙️ Parametry")
    data_startu = st.date_input("Data startu:", datetime.datetime.now())
    st.write("---")
    st.header("📦 Zamówienie (ilość palet)")
    zamowienie_input = []
    for index in wydajnosc.keys():
        ile = st.number_input(f"Art. {index}", min_value=0, step=1, value=0)
        if ile > 0:
            # Przeliczamy od razu na minuty całkowite
            zamowienie_input.append({"idx": index, "ile_total": ile, "pozostalo_min": ile * wydajnosc[index]})

if st.button("Generuj Harmonogram"):
    if not zamowienie_input:
        st.warning("Proszę wpisać ilości palet w panelu bocznym.")
    else:
        dni_planu = {}
        czas_dniowki = 840  # 14h (6-22)
        
        aktualny_dzien = data_startu
        wolny_czas_dzis = czas_dniowki
        zadanie_idx = 0
        
        while zadanie_idx < len(zamowienie_input):
            dzien_key = aktualny_dzien.strftime("%d.%m.%Y (%A)")
            if dzien_key not in dni_planu:
                dni_planu[dzien_key] = {"produkty": [], "wolny_czas": 0}
            
            zadanie = zamowienie_input[zadanie_idx]
            czas_jednej_palety = wydajnosc[zadanie["idx"]]
            
            # Ile PEŁNYCH palet zmieści się w pozostałym czasie dnia?
            max_palet_dzis = wolny_czas_dzis // czas_jednej_palety
            # Ile palet realnie potrzebujemy jeszcze zrobić z tego zamówienia?
            potrzebne_palety = math.ceil(zadanie["pozostalo_min"] / czas_jednej_palety)
            
            ile_robimy_dzis = min(max_palet_dzis, potrzebne_palety)
            
            if ile_robimy_dzis > 0:
                czas_zuzyty = ile_robimy_dzis * czas_jednej_palety
                
                # Dodaj lub zsumuj w widoku dnia
                found = False
                for p in dni_planu[dzien_key]["produkty"]:
                    if p["art"] == zadanie["idx"]:
                        p["ilosc"] += ile_robimy_dzis
                        found = True
                        break
                if not found:
                    dni_planu[dzien_key]["produkty"].append({"art": zadanie["idx"], "ilosc": int(ile_robimy_dzis)})
                
                zadanie["pozostalo_min"] -= czas_zuzyty
                wolny_czas_dzis -= czas_zuzyty
            
            # Jeśli zadanie skończone lub nie wejdzie już ani jedna pełna paleta
            if zadanie["pozostalo_min"] <= 0:
                zadanie_idx += 1
            
            # Jeśli dzień pełny lub brak zadań, przejdź do następnego
            if wolny_czas_dzis < min([wydajnosc[z["idx"]] for z in zamowienie_input[zadanie_idx:]] or [9999]):
                dni_planu[dzien_key]["wolny_czas"] = wolny_czas_dzis
                aktualny_dzien += datetime.timedelta(days=1)
                wolny_czas_dzis = czas_dniowki

        # Wyświetlanie
        dni_list = list(dni_planu.keys())
        for i in range(0, len(dni_list), 5):
            cols = st.columns(5)
            for j in range(5):
                if i + j < len(dni_list):
                    d_key = dni_list[i + j]
                    with cols[j]:
                        st.markdown(f'<div class="day-card"><div class="day-header">{d_key}</div>', unsafe_allow_html=True)
                        for p in dni_planu[d_key]["produkty"]:
                            st.markdown(f'<div class="art-row"><span><b>{p["art"]}</b></span><span>{p["ilosc"]} pal.</span></div>', unsafe_allow_html=True)
                        
                        luz = int(dni_planu[d_key]["wolny_czas"])
                        if luz > 0:
                            st.markdown(f'<div class="luz-row">Wolne: {luz} min</div>', unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
