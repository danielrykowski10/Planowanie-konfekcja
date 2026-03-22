import streamlit as st
import datetime
import pandas as pd

# 1. Konfiguracja i tłumaczenia
DNI_PL = {
    "Monday": "Poniedziałek", "Tuesday": "Wtorek", "Wednesday": "Środa",
    "Thursday": "Czwartek", "Friday": "Piątek", "Saturday": "Sobota", "Sunday": "Niedziela"
}

WYDAJNOSC = {
    "232": 70, "233": 60, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Planista JIT", layout="wide")

if 'kolejka' not in st.session_state:
    st.session_state.kolejka = []

# --- LOGIKA JIT ---
@st.cache_data
def generuj_harmonogram_jit(kolejka_tuple, data_dzisiejsza):
    if not kolejka_tuple:
        return {}, [], pd.DataFrame()
    
    zadania = [dict(z) for z in kolejka_tuple]
    zadania = sorted(zadania, key=lambda x: x['termin'], reverse=True)
    
    limit_minut = 840
    plan_roboczy = {} 
    wyniki_produkcji = []

    for z in zadania:
        ilosc_do_zrobienia = z['ile']
        wyd = WYDAJNOSC.get(z["art"], 70)
        dzien_planowania = z['termin'] - datetime.timedelta(days=1)
        
        if dzien_planowania < data_dzisiejsza:
            dzien_planowania = data_dzisiejsza

        while ilosc_do_zrobienia > 0:
            d_key = dzien_planowania.strftime("%Y-%m-%d")
            if d_key not in plan_roboczy:
                plan_roboczy[d_key] = limit_minut
            
            wolny_czas = plan_roboczy[d_key]
            if wolny_czas >= wyd:
                ile_dzis = min(wolny_czas // wyd, ilosc_do_zrobienia)
                wyniki_produkcji.append({
                    "data_sort": dzien_planowania,
                    "Data Produkcji": dzien_planowania.strftime("%d.%m"),
                    "Dzień": DNI_PL.get(dzien_en := dzien_planowania.strftime("%A"), dzien_en),
                    "Artykuł": z["art"],
                    "Palety": int(ile_dzis),
                    "Data Wysyłki": z["termin"].strftime("%d.%m")
                })
                ilosc_do_zrobienia -= ile_dzis
                plan_roboczy[d_key] -= (ile_dzis * wyd)
            
            dzien_planowania -= datetime.timedelta(days=1)
            if dzien_planowania < data_dzisiejsza:
                if ilosc_do_zrobienia > 0:
                    wyniki_produkcji.append({
                        "data_sort": data_dzisiejsza,
                        "Data Produkcji": data_dzisiejsza.strftime("%d.%m"),
                        "Dzień": DNI_PL.get(data_dzisiejsza.strftime("%A")),
                        "Artykuł": z["art"],
                        "Palety": int(ilosc_do_zrobienia),
                        "Data Wysyłki": z["termin"].strftime("%d.%m") + " ⚠️ PILNE"
                    })
                break

    # 1. Przygotowanie danych do kafelków
    dni_wyswietl = {}
    raport_finalny = sorted(wyniki_produkcji, key=lambda x: x['data_sort'])
    for r in raport_finalny:
        d_key = r['Data Produkcji']
        if d_key not in dni_wyswietl:
            dni_wyswietl[d_key] = {"dzien": r['Dzień'], "suma": 0, "p": []}
        dni_wyswietl[d_key]["p"].append(r)
        dni_wyswietl[d_key]["suma"] += r["Palety"]

    # 2. Tabela zbiorcza (Artykuł vs Data Wysyłki)
    df_temp = pd.DataFrame(wyniki_produkcji)
    tabela_zbiorcza = df_temp.pivot_table(
        index="Artykuł", 
        columns="Data Wysyłki", 
        values="Palety", 
        aggfunc="sum", 
        fill_value=0
    )
    
    return dni_wyswietl, raport_finalny, tabela_zbiorcza

# --- INTERFEJS ---
st.title("🥛 Planista JIT - Produkcja i Wysyłka")

with st.sidebar:
    st.header("📦 Zarządzanie")
    if st.button("➕ DODAJ ZAMÓWIENIE", type="primary", use_container_width=True):
        st.session_state.open_dialog = True
    
    st.divider()
    for i, item in enumerate(st.session_state.kolejka):
        c_t, c_d = st.columns([4, 1])
        c_t.write(f"**{item['art']}** ({item['ile']} pal.)\n→ {item['termin'].strftime('%d.%m')}")
        if c_d.button("❌", key=f"d_{i}"):
            st.session_state.kolejka.pop(i)
            st.rerun()
    
    if st.button("🗑️ WYCZYŚĆ WSZYSTKO", use_container_width=True):
        st.session_state.kolejka = []
        st.rerun()

# Okno dodawania (Simulated Dialog)
if st.session_state.get('open_dialog'):
    with st.expander("Wprowadź nowe dane", expanded=True):
        cols = st.columns(2)
        nowe = []
        for i, art_id in enumerate(WYDAJNOSC.keys()):
            with cols[i % 2]:
                n = st.number_input(f"Art {art_id}", min_value=0, step=1, key=f"inp_{art_id}")
                if n > 0: nowe.append({"art": art_id, "ile": n})
        dt = st.date_input("Data wysyłki:", datetime.date.today() + datetime.timedelta(days=4))
        if st.button("ZAPISZ"):
            for item in nowe:
                st.session_state.kolejka.append({"art": item["art"], "ile": item["ile"], "termin": dt})
            st.session_state.open_dialog = False
            st.rerun()

# --- WIDOK GŁÓWNY ---
if st.session_state.kolejka:
    k_tuple = tuple(tuple(d.items()) for d in st.session_state.kolejka)
    dni, raport, zbiorcza = generuj_harmonogram_jit(k_tuple, datetime.date.today())
    
    # 1. TABELA ZBIORCZA (Wysyłki)
    st.subheader("📊 PODSUMOWANIE WYSYŁEK (Ile palet na jaki dzień)")
    st.dataframe(zbiorcza, use_container_width=True)

    # 2. KAFELKI PRODUKCJI
    st.subheader("🗓️ HARMONOGRAM PRODUKCJI (Kiedy co robić)")
    siatka = st.columns(5)
    for i, d_key in enumerate(sorted(dni.keys(), key=lambda x: datetime.datetime.strptime(x, "%d.%m"))):
        with siatka[i % 5]:
            info = dni[d_key]
            st.markdown(f"""
                <div style="border:1px solid #ddd; border-radius:10px; padding:8px; background-color:#f8f9fa;">
                    <b style="color:#1f77b4;">{d_key} ({info['dzien']})</b><br>
                    <span style="color:green; font-weight:bold;">Łącznie: {info['suma']} pal.</span><hr style="margin:4px 0;">
            """, unsafe_allow_html=True)
            for p in info["p"]:
                st.write(f"**{p['Artykuł']}**: {p['Palety']} pal. (do: {p['Data Wysyłki']})")
            st.markdown("</div>", unsafe_allow_html=True)

    # 3. RAPORT DO DRUKU
    st.divider()
    st.subheader("🖨️ LISTA PRODUKCYJNA (Widok do druku)")
    df_rep = pd.DataFrame(raport)[["Data Produkcji", "Dzień", "Artykuł", "Palety", "Data Wysyłki"]]
    st.table(df_rep)
    
    st.caption("Wskazówka: Naciśnij Ctrl + P, aby wydrukować powyższą listę.")
else:
    st.info("Dodaj zamówienie w panelu bocznym.")
