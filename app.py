import streamlit as st
import datetime
import pandas as pd

# 1. Dane stałe
DNI_PL = {
    "Monday": "Poniedziałek", "Tuesday": "Wtorek", "Wednesday": "Środa",
    "Thursday": "Czwartek", "Friday": "Piątek", "Saturday": "Sobota", "Sunday": "Niedziela"
}

MIESIACE_PL = {
    1: "Styczeń", 2: "Luty", 3: "Marzec", 4: "Kwiecień", 5: "Maj", 6: "Czerwiec",
    7: "Lipiec", 8: "Sierpień", 9: "Wrzesień", 10: "Październik", 11: "Listopad", 12: "Grudzień"
}

WYDAJNOSC = {
    "232": 70, "233": 60, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Planista JIT - Poprawna Kolejność", layout="wide")

if 'kolejka' not in st.session_state:
    st.session_state.kolejka = []

# --- NOWA LOGIKA ZABEZPIECZAJĄCA KOLEJNOŚĆ ---
@st.cache_data
def generuj_dane_jit(kolejka_tuple, data_dzisiejsza):
    if not kolejka_tuple:
        return {}, [], pd.DataFrame()
    
    # 1. Sortujemy zamówienia od NAJWCZEŚNIEJSZEJ wysyłki (29.03 przed 30.03)
    zadania = [dict(z) for z in kolejka_tuple]
    zadania = sorted(zadania, key=lambda x: x['termin'])
    
    limit_minut = 840
    plan_roboczy = {} # Słownik zajętości minut w danym dniu
    wyniki_produkcji = []

    # 2. Przetwarzamy każde zamówienie po kolei (Gwarancja priorytetu)
    for z in zadania:
        ilosc_do_zrobienia = z['ile']
        wyd = WYDAJNOSC.get(z["art"], 70)
        
        # Próbujemy planować jak najpóźniej, ale przed wysyłką
        # Zaczynamy od dnia przed wysyłką i cofamy się
        dzien_planowania = z['termin'] - datetime.timedelta(days=1)
        
        while ilosc_do_zrobienia > 0:
            # Nie planujemy w przeszłości
            if dzien_planowania < data_dzisiejsza:
                # Jeśli brakło miejsca do dnia dzisiejszego, resztę wrzucamy w nadgodziny dzisiaj
                d_key_dzis = data_dzisiejsza.strftime("%Y-%m-%d")
                wyniki_produkcji.append({
                    "data_sort": data_dzisiejsza,
                    "Data Produkcji": data_dzisiejsza.strftime("%d.%m"),
                    "Dzień": DNI_PL.get(data_dzisiejsza.strftime("%A")),
                    "Artykuł": z["art"],
                    "Palety": int(ilosc_do_zrobienia),
                    "Kraj": z.get("kraj", "Czechy"),
                    "Data Wysyłki": z["termin"].strftime("%d.%m") + " ⚠️ PILNE",
                    "Miesiac": data_dzisiejsza.month
                })
                ilosc_do_zrobienia = 0
                break

            d_key = dzien_planowania.strftime("%Y-%m-%d")
            if d_key not in plan_roboczy:
                plan_roboczy[d_key] = limit_minut
            
            wolny_czas = plan_roboczy[d_key]
            
            if wolny_czas >= wyd:
                ile_dzis = min(wolny_czas // wyd, ilosc_do_zrobienia)
                if ile_dzis > 0:
                    wyniki_produkcji.append({
                        "data_sort": dzien_planowania,
                        "Data Produkcji": dzien_planowania.strftime("%d.%m"),
                        "Dzień": DNI_PL.get(dzien_planowania.strftime("%A")),
                        "Artykuł": z["art"],
                        "Palety": int(ile_dzis),
                        "Kraj": z.get("kraj", "Czechy"),
                        "Data Wysyłki": z["termin"].strftime("%d.%m"),
                        "Miesiac": dzien_planowania.month
                    })
                    ilosc_do_zrobienia -= ile_dzis
                    plan_roboczy[d_key] -= (ile_dzis * wyd)
            
            # Jeśli w tym dniu nie ma już miejsca LUB skończyliśmy zadanie, 
            # pętla przejdzie do dnia wcześniej dla pozostałej ilości towaru
            dzien_planowania -= datetime.timedelta(days=1)

    # Przygotowanie widoku
    dni_wyswietl = {}
    # Sortowanie końcowe kafelków chronologicznie
    raport_lista = sorted(wyniki_produkcji, key=lambda x: x['data_sort'])
    
    for r in raport_lista:
        dk = r['Data Produkcji']
        if dk not in dni_wyswietl:
            dni_wyswietl[dk] = {"dzien": r['Dzień'], "suma": 0, "p": []}
        dni_wyswietl[dk]["p"].append(r)
        dni_wyswietl[dk]["suma"] += r["Palety"]
    
    return dni_wyswietl, raport_lista

# --- INTERFEJS ---
st.title("🥛 Planista Produkcji - Poprawka Kolejności")

with st.sidebar:
    st.header("Zarządzanie")
    if st.button("➕ DODAJ NOWE ZAMÓWIENIE", type="primary", use_container_width=True):
        st.session_state.pokaz_okno = True
    if st.button("🗑️ CZYŚĆ PLAN", use_container_width=True):
        st.session_state.kolejka = []
        st.cache_data.clear()
        st.rerun()
    
    st.divider()
    if st.session_state.kolejka:
        st.subheader("✏️ Edycja")
        daty = sorted(list(set([z['termin'] for z in st.session_state.kolejka])))
        for d in daty:
            with st.expander(f"Wysyłka {d.strftime('%d.%m')}"):
                if st.button("Usuń tę datę", key=f"del_{d}"):
                    st.session_state.kolejka = [z for z in st.session_state.kolejka if z['termin'] != d]
                    st.rerun()

if st.session_state.get('pokaz_okno'):
    with st.container():
        st.markdown("### Nowe zamówienie")
        c1, c2 = st.columns(2)
        kraj = c1.selectbox("Kierunek:", ["Czechy", "Słowacja"])
        dt = c2.date_input("Data wysyłki:", datetime.date.today() + datetime.timedelta(days=3))
        cols = st.columns(2)
        pobrane = []
        for i, art_id in enumerate(WYDAJNOSC.keys()):
            with cols[i % 2]:
                v = st.number_input(f"Art {art_id}", min_value=0, step=1)
                if v > 0: pobrane.append({"art": art_id, "ile": v})
        if st.button("ZATWIERDŹ"):
            for p in pobrane:
                st.session_state.kolejka.append({"art": p["art"], "ile": p["ile"], "termin": dt, "kraj": kraj})
            st.session_state.pokaz_okno = False
            st.rerun()

# --- WIDOK ---
if st.session_state.kolejka:
    k_tuple = tuple(tuple(d.items()) for d in st.session_state.kolejka)
    dni, raport_surowy = generuj_dane_jit(k_tuple, datetime.date.today())
    df_full = pd.DataFrame(raport_surowy)

    st.subheader("🗓️ Harmonogram Produkcji (Priorytet Daty Wysyłki)")
    siatka = st.columns(5)
    for i, dk in enumerate(sorted(dni.keys(), key=lambda x: datetime.datetime.strptime(x, "%d.%m"))):
        with siatka[i % 5]:
            info = dni[dk]
            st.markdown(f"""<div style="border:1px solid #ddd; border-radius:10px; padding:8px; background-color:#f8f9fa;">
                <b style="color:#1f77b4;">{dk}</b> ({info['dzien']})<br>
                <b>Suma: {info['suma']} pal.</b><hr style="margin:4px 0;">""", unsafe_allow_html=True)
            for p in info["p"]:
                bg = "#d4edda" if p["Kraj"] == "Słowacja" else "white"
                st.markdown(f"""<div style="background-color:{bg}; border:1px solid #eee; padding:3px 6px; border-radius:4px; margin-bottom:3px;">
                    <b>{p['Artykuł']}</b>: {p['Palety']} pal.<br>
                    <small>📦 Wysyłka: {p['Data Wysyłki']}</small>
                </div>""", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("Brak zamówień.")
