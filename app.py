import streamlit as st
import datetime

# Baza wydajności (minuty na 1 paletę)
wydajnosc = {
    "232": 70, "233": 60, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Planista Mleczarnia", page_icon="🥛")
st.title("🥛 Planista Konfekcji Sera")

# Wybór artykułu
artykul = st.selectbox("Wybierz artykuł (Indeks):", list(wydajnosc.keys()))
ilosc_palet = st.number_input("Ile palet do zrobienia?", min_value=0.5, step=0.5, value=1.0)

# Ustalenie startu (teraz)
teraz = datetime.datetime.now()
data_startu = st.date_input("Dzień rozpoczęcia:", teraz)
godzina = teraz.hour

if st.button("Generuj Plan"):
    czas_jednej = wydajnosc[artykul]
    pozostalo_minut = ilosc_palet * czas_jednej
    czas_zmiany = 420  # 7h netto
    
    st.write(f"### 📋 Wynik dla: {artykul}")
    st.write(f"Łączny czas: **{int(pozostalo_minut)} min**")
    
    aktualna_data = data_startu
    # Jeśli planujesz dzisiaj po 22:00, zacznij od jutra rana
    if godzina >= 22:
        aktualna_data += datetime.timedelta(days=1)
        start_od_zmiany = 1
    elif godzina >= 14:
        start_od_zmiany = 2
    else:
        start_od_zmiany = 1

    dzien = 0
    while pozostalo_minut > 0:
        data_str = (aktualna_data + datetime.timedelta(days=dzien)).strftime("%d.%m (%A)")
        st.info(f"📅 **{data_str}**")
        
        # Zmiana I
        if start_od_zmiany <= 1:
            robota = min(pozostalo_minut, czas_zmiany)
            p_z1 = round(robota / czas_jednej, 1)
            st.success(f"I zmiana (6-14): **{p_z1} palet**")
            pozostalo_minut -= robota
        
        if pozostalo_minut <= 0: break
            
        # Zmiana II
        robota = min(pozostalo_minut, czas_zmiany)
        p_z2 = round(robota / czas_jednej, 1)
        st.success(f"II zmiana (14-22): **{p_z2} palet**")
        pozostalo_minut -= robota
        
        start_od_zmiany = 1 # Kolejne dni zaczynamy od I zmiany
        dzien += 1
