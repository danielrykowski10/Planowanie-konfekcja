import streamlit as st
import datetime
import pandas as pd

# 1. Tłumaczenia i wydajność
DNI_PL = {
    "Monday": "Poniedziałek", "Tuesday": "Wtorek", "Wednesday": "Środa",
    "Thursday": "Czwartek", "Friday": "Piątek", "Saturday": "Sobota", "Sunday": "Niedziela"
}

WYDAJNOSC = {
    "232": 70, "233": 60, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Planista JIT - Mleczarnia", layout="wide")

if 'kolejka' not in st.session_state:
    st.session_state.kolejka = []

# --- LOGIKA "JUST IN TIME" (PLANOWANIE OD KOŃCA) ---
@st.cache_data
def generuj_harmonogram_jit(kolejka_tuple, data_dzisiejsza):
    if not kolejka_tuple:
        return {}, []
    
    # Konwersja danych i sortowanie od NAJPÓŹNIEJSZYCH terminów wysyłki
    zadania = [dict(z) for z in kolejka_tuple]
    # Sortujemy po terminie malejąco (najpierw planujemy to, co wyjeżdża najpóźniej)
    zadania = sorted(zadania, key=lambda x: x['termin'], reverse=True)
    
    limit_minut = 840
    plan_roboczy = {} # Słownik: data -> pozostałe minuty

    wyniki_produkcji = []

    for z in zadania:
        ilosc_do_zrobienia = z['ile']
        wyd = WYDAJNOSC.get(z["art"], 70)
        
        # Startujemy planowanie od dnia przed wysyłką
        dzien_planowania = z['termin'] - datetime.timedelta(days=1)
        
        # Nie możemy planować w przeszłości
        if dzien_planowania < data_dzisiejsza:
            dzien_planowania = data_dzisiejsza

        while ilosc_do_zrobienia > 0:
            d_key = dzien_planowania.strftime("%Y-%m-%d")
            
            # Inicjalizacja dnia w kalendarzu roboczym
            if d_key not in plan_roboczy:
                plan_roboczy[d_key] = limit_minut
            
            wolny_czas = plan_roboczy[d_key]
            
            if wolny_czas >= wyd:
                ile_dzis = min(wolny_czas // wyd, ilosc_do_zrobienia)
                
                wyniki_produkcji.append({
                    "data_sort": dzien_planowania,
                    "Data": dzien_planowania.strftime("%d.%m"),
                    "Dzień": DNI_PL.get(dzien_planowania.strftime("%A")),
                    "Art": z["art"],
                    "Palety": int(ile_dzis),
                    "Wysyłka": z["termin"].strftime("%d.%m")
                })
                
                ilosc_do_zrobienia -= ile_dzis
                plan_roboczy[d_key] -= (ile_dzis * wyd)
            
            # Jeśli w tym dniu nie ma już miejsca lub zrobiliśmy co trzeba, cofamy się o jeden dzień
            dzien_planowania -= datetime.timedelta(days=1)
            
            # Bezpiecznik: jeśli cofnęliśmy się przed dzisiaj, a nadal jest towar, musimy go upchać dzisiaj (nadgodziny/priorytet)
            if dzien_planowania < data_dzisiejsza:
                if ilosc_do_zrobienia > 0:
                    # Dodaj do dzisiejszego raportu z ostrzeżeniem o braku czasu
                    wyniki_produkcji.append({
                        "data_sort": data_dzisiejsza,
                        "Data": data_dzisiejsza.strftime("%d.%m"),
                        "Dzień": DNI_PL.get(data_dzisiejsza.strftime("%A")),
                        "Art": z["art"],
                        "Palety": int(ilosc_do_zrobienia),
                        "Wysyłka": z["termin"].strftime("%d.%m") + " ⚠️ PILNE"
                    })
                break

    # Grupowanie wyników do wyświetlenia (sortowanie chronologiczne)
    dni_wyswietl = {}
    raport_finalny = sorted(wyniki_produkcji, key=lambda x: x['data_sort'])
    
    for r in raport_finalny:
        d_key = r['Data']
        if d_key not in dni_wyswietl:
            dni_wyswietl[d_key] = {"dzien": r['Dzień'], "suma": 0, "p": []}
        dni_wyswietl[d_key]["p"].append(r)
        dni_wyswietl[d_key]["suma"] += r["Palety"]

    return dni_wyswietl, raport_finalny

# --- DIALOG ---
@st.dialog("➕ Nowe Zamówienie (JIT)")
def okno_jit():
    cols = st.columns(2)
    nowe = []
    for i, art_id in enumerate(WYDAJNOSC.keys()):
        with cols[i % 2]:
            n = st.number_input(f"Art {art_id}", min_value=0, step=1)
            if n > 0: nowe.append({"art": art_id, "ile": n})
    
    st.divider()
    dt = st.date_input("Data wysyłki (Termin):", datetime.date.today() + datetime.timedelta(days=7))
    
    if st.button("ZAPLANUJ POD WYSYŁKĘ", use_container_width=True, type="primary"):
        if nowe:
            for item in nowe:
                st.session_state.kolejka.append({
                    "art": item["art"], "ile": item["ile"], 
                    "termin": dt, "start": datetime.date.today() # Start techniczny
                })
            st.rerun()

# --- INTERFEJS ---
st.title("🥛 Planista Produkcji - System Just-In-Time")
st.info("System rozplanowuje produkcję tak, aby kończyła się jak najbliżej daty wysyłki.")

with st.sidebar:
    st.header("📦 Aktywne zamówienia")
    for i, item in enumerate(st.session_state.kolejka):
        c_t, c_d = st.columns([4, 1])
        c_t.write(f"**{item['art']}** ({item['ile']} pal.) \n → Wysyłka: {item['termin'].strftime('%d.%m')}")
        if c_d.button("❌", key=f"d_{i}"):
            st.session_state.kolejka.pop(i)
            st.rerun()
    
    if st.button("🗑️ WYCZYŚĆ PLAN"):
        st.session_state.kolejka = []
        st.cache_data.clear()
        st.rerun()

if st.button("➕ DODAJ ZAMÓWIENIE", type="primary"):
    okno_jit()

if st.session_state.kolejka:
    k_tuple = tuple(tuple(d.items()) for d in st.session_state.kolejka)
    dzis = datetime.date.today()
    dni, raport = generuj_harmonogram_jit(k_tuple, dzis)
    
    st.subheader("🗓️ Harmonogram Produkcji (dni robocze)")
    siatka = st.columns(5)
    for i, d_key in enumerate(sorted(dni.keys(), key=lambda x: datetime.datetime.strptime(x, "%d.%m"))):
        with siatka[i % 5]:
            info = dni[d_key]
            st.markdown(f"""
                <div style="border:1px solid #ddd; border-radius:10px; padding:10px; background-color:#f0f2f6;">
                    <b style="font-size:18px; color:#1f77b4;">{d_key}</b><br>
                    <small>{info['dzien']}</small><br>
                    <span style="color:green; font-weight:bold;">Suma: {info['suma']} pal.</span>
                    <hr style="margin:5px 0;">
            """, unsafe_allow_html=True)
            for p in info["p"]:
                st.write(f"**{p['Art']}**: {p['Palety']} pal.")
                st.caption(f"Dla wysyłki: {p['Wysyłka']}")
            st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    st.subheader("🖨️ Tabela zbiorcza")
    df_rep = pd.DataFrame(raport)[["Data", "Dzień", "Art", "Palety", "Wysyłka"]]
    st.table(df_rep)
