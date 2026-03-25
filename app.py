import streamlit as st
import datetime
import pandas as pd
import json
import os

# --- KONFIGURACJA ---
PLIK_DANYCH = "dane_zamowien.json"
st.set_page_config(page_title="Konfekcja SM - System Planowania", layout="wide")

# --- LUKSUSOWA STYLIZACJA ---
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
    /* GŁÓWNA KARTA DNIA */
    .karta-dnia {
        border: 2px solid #2E7D32; 
        border-radius: 12px; 
        padding: 12px; 
        background-color: white; 
        margin-bottom: 20px;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.1);
        position: relative;
    }
    /* RAMKA DATY (BADGE) */
    .date-badge {
        border: 2px solid #1B5E20;
        background-color: #F1F8E9;
        border-radius: 10px;
        padding: 6px 12px;
        display: inline-block;
        text-align: center;
        box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);
    }
    .date-badge-nad {
        border: 2px solid #E65100;
        background-color: #FFF3E0;
        border-radius: 10px;
        padding: 6px 12px;
        display: inline-block;
        text-align: center;
        box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);
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
        if isinstance(z_kopia['termin'], datetime.date): z_kopia['termin'] = z_kopia['termin'].strftime("%Y-%m-%d")
        if isinstance(z_kopia['start_produkcji'], datetime.date): z_kopia['start_produkcji'] = z_kopia['start_produkcji'].strftime("%Y-%m-%d")
        kolejka_do_zapisu.append(z_kopia)
    with open(PLIK_DANYCH, "w", encoding="utf-8") as f:
        json.dump(kolejka_do_zapisu, f, ensure_ascii=False, indent=4)

DNI_PL = {"Monday": "Poniedziałek", "Tuesday": "Wtorek", "Wednesday": "Środa", "Thursday": "Czwartek", "Friday": "Piątek", "Saturday": "Sobota", "Sunday": "Niedziela"}
WYDAJNOSC = {"232": 84, "233": 56, "236": 84, "261": 84, "246": 84, "254": 52.5, "1221217": 120, "1221070": 52.5, "1221181": 210}

# --- LOGIKA PLANOWANIA ---
def generuj_plan_finalny(kolejka, pracujemy_niedziela):
    if not kolejka: return {}, []
    zadania = [dict(z) for z in kolejka]
    plan_dni, raport, MAX_CZAS = {}, [], 840
    data_dzis = datetime.date.today()
    zadania.sort(key=lambda x: (x['termin'], x['art']))

    for idx, z in enumerate(zadania):
        ile = int(z['ile'])
        wyd = WYDAJNOSC.get(str(z["art"]), 70)
        data_k = max(data_dzis, z['start_produkcji'])
        while ile > 0:
            if not pracujemy_niedziela and data_k.weekday() == 6: 
                data_k += datetime.timedelta(days=1); continue
            d_key = data_k.strftime("%Y-%m-%d")
            if d_key not in plan_dni: plan_dni[d_key] = MAX_CZAS
            wolny_czas = plan_dni[d_key]
            dostepny = wolny_czas if data_k != z['termin'] else max(0, 420 - (MAX_CZAS - wolny_czas))
            produkcja = min(dostepny // wyd, ile)
            is_nad = False
            if data_k == z['termin'] and ile > produkcja:
                produkcja = ile; is_nad = True
            if produkcja > 0:
                przyd = data_k + datetime.timedelta(days=80)
                raport.append({"Data": data_k.strftime("%d.%m"), "Dzień": DNI_PL.get(data_k.strftime("%A")), "Art": z["art"], "Palety": int(produkcja), "Kraj": z["kraj"], "Wysyłka": z["termin"].strftime("%d.%m"), "Przydatność": przyd.strftime("%d.%m.%y"), "dt_s": data_k, "nad": is_nad, "orig_idx": idx})
                ile -= produkcja
                plan_dni[d_key] -= (produkcja * wyd)
                if ile > 0: plan_dni[d_key] = 0
            if ile > 0: data_k += datetime.timedelta(days=1)
    
    widok = {}
    for r in sorted(raport, key=lambda x: x['dt_s']):
        dk = r['Data']
        if dk not in widok: widok[dk] = {"dz": r['Dzień'], "p": [], "suma": 0, "czas_suma": 0, "ma_nad": False, "prz": r["Przydatność"]}
        widok[dk]["p"].append(r); widok[dk]["suma"] += r["Palety"]; widok[dk]["czas_suma"] += r["Palety"] * WYDAJNOSC.get(str(r["Art"]), 70)
        if r["nad"]: widok[dk]["ma_nad"] = True
    return widok, raport

# --- PROGRAM GŁÓWNY ---
if 'kolejka' not in st.session_state:
    st.session_state.kolejka = wczytaj_dane()

with st.sidebar:
    st.header("⚙️ OPCJE")
    pracujemy_niedziela = st.checkbox("Planuj pracę w Niedziele", value=True)
    st.divider()

t1, t2 = st.tabs(["📥 WPISYWANIE", "📋 HARMONOGRAM NA HALĘ"])

with t1:
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
        if st.form_submit_button("DODAJ DO KOLEJKI"):
            st.session_state.kolejka.extend(nowe); zapisz_dane(st.session_state.kolejka); st.rerun()

    if st.session_state.kolejka:
        st.subheader("Kolejka (Edytuj bezpośrednio)")
        df_edit = pd.DataFrame(st.session_state.kolejka)
        def style_sk(row):
            return ['background-color: #C8E6C9' if row.kraj == 'Słowacja' else ''] * len(row)
        st.data_editor(df_edit.style.apply(style_sk, axis=1), use_container_width=True, hide_index=True)
        if st.button("USUŃ WSZYSTKO"):
            st.session_state.kolejka = []; zapisz_dane([]); st.rerun()

with t2:
    if st.session_state.kolejka:
        dni_plan, _ = generuj_plan_finalny(st.session_state.kolejka, pracujemy_niedziela)
        grid = st.columns(5)
        for i, dk in enumerate(sorted(dni_plan.keys(), key=lambda x: datetime.datetime.strptime(x, "%d.%m"))):
            with grid[i % 5]:
                d = dni_plan[dk]
                nad = d["ma_nad"] or d["czas_suma"] > 840
                c_h = "#E65100" if nad else "#1B5E20"
                badge_class = "date-badge-nad" if nad else "date-badge"
                
                # --- NAGŁÓWEK Z PEŁNĄ NAZWĄ DNIA ---
                c_head1, c_head2, c_head3 = st.columns([2.5, 3.5, 0.5])
                
                # Ramka z pełną datą (usunięto skracanie [:3])
                c_head1.markdown(f"<div class='{badge_class}'><b style='color:{c_h}; font-size:14px;'>{dk} ({d['dz']})</b></div>", unsafe_allow_html=True)
                
                # Duża przydatność na środku
                c_head2.markdown(f"<center><b style='color:#d32f2f; font-size:14px; line-height:35px;'>PRZ: {d['prz']}</b></center>", unsafe_allow_html=True)
                
                # Przycisk usuwania
                if c_head3.button("❌", key=f"del_{dk}"):
                    idxs = set(p['orig_idx'] for p in d['p'])
                    st.session_state.kolejka = [z for idx, z in enumerate(st.session_state.kolejka) if idx not in idxs]
                    zapisz_dane(st.session_state.kolejka); st.rerun()

                # --- TREŚĆ KARTY ---
                zm = "2 zmiany" if d["czas_suma"] > 420 else "1 zmiana"
                godz = "06-15 / 15-23" if nad else "06-14 / 14-22"
                bg_h = "#FFF3E0" if nad else "#F1F8E9"
                
                html = f"""<div class='karta-dnia' style='border-color:{c_h}'>
                <div style='background:{bg_h}; padding:5px; border-radius:5px; margin-bottom:10px;'>
                <b>SUMA: {int(d['suma'])} palet</b><br>
                <b style='color:#FF0000; font-size:12px;'>{zm} ({godz})</b>
                </div>"""
                for p in d['p']:
                    col = "#A5D6A7" if p['Kraj'] == "Słowacja" else "#F1F1F1"
                    html += f"<div style='background:{col}; border:1px solid #ccc; border-radius:5px; padding:5px; margin-bottom:5px; font-size:12px; color:#000;'>"
                    html += f"<b>Art {p['Art']} — {int(p['Palety'])} pal.</b><br>Auto: {p['Wysyłka']}</div>"
                st.markdown(html + "</div>", unsafe_allow_html=True)
                
