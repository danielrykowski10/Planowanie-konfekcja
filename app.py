import streamlit as st
import datetime
import pandas as pd
import json
import os

# --- KONFIGURACJA ---
PLIK_DANYCH = "dane_zamowien.json"
st.set_page_config(page_title="Konfekcja SM - System Planowania", layout="wide")

# Stylizacja
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
DNI_PL = {"Monday": "Poniedziałek", "Tuesday": "Wtorek", "Wednesday": "Środa", "Thursday": "Czwartek", "Friday": "Piątek", "Saturday": "Sobota", "Sunday": "Niedziela"}
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
            is_nad = False
            if data_k == z['termin'] and ile > produkcja:
                produkcja = ile
                is_nad = True

            if produkcja > 0:
                # OBLICZANIE DATY PRZYDATNOŚCI (Data produkcji + 80 dni)
                przydatnosc = data_k + datetime.timedelta(days=80)
                
                raport.append({
                    "Data": data_k.strftime("%d.%m"), 
                    "Dzień": DNI_PL.get(data_k.strftime("%A")), 
                    "Art": z["art"], 
                    "Palety": int(produkcja), 
                    "Kraj": z["kraj"], 
                    "Wysyłka": z["termin"].strftime("%d.%m"), 
                    "Przydatność": przydatnosc.strftime("%d.%m.%y"),
                    "dt_s": data_k, 
                    "nad": is_nad
                })
                ile -= produkcja
                plan_dni[d_key] -= (produkcja * wyd)
                if ile > 0: plan_dni[d_key] = 0
            if ile > 0: data_k += datetime.timedelta(days=1)
            
    widok = {}
    raport_sorted = sorted(raport, key=lambda x: x['dt_s'])
    for r in raport_sorted:
        dk = r['Data']
        if dk not in widok: 
            widok[dk] = {"dz": r['Dzień'], "p": [], "suma": 0, "czas_suma": 0, "ma_nad": False}
        widok[dk]["p"].append(r)
        widok[dk]["suma"] += r["Palety"]
        widok[dk]["czas_suma"] += r["Palety"] * WYDAJNOSC.get(r["Art"], 70)
        if r["nad"]: widok[dk]["ma_nad"] = True
        
    return widok, raport_sorted

# --- START ---
if 'kolejka' not in st.session_state:
    st.session_state.kolejka = wczytaj_dane()

tab1, tab2 = st.tabs(["📥 WPISYWANIE ZAMÓWIEŃ", "📋 GOTOWY HARMONOGRAM NA HALĘ"])

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
        for i, art_id in enumerate(WYDAJNOSC.keys()):
            with cols_art[i % 5]:
                val = st.number_input(f"Art {art_id}", min_value=0, step=1)
                if val > 0: temp_list.append({"art": art_id, "ile": val, "termin": f_wysylka, "start_produkcji": f_start, "kraj": f_kraj})
        if st.form_submit_button("ZAPISZ ZAMÓWIENIA", use_container_width=True):
            st.session_state.kolejka.extend(temp_list)
            zapisz_dane(st.session_state.kolejka)
            st.rerun()

    st.divider()
    if st.session_state.kolejka:
        df_edit = pd.DataFrame(st.session_state.kolejka)
        st.dataframe(df_edit[['kraj', 'art', 'ile', 'start_produkcji', 'termin']].style.apply(lambda r: ['background-color: #C8E6C9' if r.kraj == 'Słowacja' else ''] * len(r), axis=1), use_container_width=True, hide_index=True)
        if st.button("USUŃ WSZYSTKIE ZAMÓWIENIA"):
            st.session_state.kolejka = []
            zapisz_dane([])
            st.rerun()

with tab2:
    st.subheader("Harmonogram Produkcji (Rozpiska na halę)")
    if st.session_state.kolejka:
        dni_plan, raport_raw = generuj_plan_finalny(st.session_state.kolejka)
        dni_posortowane = sorted(dni_plan.keys(), key=lambda x: datetime.datetime.strptime(x, "%d.%m"))
        grid = st.columns(5)
        
        for i, dk in enumerate(dni_posortowane):
            with grid[i % 5]:
                d_info = dni_plan[dk]
                
                is_nad = d_info["ma_nad"] or d_info["czas_suma"] > 840
                if d_info["czas_suma"] <= 420:
                    zmiany_txt = "⏱️ 1 zmiana"
                    godziny = "06:00 - 15:00" if is_nad else "06:00 - 14:00"
                else:
                    zmiany_txt = "⏱️ 2 zmiany"
                    godziny = "06:00-15:00, 15:00-23:00" if is_nad else "06:00-14:00, 14:00-22:00"
                
                color_header = "#E65100" if is_nad else "#1B5E20"
                bg_header = "#FFF3E0" if is_nad else "#F1F8E9"

                karta_html = f'<div class="karta-dnia" style="border-color: {color_header};">'
                karta_html += f'<div style="font-size: 18px; font-weight: bold; color: {color_header}; border-bottom: 2px solid #EEE; margin-bottom: 5px;">{dk} ({d_info["dz"]})</div>'
                karta_html += f'<div style="background-color: {bg_header}; padding: 5px; border-radius: 5px; margin-bottom: 10px;">'
                karta_html += f'<span style="font-size: 14px; font-weight: bold; color: #000;">SUMA: {int(d_info["suma"])} palet</span><br>'
                karta_html += f'<span style="font-size: 13px; font-weight: bold; color: #FF0000;">{zmiany_txt} ({godziny})</span>'
                karta_html += '</div>'
                
                for p in d_info['p']:
                    is_sk = p['Kraj'] == "Słowacja"
                    bg = "#A5D6A7" if is_sk else "#F1F1F1"
                    brd = "#2E7D32" if is_sk else "#CCC"
                    
                    karta_html += f'<div style="background-color: {bg}; border: 1px solid {brd}; border-radius: 6px; padding: 6px; margin-bottom: 6px; font-size: 12px; color: #000;">'
                    karta_html += f'Art {p["Art"]} — <b style="font-size: 13px; color: #000;">{int(p["Palety"])} pal.</b><br>'
                    karta_html += f'<span style="font-size: 11px; color: #000;">Wysyłka: {p["Wysyłka"]} ({p["Kraj"]})</span><br>'
                    # DODANA DATA PRZYDATNOŚCI
                    karta_html += f'<span style="font-size: 11px; font-weight: bold; color: #000;">Przydatność: {p["Przydatność"]}</span>'
                    karta_html += f'</div>'
                
                karta_html += '</div>'
                st.markdown(karta_html, unsafe_allow_html=True)

        st.divider()
        st.subheader("Lista zbiorcza")
        df_final = pd.DataFrame(raport_raw)
        if not df_final.empty:
            st.dataframe(df_final[['Data', 'Dzień', 'Art', 'Palety', 'Kraj', 'Wysyłka', 'Przydatność']].style.apply(lambda r: ['background-color: #C8E6C9' if r.Kraj == 'Słowacja' else ''] * len(r), axis=1), use_container_width=True, hide_index=True)
