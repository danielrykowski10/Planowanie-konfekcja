import streamlit as st
import datetime
import pandas as pd
import json
import os

# --- KONFIGURACJA ZAPISU DANYCH ---
PLIK_DANYCH = "dane_zamowien.json"

def wczytaj_dane():
    if os.path.exists(PLIK_DANYCH):
        try:
            with open(PLIK_DANYCH, "r", encoding="utf-8") as f:
                dane = json.load(f)
                for z in dane:
                    z['termin'] = datetime.datetime.strptime(z['termin'], "%Y-%m-%d").date()
                return dane
        except Exception:
            return []
    return []

def zapisz_dane(kolejka):
    try:
        kolejka_do_zapisu = []
        for z in kolejka:
            z_kopia = z.copy()
            z_kopia['termin'] = z_kopia['termin'].strftime("%Y-%m-%d")
            kolejka_do_zapisu.append(z_kopia)
        with open(PLIK_DANYCH, "w", encoding="utf-8") as f:
            json.dump(kolejka_do_zapisu, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

# Dane stałe
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
    st.session_state.kolejka = wczytaj_dane()

# --- PLANOWANIE ---
@st.cache_data
def generuj_plan_forward(kolejka_tuple, data_dzis):
    if not kolejka_tuple: 
        return {}, []

    zadania = [dict(z) for z in kolejka_tuple]
    plan_dni = {}
    raport = []
    CZAS_NETTO = 840 
    ostatni_art = None 

    while zadania:
        idx_wybranego = -1
        # 1. Szukaj kontynuacji tego samego artykułu
        for i, z in enumerate(zadania):
            if z['art'] == ostatni_art:
                idx_wybranego = i
                break
        
        # 2. Jeśli nie ma kontynuacji, bierz najwcześniejszą wysyłkę
        if idx_wybranego == -1:
            zadania.sort(key=lambda x: (x['termin'], x['art']))
            idx_wybranego = 0

        z = zadania.pop(idx_wybranego)
        ile = z['ile']
        wyd = WYDAJNOSC.get(z["art"], 70)
        data_kursora = data_dzis
        
        while ile > 0:
            if data_kursora.weekday() == 6: 
                data_kursora += datetime.timedelta(days=1)
                continue
                
            d_key = data_kursora.strftime("%Y-%m-%d")
            if d_key not in plan_dni:
                plan_dni[d_key] = CZAS_NETTO
            
            wolny_czas = plan_dni[d_key]
            
            # Logika wydajności w dniu wysyłki
            if data_kursora == z['termin']:
                zajete_dzis = CZAS_NETTO - wolny_czas
                dostepny_czas = max(0, 420 - zajete_dzis)
            else:
                dostepny_czas = wolny_czas
                
            produkcja = min(dostepny_czas // wyd, ile)
            nadgodziny = False
            
            # Sprawdzenie czy potrzebna wydłużona zmiana
            jutro = data_kursora + datetime.timedelta(days=1)
            if jutro.weekday() == 6: jutro += datetime.timedelta(days=1)
            
            if jutro == z['termin']:
                d_key_jutro = jutro.strftime("%Y-%m-%d")
                czas_jutro = plan_dni.get(d_key_jutro, CZAS_NETTO)
                dostepne_jutro = max(0, 420 - (CZAS_NETTO - czas_jutro))
                if (ile - produkcja) > (dostepne_jutro // wyd):
                    produkcja += (ile - produkcja) - (dostepne_jutro // wyd)
                    nadgodziny = True

            if data_kursora == z['termin'] and ile > produkcja:
                produkcja = ile 
                
            if produkcja > 0:
                raport.append({
                    "Data": data_kursora.strftime("%d.%m"),
                    "Dzień": DNI_PL.get(data_kursora.strftime("%A")),
                    "Art": z["art"],
                    "Palety": int(produkcja),
                    "Kraj": z.get("kraj", "Czechy"),
                    "Wysyłka": z["termin"].strftime("%d.%m"),
                    "dt_sort": data_kursora,
                    "termin_sort": z["termin"],
                    "Nadgodziny": nadgodziny
                })
                ile -= produkcja
                plan_dni[d_key] -= (produkcja * wyd)
                ostatni_art = z["art"]
            
            if ile > 0:
                data_kursora += datetime.timedelta(days=1)

    widok = {}
    raport.sort(key=lambda x: (x['dt_sort'], x['termin_sort']))
    for r in raport:
        dk = r['Data']
        if dk not in widok: 
            widok[dk] = {"dz": r['Dzień'], "suma": 0, "p": [], "nad": False}
        widok[dk]["p"].append(r)
        widok[dk]["suma"] += r["Palety"]
        if r["Nadgodziny"]: widok[dk]["nad"] = True
            
    return widok, raport

# --- INTERFEJS ---
with st.sidebar:
    st.header("⚙️ Zarządzanie")
    if st.button("➕ DODAJ ZAMÓWIENIE", type="primary", use_container_width=True): 
        st.session_state.pokaz_f = True
    
    if st.button("🗑️ WYCZYŚĆ WSZYSTKO", use_container_width=True):
        st.session_state.kolejka = []
        zapisz_dane([])
        st.rerun()

    if st.session_state.kolejka:
        st.divider()
        daty = sorted(list(set([z['termin'] for z in st.session_state.kolejka])))
        for d in daty:
            with st.expander(f"📅 Wysyłka: {d.strftime('%d.%m')}"):
                for i, z in enumerate(st.session_state.kolejka):
                    if z['termin'] == d:
                        c1, c2 = st.columns([3, 1])
                        c1.write(f"Art {z['art']} ({z['kraj']})")
                        if c2.button("❌", key=f"del_{i}"):
                            st.session_state.kolejka.pop(i)
                            zapisz_dane(st.session_state.kolejka)
                            st.rerun()

if st.session_state.get('pokaz_f'):
    with st.form("add_form"):
        kraj = st.selectbox("Kraj", ["Czechy", "Słowacja"])
        term = st.date_input("Termin", datetime.date.today() + datetime.timedelta(days=3))
        cols = st.columns(3)
        for i, art_id in enumerate(WYDAJNOSC.keys()):
            with cols[i % 3]:
                v = st.number_input(f"Art {art_id}", min_value=0, step=1)
                if v > 0: 
                    if 'temp_q' not in st.session_state: st.session_state.temp_q = []
                    st.session_state.temp_q.append({"art": art_id, "ile": v, "termin": term, "kraj": kraj})
        if st.form_submit_button("Zatwierdź"):
            st.session_state.kolejka.extend(st.session_state.temp_q)
            st.session_state.temp_q = []
            zapisz_dane(st.session_state.kolejka)
            st.session_state.pokaz_f = False
            st.rerun()

st.title("Konfekcja SM - Harmonogram")

if st.session_state.kolejka:
    k_tuple = tuple(tuple(d.items()) for d in st.session_state.kolejka)
    dni, raport_surowy = generuj_plan_forward(k_tuple, datetime.date.today())

    grid = st.columns(5)
    sorted_dni = sorted(dni.keys(), key=lambda x: datetime.datetime.strptime(x, "%d.%m"))
    
    for i, dk in enumerate(sorted_dni):
        with grid[i % 5]:
            inf = dni[dk]
            border = "#ffb300" if inf["nad"] else "#ddd"
            bg = "#fff8e1" if inf["nad"] else "white"
            
            st.markdown(f"""<div style="border:2px solid {border}; border-radius:10px; padding:10px; background-color:{bg}; margin-bottom:10px;">
                <b style="color:#1f77b4;">{dk} ({inf['dz']})</b><br>
                <b style="color:green;">Suma: {inf['suma']} pal.</b><hr style="margin:5px 0;">""", unsafe_allow_html=True)
            
            for p in inf["p"]:
                k_bg = "#d4edda" if p["Kraj"] == "Słowacja" else "#f8f9fa"
                st.markdown(f"""<div style="background-color:{k_bg}; padding:5px; border-radius:5px; margin-bottom:4px; border:1px solid #eee; font-size:12px;">
                    <b>{p['Art']}</b>: {p['Palety']} pal.<br>
                    <small>Wysyłka: {p['Wysyłka']} ({p['Kraj']})</small>
                </div>""", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("Dodaj zamówienia w panelu bocznym.")
