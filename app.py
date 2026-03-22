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

st.set_page_config(page_title="Szybki Planista Produkcji", layout="wide")

if 'kolejka' not in st.session_state:
    st.session_state.kolejka = []

# --- BŁYSKAWICZNA LOGIKA ---
@st.cache_data
def generuj_plan_szybki(kolejka_tuple, data_dzis):
    if not kolejka_tuple: return {}

    # Sortowanie po terminie
    zadania = sorted([dict(z) for z in kolejka_tuple], key=lambda x: x['termin'])
    
    plan_dni = {}
    raport = []
    data_kursora = data_dzis
    
    # Realne czasy (netto)
    CZAS_NETTO = 420 
    MAX_2_ZMIANY = 840 

    for z in zadania:
        ile = z['ile']
        wyd = WYDAJNOSC.get(z["art"], 70)
        
        while ile > 0:
            d_key = data_kursora.strftime("%Y-%m-%d")
            
            # Reset kursora jeśli zamówienie jest "na już"
            if data_kursora > z['termin']: data_kursora = data_dzis
            
            if d_key not in plan_dni:
                plan_dni[d_key] = MAX_2_ZMIANY if ile * wyd > CZAS_NETTO else CZAS_NETTO
            
            wolny = plan_dni[d_key]
            if wolny >= wyd:
                produkcja = min(wolny // wyd, ile)
                if produkcja > 0:
                    raport.append({
                        "Data": data_kursora.strftime("%d.%m"),
                        "Dzień": DNI_PL.get(data_kursora.strftime("%A")),
                        "Art": z["art"],
                        "Palety": int(produkcja),
                        "Kraj": z.get("kraj", "Czechy"),
                        "Wysyłka": z["termin"].strftime("%d.%m"),
                        "sort_key": data_kursora
                    })
                    ile -= produkcja
                    plan_dni[d_key] -= (produkcja * wyd)
            
            if ile > 0:
                data_kursora += datetime.timedelta(days=1)
                if data_kursora.weekday() == 6: data_kursora += datetime.timedelta(days=1)
            else:
                break
                
    # Grupowanie
    wynik = {}
    for r in raport:
        dk = r['Data']
        if dk not in wynik: wynik[dk] = {"dz": r['Dzień'], "suma": 0, "p": []}
        wynik[dk]["p"].append(r)
        wynik[dk]["suma"] += r["Palety"]
    return wynik

# --- INTERFEJS ---
with st.sidebar:
    st.header("Zarządzanie")
    if st.button("➕ DODAJ ZAMÓWIENIE", type="primary", use_container_width=True): 
        st.session_state.pokaz_f = True
    if st.button("🗑️ WYCZYŚĆ WSZYSTKO", use_container_width=True):
        st.session_state.kolejka = []
        st.cache_data.clear()
        st.rerun()

if st.session_state.get('pokaz_f'):
    with st.form("f_add"):
        c1, c2 = st.columns(2)
        kraj = c1.selectbox("Kierunek:", ["Czechy", "Słowacja"])
        term = c2.date_input("Termin wysyłki:", datetime.date.today() + datetime.timedelta(days=2))
        st.write("Ilości palet:")
        cols = st.columns(3)
        nowe = []
        for i, art in enumerate(WYDAJNOSC.keys()):
            with cols[i % 3]:
                v = st.number_input(f"Art {art}", min_value=0, step=1)
                if v > 0: nowe.append({"art": art, "ile": v})
        if st.form_submit_button("ZATWIERDŹ"):
            for n in nowe: st.session_state.kolejka.append({"art": n['art'], "ile": n['ile'], "termin": term, "kraj": kraj})
            st.session_state.pokaz_f = False
            st.rerun()

st.title("🥛 Planista Produkcji")

if st.session_state.kolejka:
    k_tuple = tuple(tuple(d.items()) for d in st.session_state.kolejka)
    dni = generuj_plan_szybki(k_tuple, datetime.date.today())

    cols = st.columns(5)
    sorted_days = sorted(dni.keys(), key=lambda x: datetime.datetime.strptime(x, "%d.%m"))
    
    for i, dk in enumerate(sorted_days):
        with cols[i % 5]:
            inf = dni[dk]
            st.markdown(f"""
            <div style="border:1px solid #ddd; border-radius:10px; padding:10px; background-color:white; margin-bottom:10px;">
                <b style="color:#1f77b4;">{dk} ({inf['dz']})</b><br>
                <b style="color:green;">Suma: {inf['suma']} pal.</b><hr style="margin:5px 0;">
            """, unsafe_allow_html=True)
            for p in inf["p"]:
                bg = "#d4edda" if p["Kraj"] == "Słowacja" else "#f8f9fa"
                st.markdown(f"""
                <div style="background-color:{bg}; padding:5px; border-radius:5px; margin-bottom:4px; border:1px solid #eee; font-size:12px;">
                    <b>{p['Art']}</b>: {p['Palety']} pal.<br>
                    <small>Wysyłka: {p['Wysyłka']} ({p['Kraj']})</small>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("Brak zamówień.")
