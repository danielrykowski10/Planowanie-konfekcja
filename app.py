import streamlit as st
import datetime
import pandas as pd
import json
import os

# --- KONFIGURACJA ---
PLIK_DANYCH = "dane_zamowien.json"
st.set_page_config(page_title="Konfekcja SM - System Planowania", layout="wide")

# Stylizacja luksusowa/industrialna
st.markdown("""
    <style>
    .main { background-color: #FDFBF7; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f1f1f1;
        border-radius: 10px 10px 0px 0px;
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1f77b4 !important;
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- FUNKCJE DANYCH ---
def wczytaj_dane():
    if os.path.exists(PLIK_DANYCH):
        try:
            with open(PLIK_DANYCH, "r", encoding="utf-8") as f:
                dane = json.load(f)
                for z in dane:
                    z['termin'] = datetime.datetime.strptime(z['termin'], "%Y-%m-%d").date()
                    z['start_produkcji'] = datetime.datetime.strptime(z.get('start_produkcji', datetime.date.today().strftime("%Y-%m-%d")), "%Y-%m-%d").date()
                return dane
        except: return []
    return []

def zapisz_dane(kolejka):
    kolejka_do_zapisu = []
    for z in kolejka:
        z_kopia = z.copy()
        z_kopia['termin'] = z_kopia['termin'].strftime("%Y-%m-%d")
        z_kopia['start_produkcji'] = z_kopia['start_produkcji'].strftime("%Y-%m-%d")
        kolejka_do_zapisu.append(z_kopia)
    with open(PLIK_DANYCH, "w", encoding="utf-8") as f:
        json.dump(kolejka_do_zapisu, f, ensure_ascii=False, indent=4)

# --- LOGIKA PLANOWANIA ---
DNI_PL = {"Monday": "Pon", "Tuesday": "Wt", "Wednesday": "Śr", "Thursday": "Czw", "Friday": "Pt", "Saturday": "Sob", "Sunday": "Nd"}
WYDAJNOSC = {"232": 84, "233": 56, "236": 84, "261": 84, "246": 84, "254": 52.5, "1221217": 120, "1221070": 52.5, "1221181": 210}

@st.cache_data
def generuj_plan_finalny(kolejka_tuple, data_globalna):
    if not kolejka_tuple: return {}, []
    zadania = [dict(z) for z in kolejka_tuple]
    plan_dni, raport, MAX_CZAS = {}, [], 840
    ostatni_art = None

    while zadania:
        zadania.sort(key=lambda x: (x['termin'], x['art']))
        z = zadania.pop(0) # Prio: najkrótszy termin
        ile, wyd = z['ile'], WYDAJNOSC.get(z["art"], 70)
        data_k = max(data_globalna, z['start_produkcji'])
        
        while ile > 0:
            if data_k.weekday() == 6: data_k += datetime.timedelta(days=1); continue
            d_key = data_k.strftime("%Y-%m-%d")
            if d_key not in plan_dni: plan_dni[d_key] = MAX_CZAS
            
            dostepny = plan_dni[d_key] if data_k != z['termin'] else max(0, 420 - (MAX_CZAS - plan_dni[d_key]))
            produkcja = min(dostepny // wyd, ile)
            
            if produkcja > 0:
                raport.append({"Data": data_k.strftime("%d.%m"), "Dzień": DNI_PL.get(data_k.strftime("%A")), "Art": z["art"], "Palety": int(produkcja), "Kraj": z["kraj"], "Wysyłka": z["termin"].strftime("%d.%m"), "dt_s": data_k})
                ile -= produkcja
                plan_dni[d_key] -= (produkcja * wyd)
                if ile > 0: plan_dni[d_key] = 0 # Blokada maszyny do końca dnia
            if ile > 0: data_k += datetime.timedelta(days=1)

    # Grupowanie pod widok
    widok = {}
    for r in sorted(raport, key=lambda x: x['dt_s']):
        dk = r['Data']
        if dk not in widok: widok[dk] = {"dz": r['Dzień'], "p": [], "suma": 0}
        widok[dk]["p"].append(r); widok[dk]["suma"] += r["Palety"]
    return widok, raport

# --- START APLIKACJI ---
if 'kolejka' not in st.session_state:
    st.session_state.kolejka = wczytaj_dane()

# NAWIGACJA GÓRNA (OKIENKA)
tab1, tab2 = st.tabs(["📥 WPISYWANIE ZAMÓWIEŃ", "🗓️ GOTOWY HARMONOGRAM PRODUKCJI"])

# --- OKIENKO 1: DODAWANIE ---
with tab1:
    st.subheader("Dodaj nowe zamówienia do bazy")
    with st.form("fm_nowe", clear_on_submit=True):
        col_a, col_b, col_c = st.columns(3)
        f_kraj = col_a.selectbox("Kierunek", ["Czechy", "Słowacja"])
        f_start = col_b.date_input("Można produkować od:", datetime.date.today())
        f_wysylka = col_c.date_input("Termin wyjazdu:", datetime.date.today() + datetime.timedelta(days=3))
        
        st.write("Wpisz ilości palet:")
        cols_art = st.columns(5)
        nowe_paczka = []
        for i, art_id in enumerate(WYDAJNOSC.keys()):
            with cols_art[i % 5]:
                v = st.number_input(f"Art {art_id}", min_value=0, step=1)
                if v > 0:
                    nowe_paczka.append({"art": art_id, "ile": v, "termin": f_wysylka, "start_produkcji": f_start, "kraj": f_kraj})
        
        if st.form_submit_button("ZAPISZ I DODAJ DO KOLEJKI", use_container_width=True):
            st.session_state.kolejka.extend(nowe_paczka)
            zapisz_dane(st.session_state.kolejka)
            st.success(f"Dodano {len(nowe_paczka)} artykułów.")
            st.rerun()

    st.divider()
    st.subheader("Aktualna lista w kolejce (do zaplanowania)")
    if st.session_state.kolejka:
        df_list = pd.DataFrame(st.session_state.kolejka)
        st.dataframe(df_list, use_container_width=True)
        if st.button("WYCZYŚĆ CAŁĄ KOLEJKĘ"):
            st.session_state.kolejka = []
            zapisz_dane([])
            st.rerun()
    else:
        st.info("Kolejka jest pusta.")

# --- OKIENKO 2: GOTOWY HARMONOGRAM ---
with tab2:
    st.subheader("Rozpiska porcjowania na gotowo")
    c1, c2 = st.columns([1, 3])
    data_g = c1.date_input("Dzień startu maszyn:", datetime.date.today())
    
    if st.session_state.kolejka:
        # Konwersja do tuple dla cache
        k_tuple = tuple(tuple(sorted(d.items())) for d in st.session_state.kolejka)
        dni_plan, raport_raw = generuj_plan_finalny(k_tuple, data_g)

        # WIDOK KAFELKOWY (NA GOTOWO)
        st.markdown("---")
        kafelki = st.columns(5)
        for i, dk in enumerate(dni_plan.keys()):
            with kafelki[i % 5]:
                d_info = dni_plan[dk]
                
                # Karta dnia
                html_karta = f"""
                <div style="border: 2px solid #1f77b4; border-radius: 12px; padding: 15px; background-color: white; min-height: 350px; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);">
                    <div style="font-size: 20px; font-weight: bold; color: #1f77b4; border-bottom: 2px solid #eee; margin-bottom: 10px;">{dk} ({d_info['dz']})</div>
                    <div style="font-size: 14px; color: #28a745; font-weight: bold; margin-bottom: 15px;">Suma: {d_info['suma']} palet</div>
                """
                
                for p in d_info['p']:
                    # Kolorystyka Słowacji (bardziej zielona)
                    is_sk = p['Kraj'] == "Słowacja"
                    bg_col = "#c8e6c9" if is_sk else "#f8f9fa"
                    border_col = "#2e7d32" if is_sk else "#ccc"
                    
                    html_karta += f"""
                    <div style="background-color: {bg_col}; border: 1px solid {border_col}; border-radius: 6px; padding: 8px; margin-bottom: 8px; font-size: 13px;">
                        <b>Art {p['Art']}</b>: {p['Palety']} pal.<br>
                        <span style="font-size: 11px; color: #666;">Wysyłka: {p['Wysyłka']} ({p['Kraj']})</span>
                    </div>
                    """
                
                html_karta += "</div>"
                st.markdown(html_karta, unsafe_allow_html=True)

        st.divider()
        st.subheader("Podsumowanie zbiorcze (Kontrola)")
        if raport_raw:
            df_rep = pd.DataFrame(raport_raw)
            # Podświetlenie Słowacji w tabeli
            def style_sk(row):
                return ['background-color: #a5d6a7' if row.Kraj == 'Słowacja' else ''] * len(row)
            st.dataframe(df_rep.style.apply(style_sk, axis=1), use_container_width=True, hide_index=True)
            
    else:
        st.warning("Najpierw dodaj zamówienia w pierwszym okienku!")
