import streamlit as st
import datetime
import pandas as pd

# 1. Tłumaczenia i wydajność
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

st.set_page_config(page_title="Planista Produkcji JIT", layout="wide")

if 'kolejka' not in st.session_state:
    st.session_state.kolejka = []

# --- LOGIKA JIT ---
@st.cache_data
def generuj_dane_jit(kolejka_tuple, data_dzisiejsza):
    if not kolejka_tuple:
        return {}, [], pd.DataFrame()
    
    zadania = [dict(z) for z in kolejka_tuple]
    # Sortujemy od najpóźniejszych terminów
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
                    "Miesiac": dzien_planowania.month,
                    "Rok": dzien_planowania.year,
                    "Dzień": DNI_PL.get(dzien_planowania.strftime("%A")),
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
                        "Miesiac": data_dzisiejsza.month,
                        "Rok": data_dzisiejsza.year,
                        "Dzień": DNI_PL.get(data_dzisiejsza.strftime("%A")),
                        "Artykuł": z["art"],
                        "Palety": int(ilosc_do_zrobienia),
                        "Data Wysyłki": z["termin"].strftime("%d.%m") + " ⚠️ PILNE"
                    })
                break

    # Grupowanie do kafelków
    dni_wyswietl = {}
    raport_lista = sorted(wyniki_produkcji, key=lambda x: x['data_sort'])
    for r in raport_lista:
        d_key = r['Data Produkcji']
        if d_key not in dni_wyswietl:
            dni_wyswietl[d_key] = {"dzien": r['Dzień'], "suma": 0, "p": []}
        dni_wyswietl[d_key]["p"].append(r)
        dni_wyswietl[d_key]["suma"] += r["Palety"]
    
    return dni_wyswietl, raport_lista

# --- BOCZNY PANEL ---
with st.sidebar:
    st.header("⚙️ Zarządzanie")
    if st.button("➕ DODAJ ZAMÓWIENIE", type="primary", use_container_width=True):
        st.session_state.pokaz_okno = True
    
    st.divider()
    if st.button("🗑️ WYCZYŚĆ PLAN", use_container_width=True):
        st.session_state.kolejka = []
        st.cache_data.clear()
        st.rerun()

if st.session_state.get('pokaz_okno'):
    with st.expander("📝 Formularz", expanded=True):
        c = st.columns(2)
        pobrane = []
        for i, art_id in enumerate(WYDAJNOSC.keys()):
            with c[i % 2]:
                val = st.number_input(f"Art {art_id}", min_value=0, step=1, key=f"v_{art_id}")
                if val > 0: pobrane.append({"art": art_id, "ile": val})
        dt_wys = st.date_input("Wysyłka:", datetime.date.today() + datetime.timedelta(days=3))
        if st.button("ZAPISZ"):
            for p in pobrane:
                st.session_state.kolejka.append({"art": p["art"], "ile": p["ile"], "termin": dt_wys})
            st.session_state.pokaz_okno = False
            st.rerun()

# --- WIDOK GŁÓWNY ---
st.title("🥛 Planista Produkcji JIT")

if st.session_state.kolejka:
    k_tuple = tuple(tuple(d.items()) for d in st.session_state.kolejka)
    dni, raport_surowy = generuj_dane_jit(k_tuple, datetime.date.today())
    df_full = pd.DataFrame(raport_surowy)

    # 1. HARMONOGRAM PRODUKCJI
    st.subheader("🗓️ Harmonogram Produkcji (Kiedy robić)")
    siatka = st.columns(5)
    for i, d_key in enumerate(sorted(dni.keys(), key=lambda x: datetime.datetime.strptime(x, "%d.%m"))):
        with siatka[i % 5]:
            info = dni[d_key]
            st.markdown(f"""
                <div style="border:1px solid #ddd; border-radius:10px; padding:8px; background-color:#fff;">
                    <b style="color:#1f77b4;">{d_key} ({info['dzien']})</b><br>
                    <span style="color:#28a745; font-weight:bold;">Suma: {info['suma']} pal.</span><hr style="margin:4px 0;">
            """, unsafe_allow_html=True)
            for p in info["p"]:
                st.write(f"**{p['Artykuł']}**: {p['Palety']} pal.")
            st.markdown("</div>", unsafe_allow_html=True)

    # 2. PODSUMOWANIE WYSYŁEK (SZCZEGÓŁOWE)
    st.divider()
    st.subheader("🚚 Podsumowanie Wysyłek (Rozbicie na asortyment)")
    
    # Grupowanie po dacie wysyłki i artykule
    df_wysylki_szczegol = df_full.groupby(["Data Wysyłki", "Artykuł"])["Palety"].sum().reset_index()
    
    # Dodanie wierszy z sumą dzienną dla lepszej czytelności
    for data in df_wysylki_szczegol["Data Wysyłki"].unique():
        suma_dnia = df_wysylki_szczegol[df_wysylki_szczegol["Data Wysyłki"] == data]["Palety"].sum()
        st.write(f"📅 **Wysyłka: {data}** — Łącznie: **{suma_dnia} palet**")
        st.dataframe(df_wysylki_szczegol[df_wysylki_szczegol["Data Wysyłki"] == data][["Artykuł", "Palety"]], hide_index=True, use_container_width=True)

    # 3. PODSUMOWANIE MIESIĘCZNE
    st.divider()
    st.subheader("📊 Produkcja Miesięczna (Suma wg artykułu)")
    df_full["Nazwa Miesiąca"] = df_full["Miesiac"].map(MIESIACE_PL)
    df_miesiac = df_full.pivot_table(index="Artykuł", columns="Nazwa Miesiąca", values="Palety", aggfunc="sum", fill_value=0)
    st.dataframe(df_miesiac, use_container_width=True)

else:
    st.info("Dodaj zamówienie, aby zobaczyć plan.")
