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
        except Exception as e:
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
    except Exception as e:
        pass

# 1. Dane stałe
DNI_PL = {
    "Monday": "Poniedziałek", "Tuesday": "Wtorek", "Wednesday": "Środa",
    "Thursday": "Czwartek", "Friday": "Piątek", "Saturday": "Sobota", "Sunday": "Niedziela"
}

WYDAJNOSC = {
    "232": 70, "233": 50, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Konfekcja SM - Harmonogram", layout="wide")

if 'kolejka' not in st.session_state:
    st.session_state.kolejka = wczytaj_dane()

# --- PLANOWANIE W PRZÓD ---
@st.cache_data
def generuj_plan_forward(kolejka_tuple, data_dzis):
    if not kolejka_tuple: return {}, []

    zadania = [dict(z) for z in kolejka_tuple]
    
    plan_dni = {}
    raport = []
    CZAS_NETTO = 840 # 2 zmiany po 7h netto
    ostatni_art = None
    
    while zadania:
        najblizsza_wysylka = min(z['termin'] for z in zadania)
        
        idx_wybranego = -1
        for i, z in enumerate(zadania):
            if z['termin'] == najblizsza_wysylka and z['art'] == ostatni_art:
                idx_wybranego = i
                break
        
        if idx_wybranego == -1:
            for i, z in enumerate(zadania):
                if z['termin'] == najblizsza_wysylka:
                    idx_wybranego = i
                    break

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
            
            if data_kursora == z['termin']:
                zajete_dzis = CZAS_NETTO - wolny_czas
                dostepny_czas = max(0, 420 - zajete_dzis) 
            else:
                dostepny_czas = wolny_czas
                
            produkcja = min(dostepny_czas // wyd, ile)
            nadgodziny = False
            
            jutro = data_kursora + datetime.timedelta(days=1)
            if jutro.weekday() == 6:
                jutro += datetime.timedelta(days=1)
                
            jesli_kursor_to_przed_wysylka = jutro == z['termin']
            
            if jesli_kursor_to_przed_wysylka:
                d_key_jutro = jutro.strftime("%Y-%m-%d")
                czas_jutro = plan_dni.get(d_key_jutro, CZAS_NETTO)
                zajete_jutro = CZAS_NETTO - czas_jutro
                dostepne_jutro = max(0, 420 - zajete_jutro)
                
                ile_zrobimy_jutro = dostepne_jutro // wyd
                
                if (ile - produkcja) > ile_zrobimy_jutro:
                    nadwyzka = (ile - produkcja) - ile_zrobimy_jutro
                    produkcja += nadwyzka 
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
                    "termin_sort": z["termin"], # KLUCZOWE: zapisujemy datę wysyłki do sortowania
                    "Nadgodziny": nadgodziny
                })
                ile -= produkcja
                plan_dni[d_key] -= (produkcja * wyd)
                ostatni_art = z["art"]
            
            if ile > 0:
                data_kursora += datetime.timedelta(days=1)

    # GRUPOWANIE WIDOKU 
    widok = {}
    # KLUCZOWA ZMIANA: Sortujemy najpierw po dacie produkcji, POTEM po dacie wysyłki, na końcu po artykule
    raport = sorted(raport, key=lambda x: (x['dt_sort'], x['termin_sort'], x['Art']))
    
    for r in raport:
        dk = r['Data']
        if dk not in widok: 
            widok[dk] = {"dz": r['Dzień'], "suma": 0, "p": [], "nadgodziny_w_dniu": False}
        widok[dk]["p"].append(r)
        widok[dk]["suma"] += r["Palety"]
        if r.get("Nadgodziny"):
            widok[dk]["nadgodziny_w_dniu"] = True
            
    return widok, raport

# --- INTERFEJS ---
with st.sidebar:
    st.markdown("""
        <style>
            .sidebar-title { display: flex; align-items: center; gap: 10px; font-size: 24px; font-weight: bold; color: #1f77b4; }
        </style>
    """, unsafe_allow_html=True)
    st.markdown('<div class="sidebar-title">Konfekcja SM</div>', unsafe_allow_html=True)
    
    st.header("⚙️ Zarządzanie")
    if st.button("➕ DODAJ ZAMÓWIENIE", type="primary", use_container_width=True): 
        st.session_state.pokaz_f = True
    
    if st.button("🗑️ WYCZYŚĆ WSZYSTKO", use_container_width=True):
        st.session_state.kolejka = []
        zapisz_dane(st.session_state.kolejka) 
        st.cache_data.clear()
        st.rerun()

    if st.session_state.kolejka:
        st.divider()
        st.subheader("✏️ Edytuj zamówienia")
        daty = sorted(list(set([z['termin'] for z in st.session_state.kolejka])))
        for d in daty:
            with st.expander(f"📅 Wysyłka: {d.strftime('%d.%m')}"):
                for kraj in ["Czechy", "Słowacja"]:
                    st.caption(f"--- {kraj} ---")
                    for i, z in enumerate(st.session_state.kolejka):
                        if z['termin'] == d and z['kraj'] == kraj:
                            c1, c2 = st.columns([3, 1])
                            nowa_il = c1.number_input(f"Art {z['art']}", value=int(z['ile']), key=f"ed_{i}")
                            
                            if c2.button("❌", key=f"del_{i}"):
                                st.session_state.kolejka.pop(i)
                                zapisz_dane(st.session_state.kolejka)
                                st.rerun()
                                
                            if nowa_il != z['ile']:
                                st.session_state.kolejka[i]['ile'] = nowa_il
                                zapisz_dane(st.session_state.kolejka)
                                st.rerun()

if st.session_state.get('pokaz_f'):
    with st.form("quick_add", clear_on_submit=True):
        st.subheader("📝 Nowe zamówienie")
        c1, c2 = st.columns(2)
        kraj_n = c1.selectbox("Kierunek:", ["Czechy", "Słowacja"])
        term_n = c2.date_input("Termin wysyłki:", datetime.date.today() + datetime.timedelta(days=3))
        cols = st.columns(3)
        nowe_partie = []
        for i, art_id in enumerate(WYDAJNOSC.keys()):
            with cols[i % 3]:
                v = st.number_input(f"Art {art_id}", min_value=0, step=1, key=f"add_{art_id}")
                if v > 0: nowe_partie.append({"art": art_id, "ile": v, "termin": term_n, "kraj": kraj_n})
        
        if st.form_submit_button("ZATWIERDŹ"):
            st.session_state.kolejka.extend(nowe_partie)
            zapisz_dane(st.session_state.kolejka)
            st.session_state.pokaz_f = False
            st.rerun()

st.title("Konfekcja SM - Harmonogram Produkcji")

if st.session_state.kolejka:
    k_tuple = tuple(tuple(d.items()) for d in st.session_state.kolejka)
    dni, raport_surowy = generuj_plan_forward(k_tuple, datetime.date.today())

    st.subheader("🗓️ Realny Plan Produkcji")
    grid = st.columns(5)
    sorted_keys = sorted(dni.keys(), key=lambda x: datetime.datetime.strptime(x, "%d.%m"))
    
    for i, dk in enumerate(sorted_keys):
        with grid[i % 5]:
            inf = dni[dk]
            
            if inf.get("nadgodziny_w_dniu"):
                box_bg = "#fff8e1"
                box_border = "#ffb300"
                alert_dzien = "<br><span style='color:#e65100; font-weight:bold; font-size:13px;'>⚠️ WYDŁUŻONA ZMIANA</span>"
            else:
                box_bg = "white"
                box_border = "#ddd"
                alert_dzien = ""
            
            st.markdown(f"""<div style="border:2px solid {box_border}; border-radius:10px; padding:10px; background-color:{box_bg}; margin-bottom:10px;">
                <b style="color:#1f77b4; font-size:15px;">{dk} ({inf['dz']})</b>{alert_dzien}<br>
                <b style="color:green;">Suma: {inf['suma']} pal.</b><hr style="margin:5px 0; border-top:1px solid {box_border};">""", unsafe_allow_html=True)
            
            for p in inf["p"]:
                bg = "#d4edda" if p["Kraj"] == "Słowacja" else "#f8f9fa"
                border_col = "#eee"
                text_col = "#000"
                alert = ""
                
                if p.get('Nadgodziny'):
                    border_col = "#ffcc80"
                    text_col = "#e65100"
                elif datetime.datetime.strptime(p['Data'], "%d.%m").date().replace(year=datetime.date.today().year) == datetime.datetime.strptime(p['Wysyłka'], "%d.%m").date().replace(year=datetime.date.today().year) and p['Palety'] > (420 // WYDAJNOSC.get(p['Art'], 70)):
                    bg = "#ffebee" 
                    border_col = "#ffcdd2"
                    text_col = "#b71c1c"
                    alert = "<br><span style='color:red; font-weight:bold; font-size:10px;'>⚠️ BRAK MOCY W DNIU WYSYŁKI</span>"

                st.markdown(f"""<div style="background-color:{bg}; padding:5px; border-radius:5px; margin-bottom:4px; border:1px solid {border_col}; font-size:12px; color:{text_col};">
                    <b>{p['Art']}</b>: {p['Palety']} pal.{alert}<br>
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
        
    final = final[['Wysyłka', 'Kraj', 'Artykuł', 'Zamówiono (pal)', 'Zaplanowano (pal)']]
    final.columns = ['Termin Wysyłki', 'Kraj', 'Artykuł', 'Zamówiono (pal)', 'Zaplanowano (pal)']
    final['Status'] = final.apply(lambda x: "✅ OK" if x['Zamówiono (pal)'] == x['Zaplanowano (pal)'] else "❌ BŁĄD", axis=1)
    
    def style_wiersze(row):
        kolor = '#d4edda' if row['Kraj'] == 'Słowacja' else ''
        return [f'background-color: {kolor}'] * len(row)
    
    st.dataframe(final.style.apply(style_wiersze, axis=1), use_container_width=True, hide_index=True)

else:
    st.info("Brak zamówień. Dodaj je w panelu bocznym.")
