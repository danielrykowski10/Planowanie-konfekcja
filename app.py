import streamlit as st
import datetime
import pandas as pd

# 1. Dane stałe
DNI_PL = {
    "Monday": "Poniedziałek", "Tuesday": "Wtorek", "Wednesday": "Środa",
    "Thursday": "Czwartek", "Friday": "Piątek", "Saturday": "Sobota", "Sunday": "Niedziela"
}

WYDAJNOSC = {
    "232": 70, "233": 60, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Planista Produkcji JIT", layout="wide")

if 'kolejka' not in st.session_state:
    st.session_state.kolejka = []

# --- NOWA, BŁYSKAWICZNA LOGIKA LINIOWA ---
@st.cache_data
def generuj_plan_liniowy(kolejka_tuple, data_dzis):
    if not kolejka_tuple: return {}

    # Konwersja do listy słowników i sortowanie po dacie wysyłki (Priorytet 1)
    zadania = [dict(z) for z in kolejka_tuple]
    zadania = sorted(zadania, key=lambda x: x['termin'])
    
    plan_wynikowy = []
    data_kursora = data_dzis
    
    CZAS_NETTO = 420  # 7h pracy na zmianę
    MAX_2_ZMIANY = 840 # 14h pracy (2 zmiany)
    
    limit_dzienny = MAX_2_ZMIANY # Możesz tu zmienić na stałe 420 jeśli wolicie 1 zmianę
    pozostalo_minut_dzis = limit_dzienny
    ostatni_artykul = None

    while zadania:
        # Szukamy zadania z najbliższym terminem, które pasuje do ostatniego artykułu (Optymalizacja przezbrojeń)
        najblizszy_termin = zadania[0]['termin']
        z_idx = 0
        
        for i, z_temp in enumerate(zadania):
            if z_temp['termin'] == najblizszy_termin and z_temp['art'] == ostatni_artykul:
                z_idx = i
                break
        
        z = zadania.pop(z_idx)
        art = z['art']
        ile_palet = z['ile']
        wyd = WYDAJNOSC.get(art, 70)
        
        while ile_palet > 0:
            # Sprawdzamy czy nie planujemy po wysyłce (jeśli tak, wymuszamy produkcję dzisiaj)
            uzyta_data = data_kursora if data_kursora < z['termin'] else data_dzis
            
            ile_moze_wejsc = pozostalo_minut_dzis // wyd
            
            if ile_moze_wejsc > 0:
                produkcja = min(ile_moze_wejsc, ile_palet)
                plan_wynikowy.append({
                    "Data": uzyta_data.strftime("%d.%m"),
                    "Dzień": DNI_PL.get(uzyta_data.strftime("%A")),
                    "Art": art,
                    "Palety": int(produkcja),
                    "Kraj": z.get("kraj", "Czechy"),
                    "Wysyłka": z["termin"].strftime("%d.%m"),
                    "sort_key": uzyta_data
                })
                ile_palet -= produkcja
                pozostalo_minut_dzis -= (produkcja * wyd)
                ostatni_artykul = art
            
            if ile_palet > 0: # Jeśli towar został, a dzień pełny -> skaczemy do jutra
                data_kursora += datetime.timedelta(days=1)
                if data_kursora.weekday() == 6: data_kursora += datetime.timedelta(days=1)
                pozostalo_minut_dzis = limit_dzienny
                # Jeśli przeskoczyliśmy dzień, kursor artykułu się nie resetuje, 
                # pętla spróbuje dokończyć ten sam artykuł rano.

    # Grupowanie pod kafelki
    widok = {}
    for r in plan_wynikowy:
        dk = r['Data']
        if dk not in widok: widok[dk] = {"dz": r['Dzień'], "suma": 0, "p": []}
        widok[dk]["p"].append(r)
        widok[dk]["suma"] += r["Palety"]
    return widok

# --- INTERFEJS ---
st.title("🥛 Planista Produkcji - Szybka Optymalizacja")

with st.sidebar:
    st.header("Zarządzanie")
    if st.button("➕ DODAJ ZAMÓWIENIE", type="primary", use_container_width=True): 
        st.session_state.pokaz_f = True
    if st.button("🗑️ WYCZYŚĆ WSZYSTKO", use_container_width=True):
        st.session_state.kolejka = []
        st.cache_data.clear()
        st.rerun()

if st.session_state.get('pokaz_f'):
    with st.form("form_dodaj"):
        c1, c2 = st.columns(2)
        kraj_sel = c1.selectbox("Kierunek:", ["Czechy", "Słowacja"])
        term_sel = c2.date_input("Termin wysyłki:", datetime.date.today() + datetime.timedelta(days=2))
        st.write("Ilości palet:")
        cols = st.columns(3)
        lista_nowych = []
        for i, art_id in enumerate(WYDAJNOSC.keys()):
            with cols[i % 3]:
                v = st.number_input(f"Art {art_id}", min_value=0, step=1)
                if v > 0: lista_nowych.append({"art": art_id, "ile": v})
        if st.form_submit_button("ZATWIERDŹ"):
            for n in lista_nowych:
                st.session_state.kolejka.append({"art": n['art'], "ile": n['ile'], "termin": term_sel, "kraj": kraj_sel})
            st.session_state.pokaz_f = False
            st.rerun()

if st.session_state.kolejka:
    # Generowanie planu
    k_tuple = tuple(tuple(d.items()) for d in st.session_state.kolejka)
    dni = generuj_plan_liniowy(k_tuple, datetime.date.today())

    # Wyświetlanie kafelków
    st.subheader("🗓️ Harmonogram Produkcji")
    grid = st.columns(5)
    sort_dni = sorted(dni.keys(), key=lambda x: datetime.datetime.strptime(x, "%d.%m"))
    
    for i, data_klucz in enumerate(sort_dni):
        with grid[i % 5]:
            d_info = dni[data_klucz]
            st.markdown(f"""
            <div style="border:1px solid #ddd; border-radius:10px; padding:10px; background-color:white; margin-bottom:10px; min-height:180px;">
                <b style="color:#1f77b4; font-size:15px;">{data_klucz} ({d_info['dz']})</b><br>
                <b style="color:green;">Łącznie: {d_info['suma']} pal.</b><hr style="margin:5px 0;">
            """, unsafe_allow_html=True)
            for p in d_info["p"]:
                bg_col = "#d4edda" if p["Kraj"] == "Słowacja" else "#f8f9fa"
                st.markdown(f"""
                <div style="background-color:{bg_col}; padding:5px; border-radius:5px; margin-bottom:4px; border:1px solid #eee; font-size:12px;">
                    <b>{p['Art']}</b>: {p['Palety']} pal.<br>
                    <small>Wysyłka: {p['Wysyłka']} ({p['Kraj']})</small>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("Brak zamówień. Użyj panelu bocznego, aby dodać dane.")
