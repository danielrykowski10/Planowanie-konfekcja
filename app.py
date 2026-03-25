import streamlit as st
import datetime
import pandas as pd
import json
import os

# --- KONFIGURACJA PLIKU ---
PLIK_DANYCH = "dane_zamowien.json"
st.set_page_config(page_title="Konfekcja SM", layout="wide")

# --- STYLIZACJA CSS ---
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #2E7D32 !important; color: white !important; }
    
    /* ZDJĘCIE 2: Obramowanie na całość karty */
    .karta-wrapper {
        border: 2px solid #1B5E20;
        border-radius: 12px;
        padding: 12px;
        background-color: white;
        margin-bottom: 20px;
        min-height: 250px;
    }
    .karta-nad-border { border-color: #E65100 !important; }
    
    .naglowek-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNKCJE ---
def wczytaj_dane():
    if os.path.exists(PLIK_DANYCH):
        try:
            with open(PLIK_DANYCH, "r", encoding="utf-8") as f:
                d = json.load(f)
                for x in d:
                    x['termin'] = datetime.datetime.strptime(x['termin'], "%Y-%m-%d").date()
                    x['start_produkcji'] = datetime.datetime.strptime(x.get('start_produkcji', datetime.date.today().strftime("%Y-%m-%d")), "%Y-%m-%d").date()
                return d
        except: return []
    return []

def zapisz_dane(kolejka):
    do_zapisu = []
    for x in kolejka:
        k = x.copy()
        k['termin'] = k['termin'].strftime("%Y-%m-%d") if isinstance(k['termin'], datetime.date) else k['termin']
        k['start_produkcji'] = k['start_produkcji'].strftime("%Y-%m-%d") if isinstance(k['start_produkcji'], datetime.date) else k['start_produkcji']
        do_zapisu.append(k)
    with open(PLIK_DANYCH, "w", encoding="utf-8") as f:
        json.dump(do_zapisu, f, ensure_ascii=False, indent=4)

if 'kolejka' not in st.session_state:
    st.session_state.kolejka = wczytaj_dane()

# --- INTERFEJS ---
t1, t2 = st.tabs(["📥 WPISYWANIE", "📋 HARMONOGRAM"])

with t1:
    with st.form("dodaj_form"):
        c1, c2, c3 = st.columns(3)
        f_kraj = c1.selectbox("Kierunek", ["Czechy", "Słowacja"])
        f_start = c2.date_input("Start produkcji", datetime.date.today())
        f_koniec = c3.date_input("Wysyłka", datetime.date.today() + datetime.timedelta(days=3))
        
        art_ids = ["232", "233", "236", "261", "246", "254", "1221217", "1221070", "1221181"]
        cols = st.columns(5)
        nowe = []
        for i, aid in enumerate(art_ids):
            with cols[i % 5]:
                ile = st.number_input(f"Art {aid}", min_value=0, step=1)
                if ile > 0:
                    nowe.append({"art": aid, "ile": ile, "termin": f_koniec, "start_produkcji": f_start, "kraj": f_kraj})
        
        if st.form_submit_button("DODAJ DO KOLEJKI"):
            st.session_state.kolejka.extend(nowe)
            zapisz_dane(st.session_state.kolejka)
            st.rerun()

    if st.session_state.kolejka:
        df = pd.DataFrame(st.session_state.kolejka)
        
        # --- ZDJĘCIE 1: SŁOWACJA NA ZIELONO ---
        def apply_color(row):
            if row['kraj'] == 'Słowacja':
                return ['background-color: #C8E6C9'] * len(row)
            return [''] * len(row)
        
        st.subheader("Bieżąca kolejka")
        st.data_editor(df.style.apply(apply_color, axis=1), use_container_width=True, hide_index=True)
        
        if st.button("USUŃ WSZYSTKO"):
            st.session_state.kolejka = []
            zapisz_dane([])
            st.rerun()

with t2:
    if st.session_state.kolejka:
        # Grupowanie po dacie startu dla widoku halowego
        dni = {}
        dni_pl = {"Monday": "Poniedziałek", "Tuesday": "Wtorek", "Wednesday": "Środa", "Thursday": "Czwartek", "Friday": "Piątek", "Saturday": "Sobota", "Sunday": "Niedziela"}
        
        for item in st.session_state.kolejka:
            k = item['start_produkcji'].strftime("%Y-%m-%d")
            if k not in dni:
                przyd = item['start_produkcji'] + datetime.timedelta(days=80)
                dni[k] = {"data": item['start_produkcji'].strftime("%d.%m"), "dzien": dni_pl.get(item['start_produkcji'].strftime("%A")), "prz": przyd.strftime("%d.%m"), "items": [], "suma": 0}
            dni[k]["items"].append(item)
            dni[k]["suma"] += item['ile']

        grid = st.columns(5)
        for i, (klucz, d) in enumerate(sorted(dni.items())):
            with grid[i % 5]:
                # Logika nadgodzin (np. powyżej 15 palet)
                is_nad = d['suma'] > 15
                border_style = "karta-nad-border" if is_nad else ""
                badge_color = "#E65100" if is_nad else "#1B5E20"
                
                # --- ZDJĘCIE 2: CAŁA KARTA W RAMCE ---
                html = f"""
                <div class="karta-wrapper {border_style}">
                    <div class="naglowek-row">
                        <div style="background:#F1F8E9; border:1.5px solid {badge_color}; padding:3px 8px; border-radius:8px; font-weight:bold; font-size:12px; color:{badge_color};">
                            {d['data']} ({d['dzien'][:3]})
                        </div>
                        <div style="color:#D32F2F; font-weight:bold; font-size:12px;">PRZ: {d['prz']}</div>
                    </div>
                    <div style="margin-bottom:10px;">
                        <b>SUMA: {int(d['suma'])} palet</b><br>
                        <small style="color:red;">{"2 zmiany (NADGODZINY)" if is_nad else "1 zmiana"}</small>
                    </div>
                """
                
                for it in d['items']:
                    bg = "#C8E6C9" if it['kraj'] == "Słowacja" else "#F1F1F1"
                    html += f"""
                    <div style="background:{bg}; border:1px solid #ddd; border-radius:6px; padding:5px; margin-bottom:5px; font-size:11px;">
                        <b>Art {it['art']} - {int(it['ile'])} pal.</b><br>
                        <span style="font-size:10px;">{it['kraj']}</span>
                    </div>
                    """
                st.markdown(html + "</div>", unsafe_allow_html=True)
                
                if st.button("Usuń dzień", key=f"btn_{klucz}"):
                    st.session_state.kolejka = [x for x in st.session_state.kolejka if x['start_produkcji'].strftime("%Y-%m-%d") != klucz]
                    zapisz_dane(st.session_state.kolejka)
                    st.rerun()
