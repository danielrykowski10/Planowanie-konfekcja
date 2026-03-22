import streamlit as st
import datetime
import pandas as pd

# 1. Dane stałe i tłumaczenia
DNI_PL = {
    "Monday": "Poniedziałek", "Tuesday": "Wtorek", "Wednesday": "Środa",
    "Thursday": "Czwartek", "Friday": "Piątek", "Saturday": "Sobota", "Sunday": "Niedziela"
}

WYDAJNOSC = {
    "232": 70, "233": 60, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Konfekcja SM - Harmonogram", layout="wide")

if 'kolejka' not in st.session_state:
    st.session_state.kolejka = []

# --- NOWY SILNIK PLANOWANIA (PRIORYTET TERMINU + CIĄGŁOŚĆ PRODUKCJI) ---
@st.cache_data
def generuj_plan_priorytet_wysylki(kolejka_tuple, data_dzis):
    if not kolejka_tuple: return {}, []

    # 1. Sortujemy kolejkę: NAJPIERW NAJBLIŻSZY TERMIN WYSYŁKI
    zadania = [dict(z) for z in kolejka_tuple]
    zadania = sorted(zadania, key=lambda x: x['termin'])
    
    plan_produkcji = []
    daily_capacity = {}
    
    # Kursor planowania zaczyna od jutra (zakładając, że dziś już zaplanowane)
    # Można zmienić na data_dzis, jeśli planujecie na bieżąco.
    data_kursora = data_dzis #+ datetime.timedelta(days=1)
    
    # Realne limity czasowe (netto)
    CZAS_NETTO = 420  # 7h netto pracy na zmianę
    MAX_2_ZMIANY = 840 # 14h netto pracy (2 zmiany)
    ostatni_artykul = None

    while zadania:
        # Pomiń niedziele
        if data_kursora.weekday() == 6:
            data_kursora += datetime.timedelta(days=1)
            continue
            
        d_key = data_kursora.strftime("%Y-%m-%d")
        if d_key not in daily_capacity:
            daily_capacity[d_key] = MAX_2_ZMIANY
            
        cap = daily_capacity[d_key]
        
        if cap < 52.5: # Za mało miejsca na najszybszą paletę, idź do jutra
            data_kursora += datetime.timedelta(days=1)
            continue

        # WYBÓR ZADANIA (Priorytet terminu + unikanie przezbrojeń)
        najblizsza_wysylka = zadania[0]['termin']
        idx_wybranego = 0
        
        # Sprawdzamy czy w grupie zamówień na najbliższy termin jest ciągłość artykułu
        for i, z in enumerate(zadania):
            if z['termin'] == najblizsza_wysylka:
                if z['art'] == ostatni_artykul:
                    idx_wybranego = i
                    break
            else:
                break # Przeszukaliśmy całą grupę najpilniejszych

        z = zadania[idx_wybranego]
        wyd = WYDAJNOSC.get(z["art"], 70)
        
        ile_moze_wejsc = cap // wyd
        
        if ile_moze_wejsc > 0:
            produkcja = min(ile_moze_wejsc, z['ile'])
            
            # Sprawdzenie opóźnienia
            status_opoznienia = data_kursora > z['termin']
            
            plan_produkcji.append({
                "Data": data_kursora.strftime("%d.%m"),
                "Dzień": DNI_PL.get(data_kursora.strftime("%A")),
                "Art": z["art"],
                "Palety": int(produkcja),
                "Kraj": z.get("kraj", "Czechy"),
                "Wysyłka": z["termin"].strftime("%d.%m"),
                "dt_sort": data_kursora,
                "Opóźnione": status_opoznienia
            })
            
            z['ile'] -= produkcja
            daily_capacity[d_key] -= (produkcja * wyd)
            ostatni_artykul = z["art"]
            
            # Jeśli zadanie skończone, usuń z kolejki
            if z['ile'] <= 0:
                zadania.pop(idx_wybranego)
        else:
             # Artykuł nie mieści się dziś wcale -> następny dzień
             data_kursora += datetime.timedelta(days=1)

    # Grupowanie chronologiczne pod kafelki
    widok = {}
    plan_wynik = sorted(plan_produkcji, key=lambda x: (x['dt_sort'], x['Art']))
    for r in plan_wynik:
        dk = r['Data']
        if dk not in widok: 
            widok[dk] = {"dz": r['Dzień'], "suma": 0, "p": []}
        widok[dk]["p"].append(r)
        widok[dk]["suma"] += r["Palety"]
    return widok, plan_produkcji

# --- INTERFEJS UŻYTKOWNIKA ---
with st.sidebar:
    st.markdown("""
        <style>
            .sidebar-title { display: flex; align-items: center; gap: 10px; font-size: 24px; font-weight: bold; color: #1f77b4; }
        </style>
    """, unsafe_allow_html=True)
    st.markdown('<div class="sidebar-title">Konfekcja SM</div>', unsafe_allow_html=True)
    
    st.header("⚙️ Zarządzanie")
    if st.button("➕ DODAJ ZAMÓWIENIE", type="primary", use_container_width=True): 
        st.session_state.pokaz_f = True
    if st.button("🗑️ WYCZYŚĆ WSZYSTKO", use_container_width=True):
        st.session_state.kolejka = []
        st.cache_data.clear()
        st.rerun()

    if st.session_state.kolejka:
        st.divider()
        st.subheader("✏️ Edytuj zamówienia")
        daty = sorted(list(set([z['termin'] for z in st.session_state.kolejka])))
        for d in daty:
            with st.expander(f"📅 Wysyłka: {d.strftime('%d.%m')}"):
                for kraj in ["Czechy", "Słowacja"]:
                    st.caption(f"--- {kraj} ---")
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

if st.session_state.get('pokaz_f'):
    with st.form("quick_add", clear_on_submit=True):
        st.subheader("📝 Nowe zamówienie")
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

# --- USUNIĘTY NAPIS "Planista Produkcji JIT" ---
st.title("Konfekcja SM - Harmonogram Produkcji")

if st.session_state.kolejka:
    k_tuple = tuple(tuple(d.items()) for d in st.session_state.kolejka)
    dni, raport_surowy = generuj_plan_priorytet_wysylki(k_tuple, datetime.date.today())

    st.subheader("🗓️ Realny Plan Produkcji (Dociążanie zmian 14h netto)")
    grid = st.columns(5)
    sorted_keys = sorted(dni.keys(), key=lambda x: datetime.datetime.strptime(x, "%d.%m"))
    for i, dk in enumerate(sorted_keys):
        with grid[i % 5]:
            inf = dni[dk]
            st.markdown(f"""<div style="border:1px solid #ddd; border-radius:10px; padding:10px; background-color:white; margin-bottom:10px;">
                <b style="color:#1f77b4; font-size:15px;">{dk} ({inf['dz']})</b><br>
                <b style="color:green;">Suma: {inf['suma']} pal.</b><hr style="margin:5px 0;">""", unsafe_allow_html=True)
            for p in inf["p"]:
                bg = "#d4edda" if p["Kraj"] == "Słowacja" else "#f8f9fa"
                border_col = "#eee"
                text_col = "#000"
                if p.get('Opóźnione'):
                    bg = "#ffebee" # Czerwone tło dla opóźnień
                    border_col = "#ffcdd2"
                    text_col = "#b71c1c"
                
                st.markdown(f"""<div style="background-color:{bg}; padding:5px; border-radius:5px; margin-bottom:4px; border:1px solid {border_col}; font-size:12px; color:{text_col};">
                    <b>{p['Art']}</b>: {p['Palety']} pal.<br>
                    <small>Wysyłka: {p['Wysyłka']} ({p['Kraj']})</small>
                </div>""", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # Tabela Kontrolna
    st.divider()
    st.subheader("🔍 Kontrola zgodności zamówień")
    if raport_surowy:
        df_z = pd.DataFrame(st.session_state.kolejka)
        df_z['Data Wysyłki'] = df_z['termin'].apply(lambda x: x.strftime("%d.%m"))
        df_r = pd.DataFrame(raport_surowy)
        
        res = df_z.groupby(['Data Wysyłki', 'kraj', 'art'])['ile'].sum().reset_index()
        res_r = df_r.groupby(['Wysyłka', 'Kraj', 'Art'])['Palety'].sum().reset_index()
        
        final = pd.merge(res, res_r, left_on=['Data Wysyłki', 'kraj', 'art'], right_on=['Wysyłka', 'Kraj', 'Art'], how='left').fillna(0)
        final.columns = ['Termin Wysyłki', 'Kraj', 'Artykuł', 'Zamówiono (pal)', 'Zaplanowano (pal)']
        final['Status'] = final.apply(lambda x: "✅ OK" if x['Zamówiono (pal)'] == x['Zaplanowano (pal)'] else "❌ BŁĄD", axis=1)
        st.table(final)
    else:
        st.warning("Błąd generowania danych kontrolnych.")
else:
    st.info("Brak zamówień. Dodaj je w panelu bocznym.")
