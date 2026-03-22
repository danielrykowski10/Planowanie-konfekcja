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

st.set_page_config(page_title="SM Mazowsze - Pro", layout="wide")

if 'kolejka' not in st.session_state:
    st.session_state.kolejka = []

# --- LOGIKA PLANOWANIA JIT ---
@st.cache_data
def generuj_plan_jit(kolejka_tuple, data_dzis):
    if not kolejka_tuple: return {}, []

    zadania = [dict(z) for z in kolejka_tuple]
    # Planujemy od najpóźniejszych wysyłek wstecz
    zadania = sorted(zadania, key=lambda x: x['termin'], reverse=True)
    
    plan_dni = {}
    raport = []
    CZAS_NETTO = 840 # 2 zmiany
    
    for z in zadania:
        ile = z['ile']
        wyd = WYDAJNOSC.get(z["art"], 70)
        data_planu = z['termin'] - datetime.timedelta(days=1)
        
        while ile > 0:
            if data_planu < data_dzis: data_planu = data_dzis
            
            d_key = data_planu.strftime("%Y-%m-%d")
            if d_key not in plan_dni: plan_dni[d_key] = CZAS_NETTO
            
            wolny_czas = plan_dni[d_key]
            if wolny_czas >= wyd:
                produkcja = min(wolny_czas // wyd, ile)
                if produkcja > 0:
                    raport.append({
                        "Data": data_planu.strftime("%d.%m"),
                        "Art": z["art"],
                        "Palety": int(produkcja),
                        "Kraj": z.get("kraj", "Czechy"),
                        "Wysyłka": z["termin"].strftime("%d.%m"),
                        "dt_sort": data_planu,
                        "oryg_termin": z['termin']
                    })
                    ile -= produkcja
                    plan_dni[d_key] -= (produkcja * wyd)
            
            if ile > 0:
                if data_planu == data_dzis: break
                data_planu -= datetime.timedelta(days=1)
                if data_planu.weekday() == 6: data_planu -= datetime.timedelta(days=1)
            else:
                break

    widok = {}
    raport_posortowany = sorted(raport, key=lambda x: x['dt_sort'])
    for r in raport_posortowany:
        dk = r['Data']
        if dk not in widok: widok[dk] = {"dz": DNI_PL.get(r['dt_sort'].strftime("%A")), "suma": 0, "p": []}
        widok[dk]["p"].append(r)
        widok[dk]["suma"] += r["Palety"]
    return widok, raport

# --- PANEL BOCZNY ---
with st.sidebar:
    st.header("⚙️ Zarządzanie")
    if st.button("➕ DODAJ NOWE ZAMÓWIENIE", type="primary", use_container_width=True): 
        st.session_state.pokaz_f = True
    
    if st.button("🗑️ WYCZYŚĆ WSZYSTKO", use_container_width=True):
        st.session_state.kolejka = []
        st.cache_data.clear()
        st.rerun()

    if st.session_state.kolejka:
        st.divider()
        st.subheader("✏️ Edycja zamówień")
        
        # Grupowanie unikalnych dat wysyłki
        unikalne_daty = sorted(list(set([z['termin'] for z in st.session_state.kolejka])))
        
        for d in unikalne_daty:
            with st.expander(f"📅 Wysyłka: {d.strftime('%d.%m')}"):
                for kraj in ["Czechy", "Słowacja"]:
                    st.markdown(f"**{kraj}**")
                    # Filtrowanie artykułów dla danej daty i kraju
                    for i, z in enumerate(st.session_state.kolejka):
                        if z['termin'] == d and z['kraj'] == kraj:
                            c1, c2 = st.columns([3, 1])
                            nowa_il = c1.number_input(f"Art {z['art']}", value=int(z['ile']), key=f"ed_{i}")
                            if c2.button("❌", key=f"del_{i}"):
                                st.session_state.kolejka.pop(i)
                                st.rerun()
                            if nowa_il != z['ile']:
                                st.session_state.kolejka[i]['ile'] = nowa_il
                                st.rerun()

# --- FORMULARZ DODAWANIA ---
if st.session_state.get('pokaz_f'):
    with st.form("quick_add"):
        st.subheader("Nowe zamówienie")
        c1, c2 = st.columns(2)
        kraj_n = c1.selectbox("Kierunek:", ["Czechy", "Słowacja"])
        term_n = c2.date_input("Termin wysyłki:", datetime.date.today() + datetime.timedelta(days=3))
        cols = st.columns(3)
        nowe_partie = []
        for i, art_id in enumerate(WYDAJNOSC.keys()):
            with cols[i % 3]:
                v = st.number_input(f"Art {art_id}", min_value=0, step=1, key=f"add_{art_id}")
                if v > 0: nowe_partie.append({"art": art_id, "ile": v, "termin": term_n, "kraj": kraj_n})
        if st.form_submit_button("ZATWIERDŹ"):
            st.session_state.kolejka.extend(nowe_partie)
            st.session_state.pokaz_f = False
            st.rerun()

# --- WIDOK GŁÓWNY ---
st.title("🥛 Planista Produkcji JIT")

if st.session_state.kolejka:
    k_tuple = tuple(tuple(d.items()) for d in st.session_state.kolejka)
    dni, raport_surowy = generuj_plan_jit(k_tuple, datetime.date.today())

    # 1. HARMONOGRAM
    grid = st.columns(5)
    sorted_keys = sorted(dni.keys(), key=lambda x: datetime.datetime.strptime(x, "%d.%m"))
    for i, dk in enumerate(sorted_keys):
        with grid[i % 5]:
            inf = dni[dk]
            st.markdown(f"""<div style="border:1px solid #ddd; border-radius:10px; padding:10px; background-color:white; margin-bottom:10px;">
                <b style="color:#1f77b4;">{dk} ({inf['dz']})</b><br>
                <b style="color:green;">Łącznie: {inf['suma']} pal.</b><hr style="margin:5px 0;">""", unsafe_allow_html=True)
            for p in inf["p"]:
                bg = "#d4edda" if p["Kraj"] == "Słowacja" else "#f8f9fa"
                st.markdown(f"""<div style="background-color:{bg}; padding:5px; border-radius:5px; margin-bottom:4px; border:1px solid #eee; font-size:12px;">
                    <b>{p['Art']}</b>: {p['Palety']} pal.<br><small>Wysyłka: {p['Wysyłka']} ({p['Kraj']})</small>
                </div>""", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # 2. ZESTAWIENIE KONTROLNE (NA DOLE)
    st.divider()
    st.subheader("🔍 Kontrola zgodności zamówień")
    
    # Przygotowanie danych do tabeli porównawczej
    df_zamowione = pd.DataFrame(st.session_state.kolejka)
    df_zamowione['Wysyłka'] = df_zamowione['termin'].apply(lambda x: x.strftime("%d.%m"))
    suma_zamowiona = df_zamowione.groupby(['Wysyłka', 'kraj', 'art'])['ile'].sum().reset_index()
    
    df_rozpisane = pd.DataFrame(raport_surowy)
    suma_rozpisana = df_rozpisane.groupby(['Wysyłka', 'Kraj', 'Art'])['Palety'].sum().reset_index()
    
    # Łączenie tabel
    porownanie = pd.merge(
        suma_zamowiona, 
        suma_rozpisana, 
        left_on=['Wysyłka', 'kraj', 'art'], 
        right_on=['Wysyłka', 'Kraj', 'Art'], 
        how='left'
    ).fillna(0)
    
    porownanie = porownanie[['Wysyłka', 'kraj', 'art', 'ile', 'Palety']]
    porownanie.columns = ['Data Wysyłki', 'Kraj', 'Artykuł', 'Zamówiono (pal)', 'Rozpisano w planie (pal)']
    
    # Dodanie statusu
    def sprawdz_zgodnosc(row):
        return "✅ OK" if row['Zamówiono (pal)'] == row['Rozpisano w planie (pal)'] else "❌ BŁĄD"
    
    porownanie['Status'] = porownanie.apply(sprawdz_zgodnosc, axis=1)
    
    st.table(porownanie)

else:
    st.info("Brak zamówień. Dodaj je w panelu bocznym.")
