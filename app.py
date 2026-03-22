import streamlit as st
import datetime

# Baza wydajności (minuty na 1 paletę)
wydajnosc = {
    "232": 70, "233": 60, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Harmonogram Mleczarnia", page_icon="🥛", layout="wide")

# CSS dla ładnego wyglądu kafelków
st.markdown("""
    <style>
    .day-card {
        border: 2px solid #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        background-color: #ffffff;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
        height: 100%;
    }
    .day-header {
        background-color: #ffe600;
        font-weight: bold;
        text-align: center;
        padding: 5px;
        border-radius: 5px;
        margin-bottom: 10px;
        color: black;
    }
    .art-row {
        display: flex;
        justify-content: space-between;
        border-bottom: 1px solid #eee;
        padding: 3px 0;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🥛 Harmonogram Porcjowania 2026")

# Sidebar - wprowadzanie danych
with st.sidebar:
    st.header("⚙️ Ustawienia")
    data_startu = st.date_input("Data rozpoczęcia planu:", datetime.datetime.now())
    st.write("---")
    st.header("📦 Zamówienie")
    zamowienie_input = []
    for index in wydajnosc.keys():
        ile = st.number_input(f"Art. {index} (palet)", min_value=0.0, step=1.0, value=0.0, key=f"in_{index}")
        if ile > 0:
            zamowienie_input.append({"idx": index, "ile": ile, "pozostalo_min": ile * wydajnosc[index]})

# Generowanie planu
if st.button("Generuj Harmonogram"):
    if not zamowienie_input:
        st.warning("Wpisz ilości palet w panelu bocznym.")
    else:
        dni_planu = {}
        czas_dniowki = 840  # 14h (6-22)
        
        aktualny_dzien = data_startu
        wolny_czas_dzis = czas_dniowki
        
        zadanie_idx = 0
        
        while zadanie_idx < len(zamowienie_input):
            dzien_key = aktualny_dzien.strftime("%d.%m.%Y (%A)")
            if dzien_key not in dni_planu:
                dni_planu[dzien_key] = []
            
            zadanie = zamowienie_input[zadanie_idx]
            czas_do_ulokowania = min(zadanie["pozostalo_min"], wolny_czas_dzis)
            
            ile_palet = czas_do_ulokowania / wydajnosc[zadanie["idx"]]
            
            # Jeśli ten sam artykuł już jest w tym dniu, zsumuj go
            if dni_planu[dzien_key] and dni_planu[dzien_key][-1]["art"] == zadanie["idx"]:
                dni_planu[dzien_key][-1]["ilosc"] += ile_palet
            else:
                dni_planu[dzien_key].append({"art": zadanie["idx"], "ilosc": ile_palet})
            
            zadanie["pozostalo_min"] -= czas_do_ulokowania
            wolny_czas_dzis -= czas_do_ulokowania
            
            if zadanie["pozostalo_min"] <= 0:
                zadanie_idx += 1
            
            if wolny_czas_dzis <= 0 or zadanie_idx >= len(zamowienie_input):
                aktualny_dzien += datetime.timedelta(days=1)
                wolny_czas_dzis = czas_dniowki

        # Wyświetlanie siatki (grid) - 5 kolumn na wiersz (jak dni robocze)
        dni_list = list(dni_planu.keys())
        for i in range(0, len(dni_list), 5):
            cols = st.columns(5)
            for j in range(5):
                if i + j < len(dni_list):
                    dzien_str = dni_list[i + j]
                    with cols[j]:
                        st.markdown(f"""
                            <div class="day-card">
                                <div class="day-header">{dzien_str}</div>
                            </div>
                        """, unsafe_allow_html=True)
                        for pozycja in dni_planu[dzien_str]:
                            st.markdown(f"""
                                <div class="art-row">
                                    <span><b>{pozycja['art']}</b></span>
                                    <span>{round(pozycja['ilosc'], 1)} pal.</span>
                                </div>
                            """, unsafe_allow_html=True)
