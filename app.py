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

DNI_PL = {
    "Monday": "Poniedziałek", "Tuesday": "Wtorek", "Wednesday": "Środa",
    "Thursday": "Czwartek", "Friday": "Piątek", "Saturday": "Sobota", "Sunday": "Niedziela"
}

# --- NOWE NORMY WYDAJNOŚCIOWE (MINUTY NA PALETĘ) ---
WYDAJNOSC = {
    "232": 84, 
    "233": 56, 
    "236": 84, 
    "261": 84,
    "246": 84, 
    "254": 52.5, 
    "1221217": 240,
    "1221070": 52.5, 
    "1221181": 210
}

st.set_page_config(page_title="Konfekcja SM - Harmonogram", layout="wide")

if 'kolejka' not in st.session_state:
    st.session_state.kolejka = wczytaj_dane()

# --- LOGIKA PLANOWANIA ---
@st.cache_data
def generuj_plan_forward(kolejka_tuple, data_dzis):
    if not kolejka_tuple: 
        return {}, []

    zadania = [dict(z) for z in kolejka_tuple]
    plan_dni = {}
    raport = []
    MAX_CZAS_DOBA = 840 # 2 zmiany po 7h netto
    ostatni_art = None 

    while zadania:
        idx_wybranego = -1
        
        # 1. Kontynuacja asortymentu
        if ostatni_art is not None:
            for i, z in enumerate(zadania):
                if z['art'] == ostatni_art:
                    idx_wybranego = i
                    break
        
        # 2. Najpilniejszy termin
        if idx_wybranego == -1:
            zadania.sort(key=lambda x: (x['termin'], x['art']))
            idx_wybranego = 0

        z = zadania.pop(idx_wybranego)
        ile = z['ile']
        wyd = WYDAJNOSC.get(z["art"], 70) # Domyślnie 70, jeśli dodasz kiedyś nowy bez wpisu
        data_kursora = data_dzis
        
        while ile > 0:
            if data_kursora.weekday() == 6: # Pomiń niedzielę
                data_kursora += datetime.timedelta(days=1)
                continue
                
            d_key = data_kursora.strftime("%Y-%m-%d")
            if d_key not in plan_dni:
                plan_dni[d_key] = MAX_CZAS_DOBA
            
            wolny_czas = plan_dni[d_key]
            
            # Dzień wysyłki: produkcja musi skończyć się na 1 zmianie (420 min)
            if data_kursora == z['termin']:
                zajete_juz = MAX_CZAS_DOBA - wolny_czas
                dostepny_dzis = max(0, 420 - zajete_juz)
            else:
                dostepny_dzis = wolny_czas
                
            produkcja = min(dostepny_dzis // wyd, ile)
            is_nadgodziny = False
            
            # WYKRYWANIE NADGODZIN: Jeśli musimy zrobić więcej niż pozwala czas
            jutro = data_kursora + datetime.timedelta(days=1)
            if jutro.weekday() == 6: jutro += datetime.timedelta(days=1)
            
            if jutro == z['termin']:
                d_key_jutro = jutro.strftime("%Y-%m-%d")
                wolne_jutro = plan_dni.get(d_key_jutro, MAX_CZAS_DOBA)
                zajete_jutro = MAX_CZAS_DOBA - wolne_jutro
                dostepne_jutro = max(0, 420 - zajete_jutro)
                
                potrzeba_na_jutro = (ile - produkcja) * wyd
                if potrzeba_na_jutro > (dostepne_jutro):
                    dodatek = (ile - produkcja) - (dostepne_jutro // wyd)
                    produkcja += dodatek
                    is_nadgodziny = True

            # Jeśli dzisiaj jest wysyłka i nadal mamy palety - wymuś produkcję w nadgodzinach
            if data_kursora == z['termin'] and ile > produkcja:
                produkcja = ile 
                is_nadgodziny = True
                
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
                    "Nadgodziny": is_nadgodziny
                })
                ile -= produkcja
                plan_dni[d_key] -= (produkcja * wyd)
                ostatni_art = z["art"]
            
            if ile > 0:
                data_kursora += datetime.timedelta(days=1)

    # Budowanie widoku kafelków
    widok = {}
    raport.sort(key=lambda x: (x['dt_sort'], x['termin_sort'], x['Art']))
    for r in raport:
        dk = r['Data']
        if dk not in widok: 
            widok[dk] = {"dz": r['Dzień'], "suma": 0, "p": [], "nad": False, "czas_zajety": 0}
        widok[dk]["p"].append(r)
        widok[dk]["suma"] += r["Palety"]
        widok[dk]["czas_zajety"] += r["Palety"] * WYDAJNOSC.get(r["Art"], 70)
        
        # Flaga Nadgodziny lub przekroczony fizyczny czas (840 min)
        if r["Nadgodziny"] or widok[dk]["czas_zajety"] > MAX_CZAS_DOBA:
            widok[dk]["nad"] = True
            
    return widok, raport

# --- INTERFEJS ---
with st.sidebar:
    st.header("⚙️ Zarządzanie")
    if st.button("➕ DODAJ ZAMÓWIENIE", type="primary", use_container_width=True): 
        st.session_state.pokaz_f = True
    
    if st.button("🗑️ WYCZYŚĆ WSZYSTKO", use_container_width=True):
        st.session_state.kolejka = []
        zapisz_dane([])
        st.cache_data.clear()
        st.rerun()

st.title("Konfekcja SM - Harmonogram Produkcji")

if st.session_state.get('pokaz_f'):
    with st.form("add_form"):
        kraj = st.selectbox("Kraj", ["Czechy", "Słowacja"])
        term = st.date_input("Termin", datetime.date.today() + datetime.timedelta(days=2))
        cols = st.columns(3)
        temp_dodaj = []
        for i, art_id in enumerate(WYDAJNOSC.keys()):
            with cols[i % 3]:
                v = st.number_input(f"Art {art_id}", min_value=0, step=1)
                if v > 0: temp_dodaj.append({"art": art_id, "ile": v, "termin": term, "kraj": kraj})
        if st.form_submit_button("Zatwierdź"):
            st.session_state.kolejka.extend(temp_dodaj)
            zapisz_dane(st.session_state.kolejka)
            st.session_state.pokaz_f = False
            st.rerun()

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
            txt_nad = "<br><span style='color:#e65100; font-weight:bold; font-size:13px;'>⚠️ WYDŁUŻONA ZMIANA</span>" if inf["nad"] else ""
            
            st.markdown(f"""<div style="border:2px solid {border}; border-radius:10px; padding:10px; background-color:{bg}; min-height:150px; margin-bottom:10px;">
                <b style="color:#1f77b4;">{dk} ({inf['dz']})</b>{txt_nad}<br>
                <b style="color:green;">Suma: {inf['suma']} pal.</b><hr style="margin:5px 0;">""", unsafe_allow_html=True)
            
            for p in inf["p"]:
                k_bg = "#d4edda" if p["Kraj"] == "Słowacja" else "#f8f9fa"
                st.markdown(f"""<div style="background-color:{k_bg}; padding:5px; border-radius:5px; margin-bottom:4px; border:1px solid #eee; font-size:12px;">
                    <b>{p['Art']}</b>: {p['Palety']} pal.<br>
                    <small>Wysyłka: {p['Wysyłka']} ({p['Kraj']})</small>
                </div>""", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # --- TABELA KONTROLNA ---
    st.divider()
    st.subheader("🔍 Kontrola zgodności zamówień")
    
    df_z = pd.DataFrame(st.session_state.kolejka)
    df_z['Wysyłka'] = df_z['termin'].apply(lambda x: x.strftime("%d.%m"))
    res = df_z.groupby(['Wysyłka', 'kraj', 'art'])['ile'].sum().reset_index()
    res = res.rename(columns={'kraj': 'Kraj', 'art': 'Artykuł', 'ile': 'Zamówiono (pal)'})
    
    if raport_surowy:
        df_r = pd.DataFrame(raport_surowy)
        res_r = df_r.groupby(['Wysyłka', 'Kraj', 'Art'])['Palety'].sum().reset_index()
        res_r = res_r.rename(columns={'Art': 'Artykuł', 'Palety': 'Zaplanowano (pal)'})
        final = pd.merge(res, res_r, on=['Wysyłka', 'Kraj', 'Artykuł'], how='left').fillna(0)
    else:
        final = res.copy()
        final['Zaplanowano (pal)'] = 0
        
    final['Status'] = final.apply(lambda x: "✅ OK" if x['Zamówiono (pal)'] == x['Zaplanowano (pal)'] else "❌ BŁĄD", axis=1)
    
    def style_wiersze(row):
        kolor = '#d4edda' if row['Kraj'] == 'Słowacja' else ''
        return [f'background-color: {kolor}'] * len(row)
    
    st.dataframe(final.style.apply(style_wiersze, axis=1), use_container_width=True, hide_index=True)

else:
    st.info("Brak zamówień. Dodaj je w panelu bocznym.")
