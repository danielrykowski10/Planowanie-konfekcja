import streamlit as st
import datetime
import pandas as pd
import json
import os

# --- KONFIGURACJA ---
PLIK_DANYCH = "dane_zamowien.json"
st.set_page_config(page_title="Konfekcja SM", layout="wide")

# --- CZYSZCZENIE STYLI ---
st.markdown("""
<style>
    .stTabs [data-baseweb="tab"] { font-weight: bold; border-radius: 8px 8px 0 0; }
    .stTabs [aria-selected="true"] { background-color: #2E7D32 !important; color: white !important; }
    
    .karta-dnia {
        border: 2px solid #1B5E20;
        border-radius: 12px;
        padding: 12px;
        background-color: white;
        margin-bottom: 20px;
    }
    .karta-nad { border-color: #E65100; }
    
    .naglowek-karty {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
        border-bottom: 1px solid #eee;
        padding-bottom: 5px;
    }
</style>
""", unsafe_allow_html=True)

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
    do_zapisu = []
    for z in kolejka:
        kopia = z.copy()
        if isinstance(kopia['termin'], datetime.date): kopia['termin'] = kopia['termin'].strftime("%Y-%m-%d")
        if isinstance(kopia['start_produkcji'], datetime.date): kopia['start_produkcji'] = kopia['start_produkcji'].strftime("%Y-%m-%d")
        do_zapisu.append(kopia)
    with open(PLIK_DANYCH, "w", encoding="utf-8") as f:
        json.dump(do_zapisu, f, ensure_ascii=False, indent=4)

DNI_PL = {"Monday": "Poniedziałek", "Tuesday": "Wtorek", "Wednesday": "Środa", "Thursday": "Czwartek", "Friday": "Piątek", "Saturday": "Sobota", "Sunday": "Niedziela"}
WYDAJNOSC = {"232": 84, "233": 56, "236": 84, "261": 84, "246": 84, "254": 52.5, "1221217": 120, "1221070": 52.5, "1221181": 210}

if 'kolejka' not in st.session_state:
    st.session_state.kolejka = wczytaj_dane()

tab1, tab2 = st.tabs(["📥 WPISYWANIE", "📋 HARMONOGRAM"])

with tab1:
    with st.form("form_nowe"):
        c1, c2, c3 = st.columns(3)
        v_kraj = c1.selectbox("Kierunek", ["Czechy", "Słowacja"])
        v_start = c2.date_input("Start produkcji", datetime.date.today())
        v_koniec = c3.date_input("Wysyłka", datetime.date.today() + datetime.timedelta(days=3))
        
        cols = st.columns(5)
        nowe_wpisy = []
        for i, art_id in enumerate(WYDAJNOSC.keys()):
            with cols[i % 5]:
                ile = st.number_input(f"Art {art_id}", min_value=0, step=1)
                if ile > 0:
                    nowe_wpisy.append({"art": art_id, "ile": ile, "termin": v_koniec, "start_produkcji": v_start, "kraj": v_kraj})
        
        if st.form_submit_button("DODAJ DO PLANU"):
            st.session_state.kolejka.extend(nowe_wpisy)
            zapisz_dane(st.session_state.kolejka)
            st.rerun()

    if st.session_state.kolejka:
        df = pd.DataFrame(st.session_state.kolejka)
        
        # --- FILTR ZIELONY DLA SŁOWACJI (ZDJĘCIE 1) ---
        def koloruj_slowacje(s):
            return ['background-color: #C8E6C9' if s.kraj == 'Słowacja' else '' for _ in s]
        
        st.subheader("Bieżąca kolejka")
        st.data_editor(df.style.apply(koloruj_slowacje, axis=1), use_container_width=True)
        
        if st.button("WYCZYŚĆ WSZYSTKO"):
            st.session_state.kolejka = []
            zapisz_dane([])
            st.rerun()

with tab2:
    # Uproszczona logika generowania widoku
    if st.session_state.kolejka:
        # Sortowanie i przygotowanie danych
        plan_dni = {}
        pracujemy_nd = st.sidebar.checkbox("Praca w niedzielę", value=True)
        
        # Tu uproszczony silnik dla stabilności widoku
        for idx, z in enumerate(st.session_state.kolejka):
            d_key = z['start_produkcji'].strftime("%d.%m")
            if d_key not in plan_dni:
                przyd = z['start_produkcji'] + datetime.timedelta(days=80)
                plan_dni[d_key] = {"data": d_key, "dz": DNI_PL.get(z['start_produkcji'].strftime("%A")), "prz": przyd.strftime("%d.%m"), "items": [], "suma": 0}
            plan_dni[d_key]["items"].append(z)
            plan_dni[d_key]["suma"] += z['ile']

        grid = st.columns(5)
        for i, (k, d) in enumerate(plan_dni.items()):
            with grid[i % 5]:
                # --- CAŁA KARTA W JEDNYM OBRAMOWANIU (ZDJĘCIE 2) ---
                is_nad = d["suma"] > 10 # Przykład logiki nadgodzin
                klasa = "karta-dnia karta-nad" if is_nad else "karta-dnia"
                kolor_tekst = "#E65100" if is_nad else "#1B5E20"
                
                html = f"""
                <div class="{klasa}">
                    <div class="naglowek-karty">
                        <span style="background:#F1F8E9; border:1px solid {kolor_tekst}; padding:2px 5px; border-radius:5px; font-weight:bold; font-size:12px;">{d['data']} ({d['dz']})</span>
                        <span style="color:red; font-weight:bold; font-size:12px;">PRZ: {d['prz']}</span>
                    </div>
                    <div style="font-size:13px; margin-bottom:10px;"><b>SUMA: {int(d['suma'])} palet</b></div>
                """
                
                for item in d['items']:
                    bg = "#C8E6C9" if item['kraj'] == "Słowacja" else "#f1f1f1"
                    html += f"""
                    <div style="background:{bg}; padding:4px; border-radius:4px; margin-bottom:4px; border:1px solid #ddd; font-size:11px;">
                        <b>Art {item['art']}</b> - {item['ile']} pal.<br>Kierunek: {item['kraj']}
                    </div>
                    """
                
                st.markdown(html + "</div>", unsafe_allow_html=True)
                if st.button(f"Usuń {k}", key=f"del_{k}"):
                    st.session_state.kolejka = [z for z in st.session_state.kolejka if z['start_produkcji'].strftime("%d.%m") != k]
                    zapisz_dane(st.session_state.kolejka)
                    st.rerun()
