import streamlit as st
import datetime
import pandas as pd

# 1. Dane stałe i tłumaczenia
DNI_PL = {
    "Monday": "Poniedziałek", "Tuesday": "Wtorek", "Wednesday": "Środa",
    "Thursday": "Czwartek", "Friday": "Piątek", "Saturday": "Sobota", "Sunday": "Niedziela"
}

MIESIACE_PL = {
    1: "Styczeń", 2: "Luty", 3: "Marzec", 4: "Kwiecień", 5: "Maj", 6: "Czerwiec",
    7: "Lipiec", 8: "Sierpień", 9: "Wrzesień", 10: "Październik", 11: "Listopad", 12: "Grudzień"
}

WYDAJNOSC = {
    "232": 70, "233": 60, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Planista JIT - Priorytet Wysyłek", layout="wide")

if 'kolejka' not in st.session_state:
    st.session_state.kolejka = []

# --- LOGIKA OBLICZEŃ JIT ---
@st.cache_data
def generuj_dane_jit(kolejka_tuple, data_dzisiejsza):
    if not kolejka_tuple:
        return {}, [], pd.DataFrame()
    
    zadania = [dict(z) for z in kolejka_tuple]
    
    # KLUCZOWA ZMIANA: Sortowanie po terminie rosnąco (najpierw te, które wyjeżdżają najwcześniej)
    # Dzięki temu planista najpierw rezerwuje czas na zamówienia z wcześniejszym deadline'em.
    zadania = sorted(zadania, key=lambda x: x['termin'])
    
    limit_minut = 840
    plan_roboczy = {} 
    wyniki_produkcji = []

    for z in zadania:
        ilosc_do_zrobienia = z['ile']
        if ilosc_do_zrobienia <= 0: continue
        
        wyd = WYDAJNOSC.get(z["art"], 70)
        
        # Próba planowania wstecz: startujemy od dnia przed wysyłką
        dzien_planowania = z['termin'] - datetime.timedelta(days=1)
        if dzien_planowania < data_dzisiejsza:
            dzien_planowania = data_dzisiejsza

        while ilosc_do_zrobienia > 0:
            d_key = dzien_planowania.strftime("%Y-%m-%d")
            if d_key not in plan_roboczy:
                plan_roboczy[d_key] = limit_minut
            
            wolny_czas = plan_roboczy[d_key]
            if wolny_czas >= wyd:
                ile_dzis = min(wolny_czas // wyd, ilosc_do_zrobienia)
                wyniki_produkcji.append({
                    "data_sort": dzien_planowania,
                    "Data Produkcji": dzien_planowania.strftime("%d.%m"),
                    "Miesiac": dzien_planowania.month,
                    "Dzień": DNI_PL.get(dzien_planowania.strftime("%A")),
                    "Artykuł": z["art"],
                    "Palety": int(ile_dzis),
                    "Kraj": z.get("kraj", "Czechy"),
                    "Data Wysyłki": z["termin"].strftime("%d.%m") # Zapamiętujemy datę wysyłki dla tego wpisu
                })
                ilosc_do_zrobienia -= ile_dzis
                plan_roboczy[d_key] -= (ile_dzis * wyd)
            
            # Jeśli w danym dniu nie ma już miejsca, cofamy się o kolejny dzień (jeśli to możliwe)
            dzien_planowania -= datetime.timedelta(days=1)
            
            if dzien_planowania < data_dzisiejsza:
                # Jeśli dotarliśmy do dzisiaj i nadal brakuje palet -> PILNE (nadgodziny)
                if ilosc_do_zrobienia > 0:
                    wyniki_produkcji.append({
                        "data_sort": data_dzisiejsza,
                        "Data Produkcji": data_dzisiejsza.strftime("%d.%m"),
                        "Miesiac": data_dzisiejsza.month,
                        "Dzień": DNI_PL.get(data_dzisiejsza.strftime("%A")),
                        "Artykuł": z["art"],
                        "Palety": int(ilosc_do_zrobienia),
                        "Kraj": z.get("kraj", "Czechy"),
                        "Data Wysyłki": z["termin"].strftime("%d.%m") + " ⚠️ PILNE"
                    })
                break

    dni_wyswietl = {}
    raport_lista = sorted(wyniki_produkcji, key=lambda x: x['data_sort'])
    for r in raport_lista:
        d_key = r['Data Produkcji']
        if d_key not in dni_wyswietl:
            dni_wyswietl[d_key] = {"dzien": r['Dzień'], "suma": 0, "p": []}
        dni_wyswietl[d_key]["p"].append(r)
        dni_wyswietl[d_key]["suma"] += r["Palety"]
    
    return dni_wyswietl, raport_lista

# --- PANEL BOCZNY ---
with st.sidebar:
    st.header("⚙️ Zarządzanie")
    if st.button("➕ DODAJ NOWE ZAMÓWIENIE", type="primary", use_container_width=True):
        st.session_state.pokaz_okno = True
    
    if st.button("🗑️ WYCZYŚĆ CAŁY PLAN", use_container_width=True):
        st.session_state.kolejka = []
        st.cache_data.clear()
        st.rerun()

    st.divider()
    
    if st.session_state.kolejka:
        st.subheader("✏️ Edycja i Kraje")
        daty_wysylki = sorted(list(set([z['termin'] for z in st.session_state.kolejka])))
        
        for data in daty_wysylki:
            col_label, col_bin = st.columns([4, 1])
            col_label.markdown(f"📅 **Wysyłka {data.strftime('%d.%m')}**")
            
            if col_bin.button("🗑️", key=f"bin_{data}"):
                st.session_state.kolejka = [z for z in st.session_state.kolejka if z['termin'] != data]
                st.cache_data.clear()
                st.rerun()

            with st.expander("Szczegóły"):
                for i, item in enumerate(st.session_state.kolejka):
                    if item['termin'] == data:
                        st.write(f"--- Art: {item['art']} ---")
                        n_kraj = st.selectbox("Kraj:", ["Czechy", "Słowacja"], 
                                             index=0 if item.get('kraj') == "Czechy" else 1,
                                             key=f"kraj_e_{i}")
                        n_ile = st.number_input("Palety:", value=int(item['ile']), key=f"ile_e_{i}")
                        
                        if n_kraj != item.get('kraj') or n_ile != item['ile']:
                            st.session_state.kolejka[i]['kraj'] = n_kraj
                            st.session_state.kolejka[i]['ile'] = n_ile
                            st.cache_data.clear()
                            if st.button("Zapisz", key=f"btn_e_{i}"): st.rerun()

# --- FORMULARZ ---
if st.session_state.get('pokaz_okno'):
    with st.container():
        st.markdown("### 📝 Dodaj zamówienie")
        c1, c2 = st.columns(2)
        kraj_nowy = c1.selectbox("Kierunek:", ["Czechy", "Słowacja"])
        dt_wys = c2.date_input("Wysyłka:", datetime.date.today() + datetime.timedelta(days=3))
        
        c = st.columns(2)
        pobrane = []
        for i, art_id in enumerate(WYDAJNOSC.keys()):
            with c[i % 2]:
                val = st.number_input(f"Art {art_id}", min_value=0, key=f"n_{art_id}")
                if val > 0: pobrane.append({"art": art_id, "ile": val})
        
        if st.button("ZATWIERDŹ"):
            for p in pobrane:
                st.session_state.kolejka.append({"art": p["art"], "ile": p["ile"], "termin": dt_wys, "kraj": kraj_nowy})
            st.session_state.pokaz_okno = False
            st.rerun()

# --- WIDOK GŁÓWNY ---
st.title("🥛 Planista Produkcji JIT")

if st.session_state.kolejka:
    k_tuple = tuple(tuple(d.items()) for d in st.session_state.kolejka)
    dni, raport_surowy = generuj_dane_jit(k_tuple, datetime.date.today())
    df_full = pd.DataFrame(raport_surowy)

    # 1. HARMONOGRAM
    st.subheader("🗓️ Harmonogram Produkcji")
    siatka = st.columns(5)
    for i, dk in enumerate(sorted(dni.keys(), key=lambda x: datetime.datetime.strptime(x, "%d.%m"))):
        with siatka[i % 5]:
            info = dni[dk]
            st.markdown(f"""<div style="border:1px solid #ddd; border-radius:10px; padding:8px; background-color:#f8f9fa;">
                <b style="color:#1f77b4;">{dk}</b> ({info['dzien']})<br>
                <b>Suma: {info['suma']} pal.</b><hr style="margin:4px 0;">""", unsafe_allow_html=True)
            for p in info["p"]:
                bg = "#d4edda" if p["Kraj"] == "Słowacja" else "transparent"
                st.markdown(f"""<div style="background-color:{bg}; padding:4px 6px; border-radius:4px; margin-bottom:4px; border: 1px solid #eee;">
                    <b>{p['Artykuł']}</b>: {p['Palety']} pal. <br>
                    <small>({p['Kraj']})</small><br>
                    <span style="font-size: 11px; color: #555;">📦 Wysyłka: {p['Data Wysyłki']}</span>
                </div>""", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # 2. PODSUMOWANIE MIESIĘCZNE ODDZIELNIE
    st.divider()
    st.subheader("📊 Podsumowanie Asortymentu (Miesięcznie)")
    df_full["Miesiąc"] = df_full["Miesiac"].map(MIESIACE_PL)

    col_cz, col_sk = st.columns(2)
    
    with col_cz:
        st.markdown("#### 🇨🇿 CZECHY")
        df_cz = df_full[df_full["Kraj"] == "Czechy"]
        if not df_cz.empty:
            pivot_cz = df_cz.pivot_table(index="Artykuł", columns="Miesiąc", values="Palety", aggfunc="sum", fill_value=0)
            st.dataframe(pivot_cz, use_container_width=True)
        else:
            st.write("Brak zamówień na Czechy.")

    with col_sk:
        st.markdown("#### 🇸🇰 SŁOWACJA")
        df_sk = df_full[df_full["Kraj"] == "Słowacja"]
        if not df_sk.empty:
            pivot_sk = df_sk.pivot_table(index="Artykuł", columns="Miesiąc", values="Palety", aggfunc="sum", fill_value=0)
            st.dataframe(pivot_sk, use_container_width=True)
        else:
            st.write("Brak zamówień na Słowację.")

    # 3. WYSYŁKI
    st.divider()
    st.subheader("🚚 Szczegóły Wysyłek Dziennych")
    df_wys = df_full.groupby(["Data Wysyłki", "Kraj", "Artykuł"])["Palety"].sum().reset_index()
    for data in df_wys["Data Wysyłki"].unique():
        sum_d = df_wys[df_wys["Data Wysyłki"] == data]["Palety"].sum()
        with st.expander(f"📅 Wysyłka: {data} (Łącznie: {sum_d} pal.)"):
            st.table(df_wys[df_wys["Data Wysyłki"] == data][["Kraj", "Artykuł", "Palety"]])

else: st.info("Brak zamówień. Dodaj zamówienie w panelu bocznym.")
