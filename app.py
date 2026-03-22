import streamlit as st
import datetime
import pandas as pd

# 1. Dane stałe
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
    st.session_state.kolejka = []

# --- PLANOWANIE W PRZÓD ---
@st.cache_data
def generuj_plan_forward(kolejka_tuple, data_dzis):
    if not kolejka_tuple: return {}, []

    zadania = [dict(z) for z in kolejka_tuple]
    
    plan_dni = {}
    raport = []
    CZAS_NETTO = 840 # 2 zmiany po 7h netto (14h łącznie)
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
            if data_kursora.weekday() == 6: # Pomijamy niedziele
                data_kursora += datetime.timedelta(days=1)
                continue
                
            d_key = data_kursora.strftime("%Y-%m-%d")
            if d_key not in plan_dni:
                plan_dni[d_key] = CZAS_NETTO
                
            wolny_czas = plan_dni[d_key]
            
            # W dniu wysyłki twardy limit 1 zmiany (420 min) DLA TEGO ZAMÓWIENIA
            if data_kursora == z['termin']:
                # Dostępny czas to wolny czas, ale obcięty do max 420 (bo to tylko 1 zmiana rano)
                # Musimy też odjąć to, co ewentualnie zaplanowano już na popołudnie (inne wysyłki)
                # Dlatego po prostu sprawdzamy, czy w pierwszych 420 min. jest miejsce.
                # Uproszczenie: w dniu wysyłki dana paleta ma max 420 min do dyspozycji minus zajęte rano.
                # W systemie rezerwacji w tył to było łatwiejsze, w przód trzeba to obsłużyć ręcznie:
                zajete_dzis = CZAS_NETTO - wolny_czas
                dostepny_czas = max(0, 420 - zajete_dzis) 
            else:
                dostepny_czas = wolny_czas
                
            produkcja = min(dostepny_czas // wyd, ile)
            nadgodziny = False
            
            # --- ZMIANA: Zezwalamy na planowanie w dniu wysyłki na 1 zmianie ---
            jutro = data_kursora + datetime.timedelta(days=1)
            if jutro.weekday() == 6:
                jutro += datetime.timedelta(days=1)
                
            # Jeśli JUTRO jest po terminie wysyłki (czyli dzisiaj JEST dniem wysyłki),
            # a my nadal mamy towar do zrobienia, TO znaczy, że nawet 1 zmiana rano nie wystarczyła.
            # W takiej sytuacji musimy wrzucić to jako nadgodziny W DZIEŃ POPRZEDZAJĄCY.
            # Ale nasz kursor idzie do przodu.
            
            # Nowa logika wymuszania:
            # Jeśli data kursora to dzień PRZED wysyłką...
            jesli_kursor_to_przed_wysylka = jutro == z['termin']
            
            if jesli_kursor_to_przed_wysylka:
                # Ile czasu będziemy mieli JUTRO rano?
                d_key_jutro = jutro.strftime("%Y-%m-%d")
                czas_jutro = plan_dni.get(d_key_jutro, CZAS_NETTO)
                zajete_jutro = CZAS_NETTO - czas_jutro
                dostepne_jutro = max(0, 420 - zajete_jutro)
                
                # Ile palet zrobimy jutro rano?
                ile_zrobimy_jutro = dostepne_jutro // wyd
                
                # Jeśli po odjęciu tego co zrobimy dzisiaj ORAZ tego co zmieści się jutro rano,
                # NADAL zostaje towar, to musimy dopchać go DZISIAJ jako nadgodziny.
                if (ile - produkcja) > ile_zrobimy_jutro:
                    nadwyzka = (ile - produkcja) - ile_zrobimy_jutro
                    produkcja += nadwyzka # Dopychamy na siłę dzisiaj
                    nadgodziny = True

            # Jeśli jesteśmy w dniu wysyłki i mimo ograniczenia 420 zostaje nam towar (bo się nie cofnęliśmy/coś poszło nie tak)
            # Wrzucamy go po prostu w plan z komunikatem o braku mocy (to bezpiecznik)
            if data_kursora == z['termin'] and ile > produkcja:
                produkcja = ile # Wpychamy na dzisiaj resztę, zignorujemy brak 1 zmiany
                
            if produkcja > 0:
                raport.append({
                    "Data": data_kursora.strftime("%d.%m"),
                    "Dzień": DNI_PL.get(data_kursora.strftime("%A")),
                    "Art": z["art"],
                    "Palety": int(produkcja),
                    "Kraj": z.get("kraj", "Czechy"),
                    "Wysyłka": z["termin"].strftime("%d.%m"),
                    "dt_sort": data_kursora,
                    "Nadgodziny": nadgodziny
                })
                ile -= produkcja
                plan_dni[d_key] -= (produkcja * wyd)
                ostatni_art = z["art"]
            
            if ile > 0:
                data_kursora += datetime.timedelta(days=1)

    widok = {}
    raport = sorted(raport, key=lambda x: (x['dt_sort'], x['Art']))
    for r in raport:
        dk = r['Data']
        if dk not in widok: 
            widok[dk] = {"dz": r['Dzień'], "suma": 0, "p": []}
        widok[dk]["p"].append(r)
        widok[dk]["suma"] += r["Palety"]
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
                                st.rerun()
                            if nowa_il != z['ile']:
                                st.session_state.kolejka[i]['ile'] = nowa_il
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
            st.markdown(f"""<div style="border:1px solid #ddd; border-radius:10px; padding:10px; background-color:white; margin-bottom:10px;">
                <b style="color:#1f77b4; font-size:15px;">{dk} ({inf['dz']})</b><br>
                <b style="color:green;">Suma: {inf['suma']} pal.</b><hr style="margin:5px 0;">""", unsafe_allow_html=True)
            for p in inf["p"]:
                bg = "#d4edda" if p["Kraj"] == "Słowacja" else "#f8f9fa"
                border_col = "#eee"
                text_col = "#000"
                alert = ""
                
                if p.get('Nadgodziny'):
                    bg = "#fff3e0" 
                    border_col = "#ffcc80"
                    text_col = "#e65100"
                    alert = "<br><span style='color:#e65100; font-weight:bold; font-size:10px;'>⚠️ WYDŁUŻONA ZMIANA</span>"
                
                # Zabezpieczenie: za dużo zaplanowane na dzień wysyłki
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

    # BEZPIECZNA TABELA KONTROLNA 
    st.divider()
    st.subheader("🔍 Kontrola zgodności zamówień")
    
    df_z = pd.DataFrame(st.session_state.kolejka)
    df_z['Wysyłka'] = df_z['termin'].apply(lambda x: x.strftime("%d.%m"))
    res = df_z.groupby(['Wysyłka', 'kraj', 'art'])['ile'].sum().reset_index()
    res = res.rename(columns={'kraj': 'Kraj', 'art': 'Art', 'ile': 'Zamówiono (pal)'})
    
    if raport_surowy:
        df_r = pd.DataFrame(raport_surowy)
        res_r = df_r.groupby(['Wysyłka', 'Kraj', 'Art'])['Palety'].sum().reset_index()
        res_r = res_r.rename(columns={'Palety': 'Zaplanowano (pal)'})
        
        final = pd.merge(res, res_r, on=['Wysyłka', 'Kraj', 'Art'], how='left').fillna(0)
    else:
        final = res.copy()
        final['Zaplanowano (pal)'] = 0
        
    final = final[['Wysyłka', 'Kraj', 'Art', 'Zamówiono (pal)', 'Zaplanowano (pal)']]
    final.columns = ['Termin Wysyłki', 'Kraj', 'Artykuł', 'Zamówiono (pal)', 'Zaplanowano (pal)']
    final['Status'] = final.apply(lambda x: "✅ OK" if x['Zamówiono (pal)'] == x['Zaplanowano (pal)'] else "❌ BŁĄD", axis=1)
    
    st.table(final)

else:
    st.info("Brak zamówień. Dodaj je w panelu bocznym.")
