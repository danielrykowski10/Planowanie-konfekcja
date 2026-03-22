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

st.set_page_config(page_title="Planista Produkcji", layout="wide")

if 'kolejka' not in st.session_state:
    st.session_state.kolejka = []

# --- LOGIKA PLANOWANIA (SZYBKA) ---
@st.cache_data
def generuj_plan(kolejka_tuple, data_dzis):
    if not kolejka_tuple: return {}, []

    # Sortowanie po dacie wysyłki (najpierw te, co wyjeżdżają najwcześniej)
    zadania = sorted([dict(z) for z in kolejka_tuple], key=lambda x: x['termin'])
    
    plan_dni = {}
    raport_produkcji = []
    data_kursora = data_dzis
    LIMIT = 480 # 8h zmiany

    for z in zadania:
        ile = z['ile']
        wyd = WYDAJNOSC.get(z["art"], 70)
        
        while ile > 0:
            d_key = data_kursora.strftime("%Y-%m-%d")
            
            # Jeśli kursor daty przekroczył termin wysyłki, wracamy do dzisiaj (produkcja ratunkowa)
            if data_kursora > z['termin']: 
                data_kursora = data_dzis
                d_key = data_kursora.strftime("%Y-%m-%d")
            
            if d_key not in plan_dni: plan_dni[d_key] = LIMIT
            
            wolny = plan_dni[d_key]
            if wolny >= wyd:
                produkcja = min(wolny // wyd, ile)
                if produkcja > 0:
                    raport_produkcji.append({
                        "Data": data_kursora.strftime("%d.%m"),
                        "Dzień": DNI_PL.get(data_kursora.strftime("%A")),
                        "Art": z["art"],
                        "Palety": int(produkcja),
                        "Kraj": z.get("kraj", "Czechy"),
                        "Wysyłka": z["termin"].strftime("%d.%m"),
                        "dt_sort": data_kursora
                    })
                    ile -= produkcja
                    plan_dni[d_key] -= (produkcja * wyd)
            
            if ile > 0: # Jeśli towar został, a zmiana 8h pełna -> następny dzień
                data_kursora += datetime.timedelta(days=1)
                if data_kursora.weekday() == 6: # Pomiń niedzielę
                    data_kursora += datetime.timedelta(days=1)
            else:
                break 
                
    # Grupowanie pod kafelki
    dni_widok = {}
    for r in raport_produkcji:
        dk = r['Data']
        if dk not in dni_widok: dni_widok[dk] = {"dzien": r['Dzień'], "suma": 0, "p": []}
        dni_widok[dk]["p"].append(r)
        dni_widok[dk]["suma"] += r["Palety"]
    
    return dni_widok

# --- INTERFEJS ---
st.title("🥛 Planista Produkcji - Harmonogram")

with st.sidebar:
    st.header("Zarządzanie")
    if st.button("➕ DODAJ ZAMÓWIENIE", type="primary", use_container_width=True): 
        st.session_state.pokaz_form = True
    
    if st.button("🗑️ WYCZYŚĆ WSZYSTKO", use_container_width=True):
        st.session_state.kolejka = []
        st.cache_data.clear()
        st.rerun()
    
    st.divider()
    # Lista zamówień do podglądu/usuwania w sidebarze
    if st.session_state.kolejka:
        st.subheader("📦 Aktywne zamówienia")
        for i, z in enumerate(st.session_state.kolejka):
            st.caption(f"{z['art']} | {z['ile']} pal. | {z['kraj']} | Wysyłka: {z['termin'].strftime('%d.%m')}")

if st.session_state.get('pokaz_form'):
    with st.form("form"):
        c1, c2 = st.columns(2)
        kraj = c1.selectbox("Kraj docelowy:", ["Czechy", "Słowacja"])
        termin = c2.date_input("Data wysyłki (Termin):", datetime.date.today() + datetime.timedelta(days=2))
        st.write("Wpisz ilości palet:")
        cols = st.columns(3)
        nowe = []
        for i, art in enumerate(WYDAJNOSC.keys()):
            with cols[i % 3]:
                v = st.number_input(f"Art {art}", min_value=0, key=f"inp_{art}")
                if v > 0: nowe.append({"art": art, "ile": v})
        if st.form_submit_button("DODAJ DO PLANU"):
            for n in nowe: 
                st.session_state.kolejka.append({"art": n['art'], "ile": n['ile'], "termin": termin, "kraj": kraj})
            st.session_state.pokaz_form = False
            st.rerun()

# --- WYŚWIETLANIE HARMONOGRAMU ---
if st.session_state.kolejka:
    k_tuple = tuple(tuple(d.items()) for d in st.session_state.kolejka)
    dni = generuj_plan(k_tuple, datetime.date.today())

    st.subheader("🗓️ Plan Produkcji (Zmiany 8h)")
    cols = st.columns(5)
    sorted_days = sorted(dni.keys(), key=lambda x: datetime.datetime.strptime(x, "%d.%m"))
    
    for i, dk in enumerate(sorted_days):
        with cols[i % 5]:
            d_info = dni[dk]
            st.markdown(f"""
                <div style="border:1px solid #ddd; border-radius:10px; padding:10px; background-color:white; margin-bottom:15px;">
                    <b style="color:#1f77b4; font-size:16px;">{dk} ({d_info['dzien']})</b><br>
                    <b style="color:green;">Łącznie: {d_info['suma']} pal.</b><hr style="margin:5px 0;">
            """, unsafe_allow_html=True)
            
            for p in d_info["p"]:
                bg = "#d4edda" if p["Kraj"] == "Słowacja" else "#f8f9fa"
                st.markdown(f"""
                    <div style="background-color:{bg}; padding:6px; border-radius:5px; margin-bottom:5px; border:1px solid #eee; font-size:13px;">
                        <b>{p['Art']}</b>: {p['Palety']} pal.<br>
                        <small>📦 Wysyłka: {p['Wysyłka']} ({p['Kraj']})</small>
                    </div>
                """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("Brak aktywnych zamówień. Użyj przycisku w panelu bocznym, aby dodać dane.")
