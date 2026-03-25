import streamlit as st
import datetime
import pandas as pd
import json
import os

# --- KONFIGURACJA ---
PLIK_DANYCH = "dane_zamowien.json"
st.set_page_config(page_title="Konfekcja SM - System Planowania", layout="wide")

# Stylizacja - USUNIĘTO min-height, dodano automatyczne dopasowanie
st.markdown("""
    <style>
    .main { background-color: #F8F9FA; }
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #f1f1f1;
        border-radius: 8px 8px 0px 0px;
        padding: 10px 20px;
        font-weight: bold;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2E7D32 !important;
        color: white !important;
    }
    .karta-dnia {
        border: 2px solid #2E7D32; 
        border-radius: 12px; 
        padding: 12px; 
        background-color: white; 
        margin-bottom: 20px;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.1);
        /* Karta dopasowuje się do zawartości */
        height: auto; 
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

# --- PARAMETRY ---
DNI_PL = {"Monday": "Pon", "Tuesday": "Wt", "Wednesday": "Śr", "Thursday": "Czw", "Friday": "Pt", "Saturday": "Sob", "Sunday": "Nd"}
WYDAJNOSC = {"232": 84, "233": 56, "236": 84, "261": 84, "246": 84, "254": 52.5, "1221217": 120, "1221070": 52.5, "1221181": 210}

# --- LOGIKA PLANOWANIA ---
def generuj_plan_finalny(kolejka):
    if not kolejka: return {}, []
    zadania = [dict(z) for z in kolejka]
    plan_dni, raport, MAX_CZAS = {}, [], 840
    data_dzis = datetime.date.today()
    zadania.sort(key=lambda x: (x['termin'], x['art']))

    for z in zadania:
        ile = int(z['ile'])
        wyd = WYDAJNOSC.get(z["art"], 70)
        data_k = max(data_dzis, z['start_produkcji'])
        while ile > 0:
            if data_k.weekday() == 6: 
                data_k += datetime.timedelta(days=1); continue
            d_key = data_k.strftime("%Y-%m-%d")
            if d_key not in plan_dni: plan_dni[d_key] = MAX_CZAS
            wolny_czas = plan_dni[d_key]
            if data_k == z['termin']:
                zajete_juz = MAX_CZAS - wolny_czas
                dostepny = max(0, 420 - zajete_juz)
            else: dostepny = wolny_czas
            produkcja = min(dostepny // wyd, ile)
            if produkcja > 0:
                raport.append({"Data": data_k.strftime("%d.%m"), "Dzień": DNI_PL.get(data_k.strftime("%A")), "Art": z["art"], "Palety": int(produkcja), "Kraj": z["kraj"], "Wysyłka": z["termin"].strftime("%d.%m"), "dt_s": data_k})
                ile -= produkcja
                plan_dni[d_key] -= (produkcja * wyd)
                if ile > 0: plan_dni[d_key] = 0
            if ile > 0: data_k += datetime.timedelta(days=1)
    widok = {}
    raport_sorted = sorted(raport, key=lambda x: x['dt_s'])
    for r in raport_sorted:
        dk = r['Data']
        if dk not in widok: widok[dk] = {"dz": r['Dzień'], "p": [], "suma": 0}
        widok[dk]["p"].append(r); widok[dk]["suma"] += r["Palety"]
    return widok, raport_sorted

# --- START ---
if 'kolejka' not in st.session_state:
    st.session_state.kolejka = wczytaj_dane()

tab1, tab2 = st.tabs(["📥 WPISYWANIE ZAMÓWIEŃ", "📋 GOTOWY HARMONOGRAM NA HALĘ"])

# --- OKIENKO 1: WPISYWANIE ---
with tab1:
    st.subheader("Nowe Zamówienia")
    with st.form("fm_nowe", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        f_kraj = c1.selectbox("Kierunek", ["Czechy", "Słowacja"])
        f_start = c2.date_input("Kiedy można zacząć?", datetime.date.today())
        f_wysylka = c3.date_input("Termin wyjazdu auta:", datetime.date.today() + datetime.timedelta(days=3))
        
        st.write("Wpisz ilość palet:")
        cols_art = st.columns(5)
        temp_list = []
        for i, (art_id, wyd) in enumerate(WYDAJNOSC.items()):
            with cols_art[i % 5]:
                val = st.number_input(f"Art {art_id}", min_value=0, step=1)
                if val > 0:
                    temp_list.append({"art": art_id, "ile": val, "termin": f_wysylka, "start_produkcji": f_start, "kraj": f_kraj})
        
        if st.form_submit_button("ZAPISZ ZAMÓWIENIA", use_container_width=True):
            st.session_state.kolejka.extend(temp_list)
            zapisz_dane(st.session_state.kolejka)
            st.rerun()

    st.divider()
    st.subheader("Aktualna lista w kolejce")
    if st.session_state.kolejka:
        df_edit = pd.DataFrame(st.session_state.kolejka)
        def style_kolejka(row):
            kolor = 'background-color: #C8E6C9' if row.kraj == 'Słowacja' else ''
            return [kolor] * len(row)
        st.dataframe(df_edit[['kraj', 'art', 'ile', 'start_produkcji', 'termin']].style.apply(style_kolejka, axis=1), use_container_width=True, hide_index=True)
        if st.button("USUŃ WSZYSTKIE ZAMÓWIENIA"):
            st.session_state.kolejka = []
            zapisz_dane([])
            st.rerun()
    else:
        st.info("Brak zamówień.")

# --- OKIENKO 2: HARMONOGRAM NA GOTOWO ---
with tab2:
    st.subheader("Harmonogram Produkcji (Rozpiska na halę)")
    if st.session_state.kolejka:
        dni_plan, raport_raw = generuj_plan_finalny(st.session_state.kolejka)
        if not dni_plan:
            st.warning("Brak planu do wyświetlenia.")
        else:
            dni_posortowane = sorted(dni_plan.keys(), key=lambda x: datetime.datetime.strptime(x, "%d.%m"))
            
            grid = st.columns(5)
            for i, dk in enumerate(dni_posortowane):
                with grid[i % 5]:
                    d_info = dni_plan[dk]
                    
                    karta_html = f'<div class="karta-dnia">'
                    karta_html += f'<div style="font-size: 18px; font-weight: bold; color: #1B5E20; border-bottom: 2px solid #EEE; margin-bottom: 8px;">{dk} ({d_info["dz"]})</div>'
                    karta_html += f'<div style="font-size: 14px; color: #2E7D32; font-weight: bold; margin-bottom: 12px;">SUMA: {int(d_info["suma"])} palet</div>'
                    
                    for p in d_info['p']:
                        is_sk = p['Kraj'] == "Słowacja"
                        bg = "#A5D6A7" if is_sk else "#F1F1F1"
                        brd = "#2E7D32" if is_sk else "#CCC"
                        fnt = "#1B5E20" if is_sk else "#333"
                        
                        karta_html += f'<div style="background-color: {bg}; border: 1px solid {brd}; border-radius: 6px; padding: 6px; margin-bottom: 6px; font-size: 12px; color: {fnt};">'
                        karta_html += f'<b>Art {p["Art"]}</b> — <b>{int(p["Palety"])} pal.</b><br>'
                        karta_html += f'<span style="font-size: 11px; opacity: 0.8;">Wysyłka: {p["Wysyłka"]} ({p["Kraj"]})</span>'
                        karta_html += f'</div>'
                    
                    karta_html += '</div>'
                    st.markdown(karta_html, unsafe_allow_html=True)

            st.divider()
            st.subheader("Lista zbiorcza")
            df_final = pd.DataFrame(raport_raw)
            if not df_final.empty:
                def color_rows(row):
                    return ['background-color: #C8E6C9' if row.Kraj == 'Słowacja' else ''] * len(row)
                st.dataframe(df_final[['Data', 'Dzień', 'Art', 'Palety', 'Kraj', 'Wysyłka']].style.apply(color_rows, axis=1), use_container_width=True, hide_index=True)
    else:
        st.warning("Najpierw wpisz zamówienia.")
        
