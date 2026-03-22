import streamlit as st
import datetime
import pandas as pd

# 1. Konfiguracja i dane stałe
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

st.set_page_config(page_title="Planista JIT z Edycją", layout="wide")

if 'kolejka' not in st.session_state:
    st.session_state.kolejka = []

# --- LOGIKA JIT ---
@st.cache_data
def generuj_dane_jit(kolejka_tuple, data_dzisiejsza):
    if not kolejka_tuple:
        return {}, [], pd.DataFrame()
    
    zadania = [dict(z) for z in kolejka_tuple]
    zadania = sorted(zadania, key=lambda x: x['termin'], reverse=True)
    
    limit_minut = 840
    plan_roboczy = {} 
    wyniki_produkcji = []

    for z in zadania:
        ilosc_do_zrobienia = z['ile']
        if ilosc_do_zrobienia <= 0: continue
        
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
                        "Dzień": DNI_PL.get(data_dzisiejsza.strftime("%A")),
                        "Artykuł": z["art"],
                        "Palety": int(ilosc_do_zrobienia),
                        "Data Wysyłki": z["termin"].strftime("%d.%m") + " ⚠️ PILNE"
                    })
                break

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
    st.header("⚙️ Zarządzanie Planem")
    if st.button("➕ DODAJ NOWE ZAMÓWIENIE", type="primary", use_container_width=True):
        st.session_state.pokaz_okno = True
    
    if st.button("🗑️ WYCZYŚĆ CAŁY PLAN", use_container_width=True):
        st.session_state.kolejka = []
        st.cache_data.clear()
        st.rerun()

    st.divider()
    
    # --- SEKCE EDYCJI ---
    if st.session_state.kolejka:
        st.subheader("✏️ Edytuj rozpisane wysyłki")
        
        # Grupowanie kolejki po datach wysyłki dla łatwiejszej edycji
        daty_wysylki = sorted(list(set([z['termin'] for z in st.session_state.kolejka])))
        
        for data in daty_wysylki:
            with st.expander(f"📅 Wysyłka: {data.strftime('%d.%m')}"):
                for i, item in enumerate(st.session_state.kolejka):
                    if item['termin'] == data:
                        # Klucz unikalny dla każdego inputa
                        nowa_ilosc = st.number_input(
                            f"Art {item['art']}", 
                            min_value=0, 
                            value=int(item['ile']), 
                            key=f"edit_{i}_{item['art']}"
                        )
                        if nowa_ilosc != item['ile']:
                            st.session_state.kolejka[i]['ile'] = nowa_ilosc
                            st.cache_data.clear() # Czyścimy cache, żeby przeliczyć plan
                            if st.button("Zapisz zmiany", key=f"save_{i}"):
                                st.rerun()
                
                if st.button(f"Usuń tę datę ({data.strftime('%d.%m')})", key=f"del_date_{data}"):
                    st.session_state.kolejka = [z for z in st.session_state.kolejka if z['termin'] != data]
                    st.rerun()

# --- FORMULARZ DODAWANIA ---
if st.session_state.get('pokaz_okno'):
    with st.container():
        st.markdown("### 📝 Nowe zamówienie")
        c = st.columns(2)
        pobrane = []
        for i, art_id in enumerate(WYDAJNOSC.keys()):
            with c[i % 2]:
                val = st.number_input(f"Art {art_id}", min_value=0, step=1, key=f"new_{art_id}")
                if val > 0: pobrane.append({"art": art_id, "ile": val})
        dt_wys = st.date_input("Data wysyłki:", datetime.date.today() + datetime.timedelta(days=3))
        if st.button("ZATWIERDŹ I DODAJ DO PLANU"):
            for p in pobrane:
                st.session_state.kolejka.append({"art": p["art"], "ile": p["ile"], "termin": dt_wys})
            st.session_state.pokaz_okno = False
            st.rerun()

# --- WIDOK GŁÓWNY ---
st.title("🥛 Inteligentny Planista Produkcji JIT")

if st.session_state.kolejka:
    k_tuple = tuple(tuple(d.items()) for d in st.session_state.kolejka)
    dni, raport_surowy = generuj_dane_jit(k_tuple, datetime.date.today())
    df_full = pd.DataFrame(raport_surowy)

    # 1. HARMONOGRAM
    st.subheader("🗓️ Harmonogram Produkcji (Co robić danego dnia)")
    siatka = st.columns(5)
    for i, d_key in enumerate(sorted(dni.keys(), key=lambda x: datetime.datetime.strptime(x, "%d.%m"))):
        with siatka[i % 5]:
            info = dni[d_key]
            st.markdown(f"""
                <div style="border:1px solid #ddd; border-radius:10px; padding:8px; background-color:#fff;">
                    <b style="color:#1f77b4; font-size:16px;">{d_key} ({info['dzien']})</b><br>
                    <span style="color:#28a745; font-weight:bold;">Suma: {info['suma']} pal.</span><hr style="margin:4px 0;">
            """, unsafe_allow_html=True)
            for p in info["p"]:
                st.write(f"**{p['Artykuł']}**: {p['Palety']} pal.")
            st.markdown("</div>", unsafe_allow_html=True)

    # 2. PODSUMOWANIE WYSYŁEK
    st.divider()
    st.subheader("🚚 Szczegóły Wysyłek (Sprawdzenie zamówień)")
    df_wysylki_szczegol = df_full.groupby(["Data Wysyłki", "Artykuł"])["Palety"].sum().reset_index()
    for data in df_wysylki_szczegol["Data Wysyłki"].unique():
        suma_dnia = df_wysylki_szczegol[df_wysylki_szczegol["Data Wysyłki"] == data]["Palety"].sum()
        with st.expander(f"📅 Wysyłka: {data} — Łącznie: {suma_dnia} palet", expanded=True):
            st.table(df_wysylki_szczegol[df_wysylki_szczegol["Data Wysyłki"] == data][["Artykuł", "Palety"]])

    # 3. MIESIĘCZNE
    st.divider()
    st.subheader("📊 Statystyki Miesięczne")
    df_full["Miesiąc"] = df_full["Miesiac"].map(MIESIACE_PL)
    df_miesiac = df_full.pivot_table(index="Artykuł", columns="Miesiąc", values="Palety", aggfunc="sum", fill_value=0)
    st.dataframe(df_miesiac, use_container_width=True)

else:
    st.info("Brak danych. Skorzystaj z panelu bocznego, aby dodać zamówienia.")
