import streamlit as st
import datetime

# Baza wydajności (minuty na 1 paletę)
wydajnosc = {
    "232": 70, "233": 60, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Planista Mleczarnia", page_icon="🥛", layout="wide")
st.title("🥛 Planista Wielu Zamówień")

st.sidebar.header("Ustawienia zmiany")
data_startu = st.sidebar.date_input("Dzień rozpoczęcia:", datetime.datetime.now())
czas_zmiany = 420  # 7h netto

st.write("### 📝 Wprowadź ilość palet dla poszczególnych indeksów:")

# Tworzymy formularz do wpisywania wielu ilości na raz
zamowienie = {}
cols = st.columns(3) # Rozbijamy na 3 kolumny, żeby było czytelnie
for i, index in enumerate(wydajnosc.keys()):
    with cols[i % 3]:
        ile = st.number_input(f"Indeks {index}", min_value=0.0, step=1.0, value=0.0)
        if ile > 0:
            zamowienie[index] = ile

if st.button("Generuj Harmonogram Produkcji"):
    if not zamowienie:
        st.warning("Wpisz chociaż jedną paletę!")
    else:
        # Obliczamy łączną kolejkę zadań (zadanie = (indeks, minuty))
        kolejka_zadan = []
        calkowity_czas_wszystkich = 0
        for idx, ilosc in zamowienie.items():
            czas_za_indeks = ilosc * wydajnosc[idx]
            kolejka_zadan.append({"idx": idx, "ile": ilosc, "pozostalo_min": czas_za_indeks})
            calkowity_czas_wszystkich += czas_za_indeks

        st.write(f"--- \nŁączny czas produkcji: **{int(calkowity_czas_wszystkich)} min** (ok. {round(calkowity_czas_wszystkich/60, 1)}h)")

        teraz = datetime.datetime.now()
        aktualna_data = data_startu
        # Logika startu zmiany
        if teraz.hour >= 22:
            aktualna_data += datetime.timedelta(days=1)
            start_od_zmiany = 1
        elif teraz.hour >= 14:
            start_od_zmiany = 2
        else:
            start_od_zmiany = 1

        dzien_offset = 0
        zadanie_idx = 0 # Który produkt z listy teraz robimy

        while zadanie_idx < len(kolejka_zadan):
            data_str = (aktualna_data + datetime.timedelta(days=dzien_offset)).strftime("%d.%m (%A)")
            st.info(f"📅 **{data_str}**")
            
            # Przechodzimy przez zmiany (I i II)
            for nr_zmiany in [1, 2]:
                if dzien_offset == 0 and nr_zmiany < start_od_zmiany:
                    continue
                
                wolny_czas_na_zmianie = czas_zmiany
                st.success(f"**Zmiana {'I' if nr_zmiany==1 else 'II'} ({'6-14' if nr_zmiany==1 else '14-22'})**")
                
                while wolny_czas_na_zmianie > 0 and zadanie_idx < len(kolejka_zadan):
                    zadanie = kolejka_zadan[zadanie_idx]
                    czas_do_pobrania = min(zadanie["pozostalo_min"], wolny_czas_na_zmianie)
                    
                    ile_palet_weszlo = round(czas_do_pobrania / wydajnosc[zadanie["idx"]], 1)
                    if ile_palet_weszlo > 0:
                        st.write(f"➡️ Indeks **{zadanie['idx']}**: {ile_palet_weszlo} palet")
                    
                    zadanie["pozostalo_min"] -= czas_do_pobrania
                    wolny_czas_na_zmianie -= czas_do_pobrania
                    
                    if zadanie["pozostalo_min"] <= 0:
                        zadanie_idx += 1
                
                if zadanie_idx >= len(kolejka_zadan):
                    break
            
            dzien_offset += 1
