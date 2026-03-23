hfgfvhnvhn vbnvbcnbnvb
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

# Zaktualizowana wydajność: 1221217 robione w 120 minut (3,5 pal na zmianę 7h)
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
def generuj_plan_forward(kolejka_tuple, data_dzis):
    if not kolejka_tuple: 
        return {}, []

    zadania = [dict(z) for z in kolejka_tuple]
    plan_dni = {}
    raport = []
    MAX_CZAS_DOBA = 840 # 2 zmiany po 7h netto
    ostatni_art = None 

    while zadania:
        # 1. Zawsze najpierw sortujemy po terminie wysyłki, potem po artykule
        zadania.sort(key=lambda x: (x['termin'], x['art']))
        
        # 2. Sprawdzamy, jaki jest NAJPILNIEJSZY termin w całej kolejce
        najpilniejszy_termin = zadania[0]['termin']
        
        idx_wybranego = -1
        
        # 3. Szukamy kontynuacji asortymentu, ale TYLKO w obrębie najpilniejszego terminu wysyłki!
        if ostatni_art is not None:
            for i, z in enumerate(zadania):
                if z['termin'] == najpilniejszy_termin and z['art'] == ostatni_art:
                    idx_wybranego = i
                    break
        
        # 4. Jeśli nie ma kontynuacji w tej samej dacie wysyłki, bierzemy pierwsze z brzegu dla tej daty
        if idx_wybranego == -1:
            idx_wybranego = 0

        z = zadania.pop(idx_wybranego)
        ile = z['ile']
        wyd = WYDAJNOSC.get(z["art"], 70) 
        data_kursora = data_dzis
        
        while ile > 0:
            if data_kursora.weekday() == 6: # Pomiń niedzielę
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
                    "dt_sort": data_kursora,
                    "termin_sort": z["termin"],
                    "Nadgodziny": is_nadgodziny
                })
                ile -= produkcja
                plan_dni[d_key] -= (produkcja * wyd)
                
                # BLOKADA MASZYNY - żeby nie wpychać innego artykułu, jeśli ten nie jest skończony
                if ile > 0:
                    plan_dni[d_key] = 0
                    
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
    st.markdown('<div style="font-size: 24px; font-weight: bold; color: #1f77b4; margin-bottom:15px;">Konfekcja SM</div>', unsafe_allow_html=True)
    
    if st.button("➕ DODAJ ZAMÓWIENIE", type="primary", use_container_width=True): 
        st.session_state.pokaz_f = True
    
    if st.button("🗑️ WYCZYŚĆ WSZYSTKO", use_container_width=True):
        st.session_state.kolejka = []
        zapisz_dane([])
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.subheader("✏️ Historia i Edycja Zamówień")
    
    if st.session_state.kolejka:
        tab_cz, tab_sk = st.tabs(["🇨🇿 Czechy", "🇸🇰 Słowacja"])
        
        for zakładka, wybrany_kraj in zip([tab_cz, tab_sk], ["Czechy", "Słowacja"]):
            with zakładka:
                daty = sorted(list(set([z['termin'] for z in st.session_state.kolejka if z['kraj'] == wybrany_kraj])))
                
                if not daty:
                    st.info(f"Brak zamówień na {wybrany_kraj}")
                else:
                    for d in daty:
                        with st.expander(f"📅 Wysyłka: {d.strftime('%d.%m')}"):
                            for i, z in enumerate(st.session_state.kolejka):
                                if z['termin'] == d and z['kraj'] == wybrany_kraj:
                                    c1, c2 = st.columns([3, 1])
                                    nowa_il = c1.number_input(f"Art {z['art']}", value=int(z['ile']), min_value=1, key=f"ed_{i}")
                                    
                                    if c2.button("❌", key=f"del_{i}"):
                                        st.session_state.kolejka.pop(i)
                                        zapisz_dane(st.session_state.kolejka)
                                        st.rerun()
                                    
                                    if nowa_il != z['ile']:
                                        st.session_state.kolejka[i]['ile'] = nowa_il
                                        zapisz_dane(st.session_state.kolejka)
                                        st.rerun()
    else:
        st.info("Brak wprowadzonych zamówień.")

# --- GŁÓWNY EKRAN ---
st.title("Harmonogram Produkcji")

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

    st.subheader("🗓️ Realny Plan Produkcji")
    grid = st.columns(5)
    sorted_dni = sorted(dni.keys(), key=lambda x: datetime.datetime.strptime(x, "%d.%m"))
    
    for i, dk in enumerate(sorted_dni):
        with grid[i % 5]:
            inf = dni[dk]
            border = "#ffb300" if inf["nad"] else "#e0e0e0"
            bg = "#fffcf2" if inf["nad"] else "white"
            txt_nad = "<br><span style='color:#e65100; font-weight:bold; font-size:12px;'>⚠️ ZMIANA WYDŁUŻONA</span>" if inf["nad"] else ""
            
            # --- OBLICZANIE ZMIAN I GODZIN PRACY ---
            if inf["czas_zajety"] <= 420:
                if inf["nad"]:
                    tekst_zmiany = "⏱️ 1 zmiana (06:00 - 15:00)"
                else:
                    tekst_zmiany = "⏱️ 1 zmiana (06:00 - 14:00)"
            else:
                if inf["nad"]:
                    tekst_zmiany = "⏱️ 2 zmiany (06:00 - 15:00, 15:00 - 23:00)"
                else:
                    tekst_zmiany = "⏱️ 2 zmiany (06:00 - 14:00, 14:00 - 22:00)"
            
            styl_zmiany = "color:#e65100; font-size:13px; font-weight:bold;" if inf["nad"] else "color:#444; font-size:13px; font-weight:bold;"
                
            karta_html = f"<div style='border:2px solid {border}; border-radius:8px; padding:10px; background-color:{bg}; margin-bottom:15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>"
            karta_html += f"<div style='font-size:16px; font-weight:bold; color:#1f77b4; margin-bottom:4px;'>{dk} ({inf['dz']}){txt_nad}</div>"
            karta_html += f"<div style='font-size:14px; font-weight:bold; color:green; border-bottom:1px solid {border}; padding-bottom:8px; margin-bottom:8px;'>Suma: {inf['suma']} pal.<br><span style='{styl_zmiany}'>{tekst_zmiany}</span></div>"
            
            for p in inf["p"]:
                k_bg = "#d4edda" if p["Kraj"] == "Słowacja" else "#f8f9fa"
                karta_html += f"<div style='background-color:{k_bg}; padding:6px; border-radius:5px; margin-bottom:6px; border:1px solid #ddd; font-size:12px;'><b style='font-size:13px;'>Art {p['Art']}</b>: {p['Palety']} pal.<br><span style='color:#555;'>Wysyłka: {p['Wysyłka']} ({p['Kraj']})</span></div>"
                
            karta_html += "</div>"
            
            st.markdown(karta_html, unsafe_allow_html=True)

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
