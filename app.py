import streamlit as st
import datetime
import pandas as pd
import json
import os

# --- KONFIGURACJA ---
PLIK_DANYCH = "dane_zamowien.json"
st.set_page_config(page_title="Konfekcja SM - System Planowania", layout="wide")

# --- STYLIZACJA CSS ---
st.markdown("""
    <style>
    .main { background-color: #F8F9FA; }
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px; background-color: #f1f1f1; border-radius: 8px 8px 0px 0px;
        padding: 10px 20px; font-weight: bold;
    }
    .stTabs [aria-selected="true"] { background-color: #2E7D32 !important; color: white !important; }
    
    /* ZDJĘCIE NR 1: Ramka dla głównej karty (Kierowniku, dodałem te obramowania) */
    .karta-dnia {
        border: 2px solid #2E7D32; border-radius: 12px; padding: 15px; 
        background-color: white; margin-bottom: 20px; box-shadow: 2px 2px 8px rgba(0,0,0,0.1);
    }
    
    /* RAMKA DATY (BADGE) */
    .date-badge {
        border: 2px solid #1B5E20; background-color: #F1F8E9;
        border-radius: 10px; padding: 6px 12px; display: inline-block;
        font-weight: bold; color: #1B5E20; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);
    }
    .date-badge-nad {
        border: 2px solid #E65100; background-color: #FFF3E0;
        border-radius: 10px; padding: 6px 12px; display: inline-block;
        font-weight: bold; color: #E65100;
    }

    /* GŁOWICA SUMY */
    .glowica-info {
        padding: 10px; border-radius: 8px; margin-top: 10px; margin-bottom: 10px;
    }
    .glowica-norma { background-color: #F1F8E9; border: 1px solid #C8E6C9; }
    .glowica-nad { background-color: #FFF3E0; border: 1px solid #FFE0B2; }
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
        if isinstance(z_kopia['termin'], datetime.date): z_kopia['termin'] = z_kopia['termin'].strftime("%Y-%m-%d")
        if isinstance(z_kopia['start_produkcji'], datetime.date): z_kopia['start_produkcji'] = z_kopia['start_produkcji'].strftime("%Y-%m-%d")
        kolejka_do_zapisu.append(z_kopia)
    with open(PLIK_DANYCH, "w", encoding="utf-8") as f:
        json.dump(kolejka_do_zapisu, f, ensure_ascii=False, indent=4)

DNI_PL = {"Monday": "Poniedziałek", "Tuesday": "Wtorek", "Wednesday": "Środa", "Thursday": "Czwartek", "Friday": "Piątek", "Saturday": "Sobota", "Sunday": "Niedziela"}
WYDAJNOSC = {"232": 84, "233": 56, "236": 84, "261": 84, "246": 84, "254": 52.5, "1221217": 120, "1221070": 52.5, "1221181": 210}

def generuj_plan(kolejka, prac_niedz):
    if not kolejka: return {}, []
    zadania = [dict(z) for z in kolejka]
    plan_dni, raport, MAX_CZAS = {}, [], 840
    data_dzis = datetime.date.today()
    zadania.sort(key=lambda x: (x['termin'], x['art']))

    for idx, z in enumerate(zadania):
        ile, wyd = int(z['ile']), WYDAJNOSC.get(str(z["art"]), 70)
        data_k = max(data_dzis, z['start_produkcji'])
        while ile > 0:
            if not prac_niedz and data_k.weekday() == 6: data_k += datetime.timedelta(days=1); continue
            d_key = data_k.strftime("%Y-%m-%d")
            if d_key not in plan_dni: plan_dni[d_key] = MAX_CZAS
            wolny = plan_dni[d_key]
            dostepny = wolny if data_k != z['termin'] else max(0, 420 - (MAX_CZAS - wolny))
            prod = min(dostepny // wyd, ile)
            is_nad = False
            if data_k == z['termin'] and ile > prod: prod = ile; is_nad = True
            if prod > 0:
                przyd = data_k + datetime.timedelta(days=80)
                raport.append({"Data": data_k.strftime("%d.%m"), "Dzień": DNI_PL.get(data_k.strftime("%A")), "Art": z["art"], "Palety": int(prod), "Kraj": z["kraj"], "Wysyłka": z["termin"].strftime("%d.%m"), "Przydatność": przyd.strftime("%d.%m.%y"), "dt_s": data_k, "nad": is_nad, "orig_idx": idx})
                ile -= prod
                plan_dni[d_key] -= (prod * wyd)
                if ile > 0: plan_dni[d_key] = 0
            if ile > 0: data_k += datetime.timedelta(days=1)
    
    widok = {}
    for r in sorted(raport, key=lambda x: x['dt_s']):
        dk = r['Data']
        if dk not in widok: widok[dk] = {"dz": r['Dzień'], "p": [], "suma": 0, "czas_suma": 0, "ma_nad": False, "prz": r["Przydatność"]}
        widok[dk]["p"].append(r); widok[dk]["suma"] += r["Palety"]; widok[dk]["czas_suma"] += r["Palety"] * WYDAJNOSC.get(str(r["Art"]), 70)
        if r["nad"]: widok[dk]["ma_nad"] = True
    return widok

# --- START PROGRAMU ---
if 'kolejka' not in st.session_state: st.session_state.kolejka = wczytaj_dane()

tab1, tab2 = st.tabs(["📥 WPISYWANIE", "📋 HARMONOGRAM NA HALĘ"])

with tab1:
    with st.form("f1", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        kraj = c1.selectbox("Kierunek", ["Czechy", "Słowacja"])
        ds = c2.date_input("Start produkcji", datetime.date.today())
        dw = c3.date_input("Wysyłka", datetime.date.today() + datetime.timedelta(days=3))
        cols = st.columns(5)
        nowe = []
        for i, art_id in enumerate(WYDAJNOSC.keys()):
            with cols[i % 5]:
                v = st.number_input(f"Art {art_id}", min_value=0, step=1)
                if v > 0: nowe.append({"art": art_id, "ile": v, "termin": dw, "start_produkcji": ds, "kraj": kraj})
        if st.form_submit_button("DODAJ"):
            st.session_state.kolejka.extend(nowe); zapisz_dane(st.session_state.kolejka); st.rerun()

    # ZDJĘCIE NR 2: Słowacja na zielono w tabeli
    # Poprawiony sposób kolorowania dla st.data_editor
    if st.session_state.kolejka:
        st.subheader("Kolejka (Edytuj bezpośrednio)")
        df_edit = pd.DataFrame(st.session_state.kolejka)
        
        # Definicja stylów dla tabeli edytora (najbardziej niezawodny sposób)
        df_styled = df_edit.style.map(
            lambda x: 'background-color: #C8E6C9' if x == 'Słowacja' else '',
            subset=['kraj']
        )
        
        st.data_editor(
            df_styled, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "kraj": st.column_config.SelectColumn("Kraj", options=["Czechy", "Słowacja"], required=True)
            }
        )
        
        if st.button("USUŃ WSZYSTKO"):
            st.session_state.kolejka = []; zapisz_dane([]); st.rerun()

with tab2:
    if st.session_state.kolejka:
        dni_plan = generuj_plan(st.session_state.kolejka, True)
        grid = st.columns(5)
        for i, dk in enumerate(sorted(dni_plan.keys(), key=lambda x: datetime.datetime.strptime(x, "%d.%m"))):
            with grid[i % 5]:
                d = dni_plan[dk]
                nad = d["ma_nad"]
                c_h = "#E65100" if nad else "#1B5E20"
                bdg_cls = "date-badge-nad" if nad else "date-badge"
                glow_cls = "glowica-nad" if nad else "glowica-norma"

                # KARTA DNIA (ZDJĘCIE NR 1 - Obramowanie)
                st.markdown(f"<div class='karta-dnia' style='border-color:{c_h}'>", unsafe_allow_html=True)
                
                # BELKA NAGŁÓWKOWA
                h_col1, h_col2, h_col3 = st.columns([5, 4, 1])
                h_col1.markdown(f"<div class='{bdg_cls}'>{dk} ({d['dz']})</div>", unsafe_allow_html=True)
                h_col2.markdown(f"<div style='color:#d32f2f; font-weight:bold; font-size:14px; text-align:center; line-height:35px;'>PRZ: {d['prz']}</div>", unsafe_allow_html=True)
                if h_col3.button("❌", key=f"del_{dk}"):
                    idxs = set(p['orig_idx'] for p in d['p'])
                    st.session_state.kolejka = [z for idx, z in enumerate(st.session_state.kolejka) if idx not in idxs]
                    zapisz_dane(st.session_state.kolejka); st.rerun()

                # SUMA I ZMIANY
                zm = "2 zmiany" if d["czas_suma"] > 420 else "1 zmiana"
                godz = "06-15 / 15-23" if nad else "06-14 / 14-22"
                st.markdown(f"""
                    <div class='glowica-info {glow_cls}'>
                        <b style='font-size:15px; color:#000;'>SUMA: {int(d['suma'])} palet</b><br>
                        <b style='color:#FF0000; font-size:12px;'>{zm} ({godz})</b>
                    </div>
                """, unsafe_allow_html=True)

                # ARTYKUŁY
                for p in d['p']:
                    col = "#A5D6A7" if p['Kraj'] == "Słowacja" else "#F1F1F1"
                    st.markdown(f"""
                    <div style='background:{col}; border:1px solid #ccc; border-radius:6px; padding:6px; margin-bottom:6px; font-size:12px; color:#000;'>
                        <b>Art {p['Art']} — {int(p['Palety'])} pal.</b><br>Auto: {p['Wysyłka']}
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
