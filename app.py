import streamlit as st
import datetime
import pandas as pd

# 1. Konfiguracja
DNI_PL = {
    "Monday": "Poniedziałek", "Tuesday": "Wtorek", "Wednesday": "Środa",
    "Thursday": "Czwartek", "Friday": "Piątek", "Saturday": "Sobota", "Sunday": "Niedziela"
}

MIESIACE_PL = {
    1: "Styczeń", 2: "Luty", 3: "Marzec", 4: "Kwiecień", 5: "Maj", 6: "Czerwiec",
    7: "Lipiec", 8: "Sierpień", 9: "Wrzesień", 10: "Październik", 11: "Listopad", 12: "Grudzień"
}

# Wydajność w minutach na paletę
WYDAJNOSC = {
    "232": 70, "233": 60, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Planista JIT 9H", layout="wide")

if 'kolejka' not in st.session_state:
    st.session_state.kolejka = []

# --- LOGIKA OPTYMALIZACJI I JIT ---
@st.cache_data
def generuj_dane_jit_z_grupowaniem(kolejka_tuple, data_dzisiejsza):
    if not kolejka_tuple:
        return {}, [], pd.DataFrame()
    
    # 1. Konwersja i Sortowanie (Najpierw termin wysyłki, potem Artykuł dla minimalizacji przejść)
    zadania = [dict(z) for z in kolejka_tuple]
    # Sortujemy po terminie (od najpóźniejszych) oraz po nazwie artykułu
    zadania = sorted(zadania, key=lambda x: (x['termin'], x['art']), reverse=True)
    
    LIMIT_MINUT = 540  # 9 GODZIN PRACY
    plan_roboczy = {} 
    wyniki_produkcji = []

    for z in zadania:
        ilosc_do_zrobienia = z['ile']
        if ilosc_do_zrobienia <= 0: continue
        
        wyd = WYDAJNOSC.get(z["art"], 70)
        # Startujemy planowanie od dnia przed wysyłką
        dzien_planowania = z['termin'] - datetime.timedelta(days=1)
        if dzien_planowania < data_dzisiejsza:
            dzien_planowania = data_dzisiejsza

        while ilosc_do_zrobienia > 0:
            d_key = dzien_planowania.strftime("%Y-%m-%d")
            if d_key not in plan_roboczy:
                plan_roboczy[d_key] = LIMIT_MINUT
            
            wolny_czas = plan_roboczy[d_key]
            
            # Jeśli mamy czas w 9-godzinnym dniu
            if wolny_czas >= wyd:
                ile_dzis = min(wolny_czas // wyd, ilosc_do_zrobienia)
                wyniki_produkcji.append({
                    "data_sort": dzien_planowania,
                    "Data Produkcji": dzien_planowania.strftime("%d.%m"),
                    "Miesiac": dzien_planowania.month,
                    "Artykuł": z["art"],
                    "Palety": int(ile_dzis),
                    "Kraj": z.get("kraj", "Czechy"),
                    "Data Wysyłki": z["termin"].strftime("%d.%m"),
                    "Typ": "Norma (9h)"
                })
                ilosc_do_zrobienia -= ile_dzis
                plan_roboczy[d_key] -= (ile_dzis * wyd)
            
            # Jeśli brakło czasu w normie 9h, a musimy to zrobić DZISIAJ
            if dzien_planowania <= data_dzisiejsza and ilosc_do_zrobienia > 0:
                wyniki_produkcji.append({
                    "data_sort": data_dzisiejsza,
                    "Data Produkcji": data_dzisiejsza.strftime("%d.%m"),
                    "Miesiac": data_dzisiejsza.month,
                    "Artykuł": z["art"],
                    "Palety": int(ilosc_do_zrobienia),
                    "Kraj": z.get("kraj", "Czechy"),
                    "Data Wysyłki": z["termin"].strftime("%d.%m") + " ⚠️ PONAD 9H",
                    "Typ": "Nadgodziny"
                })
                ilosc_do_zrobienia = 0 # Koniec zadania
            
            dzien_planowania -= datetime.timedelta(days=1)

    # Grupowanie dla kafelków (Sortowanie wyników, aby ten sam art był obok siebie)
    dni_wyswietl = {}
    raport_lista = sorted(wyniki_produkcji, key=lambda x: (x['data_sort'], x['Artykuł']))
    
    for r in raport_lista:
        d_key = r['Data Produkcji']
        if d_key not in dni_wyswietl:
            dni_wyswietl[d_key] = {"suma": 0, "p": []}
        dni_wyswietl[d_key]["p"].append(r)
        dni_wyswietl[d_key]["suma"] += r["Palety"]
    
    return dni_wyswietl, raport_lista

# --- INTERFEJS ---
st.title("🥛 Planista Produkcji JIT - Limit 9h")
st.info("System optymalizuje plan: limit 9h pracy oraz grupowanie artykułów dla mniejszej liczby przezbrojeń.")

# (Panel boczny i dodawanie - analogicznie jak wcześniej)
with st.sidebar:
    st.header("⚙️ Opcje")
    if st.button("➕ DODAJ ZAMÓWIENIE", type="primary", use_container_width=True):
        st.session_state.pokaz_okno = True
    if st.button("🗑️ CZYŚĆ PLAN", use_container_width=True):
        st.session_state.kolejka = []
        st.rerun()
    st.divider()
    # Sekcja edycji (skrócona dla czytelności kodu)
    if st.session_state.kolejka:
        st.subheader("✏️ Edytuj")
        daty = sorted(list(set([z['termin'] for z in st.session_state.kolejka])))
        for d in daty:
            with st.expander(f"Wysyłka {d.strftime('%d.%m')}"):
                if st.button("Usuń tę datę", key=f"del_{d}"):
                    st.session_state.kolejka = [z for z in st.session_state.kolejka if z['termin'] != d]
                    st.rerun()

# Okno formularza
if st.session_state.get('pokaz_okno'):
    with st.container():
        st.markdown("### Nowe zamówienie")
        c1, c2 = st.columns(2)
        kraj = c1.selectbox("Kraj:", ["Czechy", "Słowacja"])
        dt = c2.date_input("Data wysyłki:", datetime.date.today() + datetime.timedelta(days=3))
        cols = st.columns(2)
        pobrane = []
        for i, art_id in enumerate(WYDAJNOSC.keys()):
            with cols[i % 2]:
                v = st.number_input(f"Art {art_id}", min_value=0, key=f"n_{art_id}")
                if v > 0: pobrane.append({"art": art_id, "ile": v})
        if st.button("DODAJ"):
            for p in pobrane:
                st.session_state.kolejka.append({"art": p["art"], "ile": p["ile"], "termin": dt, "kraj": kraj})
            st.session_state.pokaz_okno = False
            st.rerun()

# --- WIDOK GŁÓWNY ---
if st.session_state.kolejka:
    k_tuple = tuple(tuple(d.items()) for d in st.session_state.kolejka)
    dni, raport_surowy = generuj_dane_jit_z_grupowaniem(k_tuple, datetime.date.today())
    df_full = pd.DataFrame(raport_surowy)

    # 1. Harmonogram (Kafelki)
    st.subheader("🗓️ Plan Produkcji (Dni robocze)")
    siatka = st.columns(5)
    for i, dk in enumerate(sorted(dni.keys(), key=lambda x: datetime.datetime.strptime(x, "%d.%m"))):
        with siatka[i % 5]:
            info = dni[dk]
            st.markdown(f"""<div style="border:1px solid #ddd; border-radius:10px; padding:8px; background-color:#fff;">
                <b style="color:#1f77b4;">{dk}</b><br>
                <b style="color:green;">Suma: {info['suma']} pal.</b><hr style="margin:4px 0;">""", unsafe_allow_html=True)
            for p in info["p"]:
                bg = "#d4edda" if p["Kraj"] == "Słowacja" else "transparent"
                label = "⚠️ PONAD 9H" if p["Typ"] == "Nadgodziny" else ""
                st.markdown(f"""<div style="background-color:{bg}; padding:2px; margin-bottom:2px; border-radius:4px;">
                    <b>{p['Artykuł']}</b>: {p['Palety']} pal. <span style="color:red; font-size:10px;">{label}</span>
                </div>""", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # 2. Statystyki Miesięczne (Podział)
    st.divider()
    st.subheader("📊 Łączna ilość asortymentu (Miesięcznie)")
    df_full["Miesiąc"] = df_full["Miesiac"].map(MIESIACE_PL)
    c_cz, c_sk = st.columns(2)
    with c_cz:
        st.markdown("#### 🇨🇿 CZECHY")
        df_cz = df_full[df_full["Kraj"] == "Czechy"]
        if not df_cz.empty: st.dataframe(df_cz.pivot_table(index="Artykuł", columns="Miesiąc", values="Palety", aggfunc="sum", fill_value=0), use_container_width=True)
    with c_sk:
        st.markdown("#### 🇸🇰 SŁOWACJA")
        df_sk = df_full[df_full["Kraj"] == "Słowacja"]
        if not df_sk.empty: st.dataframe(df_sk.pivot_table(index="Artykuł", columns="Miesiąc", values="Palety", aggfunc="sum", fill_value=0), use_container_width=True)

else:
    st.info("Dodaj zamówienie, aby zobaczyć zoptymalizowany plan.")
