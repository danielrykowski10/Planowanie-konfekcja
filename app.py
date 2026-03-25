import streamlit as st
import datetime
import pandas as pd
import json
import os

# --- KONFIGURACJA ---
# Plik bazy danych
PLIK_DANYCH = "dane_zamowien.json"
st.set_page_config(page_title="Konfekcja SM - System Planowania", layout="wide")

# --- PARAMETRY ---
WYDAJNOSC = {"232": 84, "233": 56, "236": 84, "261": 84, "246": 84, "254": 52.5, "1221217": 120, "1221070": 52.5, "1221181": 210}
DNI_PL = {"Monday": "Pon", "Tuesday": "Wt", "Wednesday": "Śr", "Thursday": "Czw", "Friday": "Pt", "Saturday": "Sob", "Sunday": "Nd"}
CZAS_ZMIANY = 420  # Minuty

# --- STYLIZACJA CSS ---
st.markdown("""
    <style>
    /* Global bold text for all planned harmonogram content - Fix Point 2 */
    .stMarkdown p { font-weight: bold; }
    
    .karta-dnia {
        border: 2px solid #2E7D32;
        border-radius: 12px;
        padding: 12px;
        background-color: white;
        margin-bottom: 20px;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.1);
    }
    .karta-naglowek {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #EEE;
        padding-bottom: 8px;
        margin-bottom: 12px;
    }
    
    /* Sage green row background for Słowacja within planned cards - Fix Point 3 */
    .slowacja-planned-row {
        background-color: #C8E6C9; /* Light Sage Green to fitting aesthetic */
        border: 1px solid #2E7D32;
        border-radius: 6px;
        padding: 8px;
        margin-bottom: 8px;
    }
    
    .other-planned-row {
        background-color: #F1F1F1;
        border: 1px solid #CCC;
        border-radius: 6px;
        padding: 8px;
        margin-bottom: 8px;
    }
    
    /* Style for simplified Queue Viewer to address Point 1 */
    [data-testid="stDataEditor"] [data-testid="stDataEditor-Col"] {
        max-width: 150px; /* Simplified display, explicitly removing dynammic product columns pointing to empty space */
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

# --- LOGIKA PLANOWANIA (Kopiowana, nie zmieniana) ---
def generuj_plan(kolejka):
    if not kolejka: return {}
    raport, plan_dni, MAX_CZAS = [], {}, 840
    data_dzis = datetime.date.today()
    zadania = [dict(z) for z in kolejka]
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
            dostepny = wolny_czas if data_k != z['termin'] else max(0, 420 - (MAX_CZAS - wolny_czas))
            produkcja = min(dostepny // wyd, ile)
            is_nadgodziny = False
            if data_k == z['termin'] and ile > produkcja:
                produkcja = ile
                is_nadgodziny = True
            if produkcja > 0:
                raport.append({"Data": data_k.strftime("%d.%m"), "Art": z["art"], "Palety": produkcja, "Kraj": z["kraj"], "Wysyłka": z["termin"].strftime("%d.%m"), "nad": is_nadgodziny, "dz": DNI_PL.get(data_k.strftime("%A")), "dt_s": data_k})
                ile -= produkcja
                plan_dni[d_key] -= (produkcja * wyd)
                if ile > 0: plan_dni[d_key] = 0
            if ile > 0: data_k += datetime.timedelta(days=1)
    
    widok = {}
    raport_raw = sorted(raport, key=lambda x: x['dt_s'])
    for r in raport_raw:
        dk = r['Data']
        if dk not in widok: widok[dk] = {"dz": r['dz'], "p": [], "suma": 0, "czas_suma": 0, "ma_nad": False}
        widok[dk]["p"].append(r)
        widok[dk]["suma"] += r["Palety"]
        widok[dk]["czas_suma"] += r["Palety"] * WYDAJNOSC.get(r["Art"], 70)
        if r["nad"]: widok[dk]["ma_nad"] = True
    return widok, raport_raw

# --- INICJALIZACJA SESJI ---
if 'kolejka' not in st.session_state:
    st.session_state.kolejka = wczytaj_dane()

# --- GŁÓWNY PANEL UI ---
t1, t2 = st.tabs(["📥 WPISYWANIE ZAMÓWIEŃ", "📋 HARMONOGRAM NA GOTOWO"])

# OKNO 1: WPISYWANIE
with t1:
    st.subheader("Nowe Zamówienia")
    with st.form("entry_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        f_kraj = c1.selectbox("Kierunek auto", ["Czechy", "Słowacja"])
        f_start = c2.date_input("Kiedy można zacząć produkcję?", datetime.date.today())
        f_wysylka = c3.date_input("Termin wyjazdu auta (Wysyłka)", datetime.date.today() + datetime.timedelta(days=3))
        st.write("Wpisz ilość palet dla artykułu:")
        temp_list = []
        cols = st.columns(5)
        
        # entry form needs explicit product ID
        for i, (art_id, wyd) in enumerate(WYDAJNOSC.items()):
            with cols[i % 5]:
                val = st.number_input(f"Art {art_id} ({wyd} min/pal)", min_value=0, step=1, key=f"inp_{art_id}")
                if val > 0:
                    temp_list.append({"kraj": f_kraj, "art": art_id, "ile": val, "termin": f_wysylka, "start_produkcji": f_start})
        
        if st.form_submit_button("ZAPISZ DO KOLEJKI (Generuj Plan)"):
            st.session_state.kolejka.extend(temp_list)
            zapisz_dane(st.session_state.kolejka)
            st.rerun()

    # OKNO 1 Queue Viewer section - FIX POINT 1 (Remove product dynamism in viewer)
    st.divider()
    st.subheader("Kolejka (Edytuj bezpośrednio)")
    if st.session_state.kolejka:
        # Construct DataFrame explicitely listing ID and Quantity per row
        df_display_base = []
        for z in st.session_state.kolejka:
            # Check for existing article ID structure vs dynamic structure from Point 1 image
            if 'art' in z and 'ile' in z:
                # This is a good standard record with explicit article ID and Quantity
                df_display_base.append({"kraj": z["kraj"], "art": z["art"], "ile": z["ile"], "termin": z["termin"], "start_produkcji": z["start_produkcji"]})
            else:
                # Dynamic record type pointed to in Image 1 -> Optimize display
                for art_id in WYDAJNOSC.keys():
                    if z.get(art_id, 0) > 0:
                         df_display_base.append({"kraj": z["kraj"], "art": art_id, "ile": z[art_id], "termin": z["termin"], "start_produkcji": z["start_produkcji"]})
        
        # Build DataFrame with Kraj, Art, Ile, Start Produkcji, Termin
        df_edit = pd.DataFrame(df_display_base)
        # Show structured view in Tab 1, only Kraj and Quantity are editable. Start Date and End Date is viewable.
        edited_df = st.data_editor(df_edit, use_container_width=True, hide_index=True)

        if st.button("USUŃ WSZYSTKIE POZYCJE Z KOLEJKI"):
            st.session_state.kolejka = []
            zapisz_dane([])
            st.rerun()

# OKNO 2: HARMONOGRAM NA GOTOWO
with t2:
    if not st.session_state.kolejka:
        st.info("Kolejka jest pusta. Wpisz zamówienia w zakładce 📥.")
    else:
        st.subheader("Harmonogram Produkcji (Rozpiska na halę)")
        dni_plan, raport_raw = generuj_plan(st.session_state.kolejka)
        
        # Widok kart planu - FIX POINT 2 (Bold text) & FIX POINT 3 (Green background for Słowacja rows)
        if not dni_plan:
             st.warning("Brak planu do wyświetlenia. Sprawdź terminy zamówień.")
        else:
            dni_posortowane = sorted(dni_plan.keys(), key=lambda x: datetime.datetime.strptime(x, "%d.%m"))
            grid = st.columns(5)
            for i, dk in enumerate(dni_posortowane):
                with grid[i % 5]:
                    d_info = dni_plan[dk]
                    nadgodziny_txt = " ⚠️ NADGODZINY ZAMÓWIEŃ" if d_info["ma_nad"] else ""
                    
                    st.markdown(f'<div class="karta-dnia">', unsafe_allow_html=True)
                    st.markdown(f'<div class="karta-naglowek"><b><span style="color:#2E7D32; font-size:18px;">{dk} ({d_info["dz"]})</span></b> <span style="font-size:12px;">Suma: <b>{int(d_info["suma"])} palet</b></span></div>', unsafe_allow_html=True)
                    
                    # Wnętrze karty (artykuły) - FIX Point 2 & 3 inside HTML
                    for p in d_info['p']:
                        # Fix Point 3: Clearly Sage Green background for Słowacja within cards
                        row_class = "slowacja-planned-row" if p['Kraj'] == "Słowacja" else "other-planned-row"
                        
                        # Apply bolder style explicitely inside internal row structure (Point 2)
                        st.markdown(f"""
                        <div class="{row_class}">
                            Art <b>{p['Art']}</b> -- <b>{int(p['Palety'])} pal.</b><br>
                            Auto: {p['Wysyłka']} ({p['Kraj']})
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Czas pracy na dole karty
                    cz = "2 zmiany" if d_info["czas_suma"] > 420 else "1 zmiana"
                    czas_style = "color:#E65100; font-weight:bold;" if d_info["ma_nad"] or d_info["czas_suma"] > 840 else ""
                    st.markdown(f'<div style="border-top:1px solid #EEE; padding-top:8px; margin-top:8px; font-size:13px;{czas_style}">{cz}{nadgodziny_txt}</div>', unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)

        st.divider()
        st.subheader("Lista Zbiorcza (Raw Data Viewer)")
        df_final = pd.DataFrame(raport_raw)
        if not df_final.empty:
            #Simplified static view in Tab 2
            st.dataframe(df_final[['Data', 'Art', 'Palety', 'Kraj', 'Wysyłka']], use_container_width=True, hide_index=True)
