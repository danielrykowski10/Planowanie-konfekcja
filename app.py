import streamlit as st
import datetime
import pandas as pd

# 1. Konfiguracja
DNI_PL = {
    "Monday": "Poniedziałek", "Tuesday": "Wtorek", "Wednesday": "Środa",
    "Thursday": "Czwartek", "Friday": "Piątek", "Saturday": "Sobota", "Sunday": "Niedziela"
}

WYDAJNOSC = {
    "232": 70, "233": 60, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Planista Produkcji - Pełne Zmiany", layout="wide")

if 'kolejka' not in st.session_state:
    st.session_state.kolejka = []

# --- ZOPTYMALIZOWANA LOGIKA PLANOWANIA ---
@st.cache_data
def generuj_plan_pelne_zmiany(kolejka_tuple, data_dzis):
    if not kolejka_tuple:
        return {}, []

    # 1. Pobieramy zadania i sortujemy po dacie wysyłki (najpierw pilne)
    zadania = [dict(z) for z in kolejka_tuple]
    zadania = sorted(zadania, key=lambda x: x['termin'])

    MINUTY_ZMIANA = 480 # 8 godzin pracy
    plan_dni = {}
    raport_produkcji = []

    # Aktualna data, od której zaczynamy wypełnianie dni (zaczynamy od jutra lub dzisiaj)
    data_kursora = data_dzis

    for z in zadania:
        ile_do_zrobienia = z['ile']
        wyd = WYDAJNOSC.get(z["art"], 70)

        # Planujemy zamówienie tak długo, aż zostanie zrealizowane
        while ile_do_zrobienia > 0:
            d_key = data_kursora.strftime("%Y-%m-%d")
            
            # Nie planujemy produkcji PO dacie wysyłki (wyjątek: zmiana 6-14 w dzień wysyłki)
            if data_kursora > z['termin']:
                # Jeśli nie zdążyliśmy, wrzucamy jako zaległość na dzisiaj
                data_kursora = data_dzis
                d_key = data_kursora.strftime("%Y-%m-%d")

            if d_key not in plan_dni:
                plan_dni[d_key] = MINUTY_ZMIANA # Zaczynamy nową zmianę 8h
            
            wolny_czas = plan_dni[d_key]
            
            if wolny_czas >= wyd:
                # Ile palet wejdzie do końca tej zmiany (8h)?
                ile_wejdzie = wolny_czas // wyd
                ile_produkujemy = min(ile_wejdzie, ile_do_zrobienia)
                
                if ile_produkujemy > 0:
                    raport_produkcji.append({
                        "data_sort": data_kursora,
                        "Data": data_kursora.strftime("%d.%m"),
                        "Dzień": DNI_PL.get(data_kursora.strftime("%A")),
                        "Art": z["art"],
                        "Palety": int(ile_produkujemy),
                        "Kraj": z.get("kraj", "Czechy"),
                        "Wysyłka": z["termin"].strftime("%d.%m")
                    })
                    ile_do_zrobienia -= ile_produkujemy
                    plan_dni[d_key] -= (ile_produkujemy * wyd)

            # Jeśli zmiana jest pełna (zostało za mało czasu na paletę), przechodzimy do następnego dnia
            if plan_dni[d_key] < wyd:
                data_kursora += datetime.timedelta(days=1)
                # Pomijamy niedziele, jeśli nie pracujecie
                if data_kursora.weekday() == 6: 
                    data_kursora += datetime.timedelta(days=1)
            else:
                # Jeśli zrobiliśmy całe zamówienie, ale w zmianie został czas, 
                # NIE przesuwamy kursora – kolejne zamówienie dociąży ten sam dzień.
                break

    # Grupowanie
    dni_widok = {}
    for r in raport_produkcji:
        dk = r['Data']
        if dk not in dni_widok:
            dni_widok[dk] = {"dzien": r['Dzień'], "suma": 0, "p": []}
        dni_widok[dk]["p"].append(r)
        dni_widok[dk]["suma"] += r["Palety"]

    return dni_widok, raport_produkcji

# --- WIDOK ---
st.title("🥛 Planista Produkcji - Optymalizacja Zmian")

with st.sidebar:
    st.header("Zarządzanie")
    if st.button("➕ DODAJ ZAMÓWIENIE", type="primary"):
        st.session_state.pokaz_form = True
    if st.button("🗑️ WYCZYŚĆ WSZYSTKO"):
        st.session_state.kolejka = []
        st.rerun()

if st.session_state.get('pokaz_form'):
    with st.form("dodaj_form"):
        c1, c2 = st.columns(2)
        kraj = c1.selectbox("Kierunek:", ["Czechy", "Słowacja"])
        termin = c2.date_input("Data wysyłki:", datetime.date.today() + datetime.timedelta(days=2))
        st.write("Ilości palet:")
        cols = st.columns(3)
        nowe = []
        for i, art in enumerate(WYDAJNOSC.keys()):
            with cols[i % 3]:
                v = st.number_input(f"Art {art}", min_value=0, key=f"f_{art}")
                if v > 0: nowe.append({"art": art, "ile": v})
        if st.form_submit_button("DODAJ"):
            for n in nowe:
                st.session_state.kolejka.append({"art": n['art'], "ile": n['ile'], "termin": termin, "kraj": kraj})
            st.session_state.pokaz_form = False
            st.rerun()

if st.session_state.kolejka:
    k_tuple = tuple(tuple(d.items()) for d in st.session_state.kolejka)
    dni, raport = generuj_plan_pelne_zmiany(k_tuple, datetime.date.today())

    st.subheader("🗓️ Harmonogram Produkcji (Dociążanie zmian 8h)")
    cols = st.columns(5)
    for i, dk in enumerate(sorted(dni.keys(), key=lambda x: datetime.datetime.strptime(x, "%d.%m"))):
        with cols[i % 5]:
            d_info = dni[dk]
            st.markdown(f"""
                <div style="border:1px solid #ddd; border-radius:10px; padding:10px; background-color:white; min-height:250px;">
                    <b style="font-size:16px; color:#1f77b4;">{dk} ({d_info['dzien']})</b><br>
                    <b style="color:green;">Suma: {d_info['suma']} pal.</b><hr style="margin:5px 0;">
            """, unsafe_allow_html=True)
            for p in d_info["p"]:
                color = "#d4edda" if p["Kraj"] == "Słowacja" else "#f8f9fa"
                st.markdown(f"""
                    <div style="background-color:{color}; padding:5px; border-radius:5px; margin-bottom:5px; border:1px solid #eee;">
                        <b>{p['Art']}</b>: {p['Palety']} pal.<br>
                        <small>📦 Wysyłka: {p['Wysyłka']}</small>
                    </div>
                """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("Brak zamówień w systemie.")
