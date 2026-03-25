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
                    # Obsługa nowej daty startu dla starych rekordów
                    if 'start_produkcji' in z:
                        z['start_produkcji'] = datetime.datetime.strptime(z['start_produkcji'], "%Y-%m-%d").date()
                    else:
                        z['start_produkcji'] = datetime.date.today()
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
            z_kopia['start_produkcji'] = z_kopia['start_produkcji'].strftime("%Y-%m-%d")
            kolejka_do_zapisu.append(z_kopia)
        with open(PLIK_DANYCH, "w", encoding="utf-8") as f:
            json.dump(kolejka_do_zapisu, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

DNI_PL = {
    "Monday": "Poniedziałek", "Tuesday": "Wtorek", "Wednesday": "Środa",
    "Thursday": "Czwartek", "Friday": "Piątek", "Saturday": "Sobota", "Sunday": "Niedziela"
}

WYDAJNOSC = {
    "232": 84, "233": 56, "236": 84, "261": 84,
    "246": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 210
}

st.set_page_config(page_title="Konfekcja SM - Harmonogram", layout="wide")

if 'kolejka' not in st.session_state:
    st.session_state.kolejka = wczytaj_dane()

# --- LOGIKA PLANOWANIA ---
@st.cache_data
def generuj_plan_forward(kolejka_tuple, data_globalnego_startu):
    if not kolejka_tuple: 
        return {}, []

    zadania = [dict(z) for z in kolejka_tuple]
    plan_dni = {}
    raport = []
    MAX_CZAS_DOBA = 840 
    ostatni_art = None 

    while zadania:
        zadania.sort(key=lambda x: (x['termin'], x['art']))
        najpilniejszy_termin = zadania[0]['termin']
        idx_wybranego = -1
        
        if ostatni_art is not None:
            for i, z in enumerate(zadania):
                if z['termin'] == najpilniejszy_termin and z['art'] == ostatni_art:
                    idx_wybranego = i
                    break
        
        if idx_wybranego == -1:
            idx_wybranego = 0

        z = zadania.pop(idx_wybranego)
        ile = z['ile']
        wyd = WYDAJNOSC.get(z["art"], 70) 
        
        # LOGIKA STARTU: bierze pod uwagę albo globalny start, albo specyficzny start zamówienia
        data_kursora = max(data_globalnego_startu, z.get('start_produkcji', data_globalnego_startu))
        
        while ile > 0:
            if data_kursora.weekday() == 6: 
                data_kursora += datetime.timedelta(days=1)
                continue
                
            d_key = data_kursora.strftime("%Y-%m-%d")
            if d_key not in plan_dni:
                plan_dni[d_key] = MAX_CZAS_DOBA
            
            wolny_czas = plan_dni[d_key]
            
            if data_kursora == z['termin']:
                zajete_juz = MAX_CZAS_DOBA - wolny_czas
                dostepny_dzis = max(0, 420 - zajete_juz)
            else:
                dostepny_dzis = wolny_czas
                
            produkcja = min(dostepny_dzis // wyd, ile)
            is_nadgodziny = False
            
            jutro = data_kursora + datetime.timedelta(days=1)
            if jutro.weekday() == 6: jutro += datetime.timedelta(days=1)
            
            if jutro == z['termin']:
                d_key_jutro = jutro.strftime("%Y-%m-%d")
                wolne_jutro = plan_dni.get(d_key_jutro, MAX_CZAS_DOBA)
                zajete_jutro = MAX_CZAS_DOBA - wolne_jutro
                dostepne_jutro = max(0, 420 - zajete_jutro)
                potrzeba_na_jutro = (ile - produkcja) * wyd
                if potrzeba_na_jutro > dostepne_jutro:
                    dodatek = (ile - produkcja) - (dostepne_jutro // wyd)
                    if dodatek > 0:
                        produkcja += dodatek
                        is_nadgodziny = True

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
                    "StartProd": z["start_produkcji"].strftime("%d.%m"),
                    "dt_sort": data_kursora,
                    "termin_sort": z["termin"],
                    "Nadgodziny": is_nadgodziny
                })
                ile -= produkcja
                plan_dni[d_key] -= (produkcja * wyd)
                if ile > 0: plan_dni[d_key] = 0
                ostatni_art = z["art"]
            
            if ile > 0:
                data_kursora += datetime.timedelta(days=1)

    widok = {}
    raport.sort(key=lambda x: (x['dt_sort'], x['termin_sort'], x['Art']))
    for r in raport:
        dk = r['Data']
        if dk not in widok: 
            widok[dk] = {"dz": r['Dzień'], "suma": 0, "p": [], "nad": False, "czas_zajety": 0}
        widok[dk]["p"].append(r)
        widok[dk]["suma"] += r["Palety"]
        widok[dk]["czas_zajety"] += r["Palety"] * WYDAJNOSC.get(r["Art"], 70)
        if r["Nadgodziny"] or widok[dk]["czas_zajety"] > MAX_CZAS_DOBA:
            widok[dk]["nad"] = True
    return widok, raport

# --- INTERFEJS BOCZNY ---
with st.sidebar:
    st.title("Konfekcja SM")
    data_globalnego_startu = st.date_input("📅 Ogólny start maszyn", datetime.date.today())
    st.divider()

    if st.button("➕ DODAJ NOWE ZAMÓWIENIE", type="primary", use_container_width=True): 
        st.session_state.pokaz_f = True
    
    if st.button("🗑️ WYCZYŚĆ PLAN", use_container_width=True):
        st.session_state.kolejka = []
        zapisz_dane([])
        st.cache_data.clear()
        st.rerun()

    st.divider()
    if st.session_state.kolejka:
        st.subheader("✏️ Edytuj zamówienia")
        tab_cz, tab_sk = st.tabs(["🇨🇿 CZ", "🇸🇰 SK"])
        for tab, kraj_id in zip([tab_cz, tab_sk], ["Czechy", "Słowacja"]):
            with tab:
                for i, z in enumerate(st.session_state.kolejka):
                    if z['kraj'] == kraj_id:
                        with st.expander(f"Art {z['art']} ({z['termin'].strftime('%d.%m')})"):
                            z['ile'] = st.number_input("Palety", value=int(z['ile']), key=f"il_{i}")
                            z['start_produkcji'] = st.date_input("Start produkcji", value=z['start_produkcji'], key=f"st_{i}")
                            if st.button("Usuń", key=f"del_{i}"):
                                st.session_state.kolejka.pop(i)
                                zapisz_dane(st.session_state.kolejka)
                                st.rerun()
                            zapisz_dane(st.session_state.kolejka)

# --- GŁÓWNY EKRAN ---
if st.session_state.get('pokaz_f'):
    with st.form("add_form"):
        st.subheader("Nowe Zamówienie")
        c1, c2, c3 = st.columns(3)
        kraj = c1.selectbox("Kraj", ["Czechy", "Słowacja"])
        # TUTAJ DODANA MOŻLIWOŚĆ WYBORU DATY STARTU DLA ZAMÓWIENIA
        st_prod = c2.date_input("Kiedy można zacząć?", datetime.date.today())
        term_wys = c3.date_input("Termin wysyłki", datetime.date.today() + datetime.timedelta(days=3))
        
        st.write("Ilość palet per artykuł:")
        cols = st.columns(3)
        temp_dodaj = []
        for i, art_id in enumerate(WYDAJNOSC.keys()):
            with cols[i % 3]:
                v = st.number_input(f"Art {art_id}", min_value=0, step=1)
                if v > 0: temp_dodaj.append({"art": art_id, "ile": v, "termin": term_wys, "start_produkcji": st_prod, "kraj": kraj})
        
        if st.form_submit_button("Dodaj do planu"):
            st.session_state.kolejka.extend(temp_dodaj)
            zapisz_dane(st.session_state.kolejka)
            st.session_state.pokaz_f = False
            st.rerun()

if st.session_state.kolejka:
    k_tuple = tuple(tuple(d.items()) for d in st.session_state.kolejka)
    dni, raport_surowy = generuj_plan_forward(k_tuple, data_globalnego_startu)

    st.subheader(f"🗓️ Harmonogram od {data_globalnego_startu.strftime('%d.%m')}")
    grid = st.columns(5)
    sorted_dni = sorted(dni.keys(), key=lambda x: datetime.datetime.strptime(x, "%d.%m"))
    
    for i, dk in enumerate(sorted_dni):
        with grid[i % 5]:
            inf = dni[dk]
            border = "#ffb300" if inf["nad"] else "#e0e0e0"
            bg = "#fffcf2" if inf["nad"] else "white"
            
            karta_html = f"<div style='border:2px solid {border}; border-radius:8px; padding:10px; background-color:{bg}; margin-bottom:15px; min-height:280px;'>"
            karta_html += f"<div style='font-size:16px; font-weight:bold; color:#1f77b4;'>{dk} ({inf['dz']})</div>"
            karta_html += f"<div style='font-size:13px; color:green; font-weight:bold; border-bottom:1px solid #ddd; padding-bottom:5px; margin-bottom:8px;'>Suma: {inf['suma']} pal.</div>"
            
            for p in inf["p"]:
                is_sk = p["Kraj"] == "Słowacja"
                k_bg = "#a5d6a7" if is_sk else "#f1f1f1"
                karta_html += f"<div style='background-color:{k_bg}; padding:5px; border-radius:4px; margin-bottom:5px; border:1px solid #ccc; font-size:11px;'>"
                karta_html += f"<b>Art {p['Art']}</b>: {p['Palety']} pal.<br>"
                karta_html += f"<span style='color:#666;'>Start: {p['StartProd']} | Wys: {p['Wysyłka']}</span></div>"
                
            karta_html += "</div>"
            st.markdown(karta_html, unsafe_allow_html=True)

    # --- TABELA KONTROLNA ---
    st.divider()
    st.subheader("🔍 Status realizacji zamówień")
    df_z = pd.DataFrame(st.session_state.kolejka)
    df_z['Wysyłka'] = df_z['termin'].apply(lambda x: x.strftime("%d.%m"))
    res = df_z.groupby(['Wysyłka', 'kraj', 'art'])['ile'].sum().reset_index()
    res = res.rename(columns={'kraj': 'Kraj', 'art': 'Artykuł', 'ile': 'Zamówiono'})
    
    if raport_surowy:
        df_r = pd.DataFrame(raport_surowy)
        res_r = df_r.groupby(['Wysyłka', 'Kraj', 'Art'])['Palety'].sum().reset_index()
        res_r = res_r.rename(columns={'Art': 'Artykuł', 'Palety': 'Zaplanowano'})
        final = pd.merge(res, res_r, on=['Wysyłka', 'Kraj', 'Artykuł'], how='left').fillna(0)
    else:
        final = res.copy(); final['Zaplanowano'] = 0
        
    final['Status'] = final.apply(lambda x: "✅" if x['Zamówiono'] == x['Zaplanowano'] else "⏳", axis=1)
    st.dataframe(final.style.apply(lambda r: ['background-color: #c8e6c9' if r.Kraj == 'Słowacja' else ''] * len(r), axis=1), use_container_width=True, hide_index=True)
else:
    st.info("Dodaj zamówienia, aby zobaczyć plan.")
