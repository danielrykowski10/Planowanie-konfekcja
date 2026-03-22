import streamlit as st
import datetime
import pandas as pd

# 1. Słownik tłumaczeń i baza wydajności
DNI_PL = {
    "Monday": "Poniedziałek", "Tuesday": "Wtorek", "Wednesday": "Środa",
    "Thursday": "Czwartek", "Friday": "Piątek", "Saturday": "Sobota", "Sunday": "Niedziela"
}

WYDAJNOSC = {
    "232": 70, "233": 60, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Planista JIT", layout="wide")

if 'kolejka' not in st.session_state:
    st.session_state.kolejka = []

# --- LOGIKA JIT (Just In Time) ---
@st.cache_data
def generuj_harmonogram_jit(kolejka_tuple, data_dzisiejsza):
    if not kolejka_tuple:
        return {}, pd.DataFrame()
    
    zadania = [dict(z) for z in kolejka_tuple]
    # Planujemy od najpóźniejszych terminów, żeby "dobić" do daty wysyłki
    zadania = sorted(zadania, key=lambda x: x['termin'], reverse=True)
    
    limit_minut = 840
    plan_roboczy = {} 
    wyniki_produkcji = []

    for z in zadania:
        ilosc_do_zrobienia = z['ile']
        wyd = WYDAJNOSC.get(z["art"], 70)
        # Produkcja powinna kończyć się dzień przed wysyłką
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
                    "Dzień": DNI_PL.get(dzien_planowania.strftime("%A")),
                    "Artykuł": z["art"],
                    "Palety": int(ile_dzis),
                    "Data Wysyłki": z["termin"].strftime("%d.%m")
                })
                ilosc_do_zrobienia -= ile_dzis
                plan_roboczy[d_key] -= (ile_dzis * wyd)
            
            dzien_planowania -= datetime.timedelta(days=1)
            if dzien_planowania < data_dzisiejsza:
                if ilosc_do_zrobienia > 0:
                    wyniki_produkcji.append({
                        "data_sort": data_dzisiejsza,
                        "Data Produkcji": data_dzisiejsza.strftime("%d.%m"),
                        "Dzień": DNI_PL.get(data_dzisiejsza.strftime("%A")),
                        "Artykuł": z["art"],
                        "Palety": int(ilosc_do_zrobienia),
                        "Data Wysyłki": z["termin"].strftime("%d.%m") + " ⚠️ PILNE"
                    })
                break

    # Grupowanie do kafelków
    dni_wyswietl = {}
    raport_lista = sorted(wyniki_produkcji, key=lambda x: x['data_sort'])
    for r in raport_lista:
        d_key = r['Data Produkcji']
        if d_key not in dni_wyswietl:
            dni_wyswietl[d_key] = {"dzien": r['Dzień'], "suma": 0, "p": []}
        dni_wyswietl[d_key]["p"].append(r)
        dni_wyswietl[d_key]["suma"] += r["Palety"]

    # Tabela zbiorcza wysyłek (Art vs Data Wysyłki)
    df_temp = pd.DataFrame(wyniki_produkcji)
    # Usuwamy dopisek "PILNE" do tabeli zbiorczej, żeby daty się zgadzały
    df_temp["Data Wysyłki Clean"] = df_temp["Data Wysyłki"].str.replace(" ⚠️ PILNE", "")
    tabela_zbiorcza = df_temp.pivot_table(
        index="Artykuł", 
        columns="Data Wysyłki Clean", 
        values="Palety", 
        aggfunc="sum", 
        fill_value=0,
        margins=True, # Dodaje sumowanie końcowe
        margins_name="SUMA"
    )
    
    return dni_wyswietl, tabela_zbiorcza

# --- PASEK BOCZNY ---
with st.sidebar:
    st.header("⚙️ Opcje")
    if st.button("➕ DODAJ ZAMÓWIENIE", type="primary", use_container_width=True):
        st.session_state.pokaz_okno = True
    
    st.divider()
    st.subheader("📦 Kolejka w pamięci")
    for i, item in enumerate(st.session_state.kolejka):
        c_t, c_d = st.columns([4, 1])
        c_t.write(f"**{item['art']}** ({item['ile']} pal.)\n→ {item['termin'].strftime('%d.%m')}")
        if c_d.button("❌", key=f"del_{i}"):
            st.session_state.kolejka.pop(i)
            st.rerun()
    
    if st.button("🗑️ WYCZYŚĆ WSZYSTKO", use_container_width=True):
        st.session_state.kolejka = []
        st.rerun()

# Okno wprowadzania danych
if st.session_state.get('pokaz_okno'):
    with st.expander("📝 Formularz zamówienia", expanded=True):
        cols = st.columns(2)
        pobrane = []
        for i, art_id in enumerate(WYDAJNOSC.keys()):
            with cols[i % 2]:
                val = st.number_input(f"Art {art_id}", min_value=0, step=1, key=f"v_{art_id}")
                if val > 0: pobrane.append({"art": art_id, "ile": val})
        
        dt_wys = st.date_input("Data wysyłki (Termin):", datetime.date.today() + datetime.timedelta(days=3))
        
        if st.button("ZATWIERDŹ"):
            for p in pobrane:
                st.session_state.kolejka.append({"art": p["art"], "ile": p["ile"], "termin": dt_wys})
            st.session_state.pokaz_okno = False
            st.rerun()

# --- WIDOK GŁÓWNY ---
st.title("🥛 Planista Produkcji JIT")

if st.session_state.kolejka:
    k_tuple = tuple(tuple(d.items()) for d in st.session_state.kolejka)
    dni, zbiorcza = generuj_harmonogram_jit(k_tuple, datetime.date.today())
    
    # 1. HARMONOGRAM (Góra)
    st.subheader("🗓️ Harmonogram Produkcji (Kiedy robić)")
    siatka = st.columns(5)
    for i, d_key in enumerate(sorted(dni.keys(), key=lambda x: datetime.datetime.strptime(x, "%d.%m"))):
        with siatka[i % 5]:
            info = dni[d_key]
            st.markdown(f"""
                <div style="border:1px solid #ddd; border-radius:10px; padding:10px; background-color:#ffffff; margin-bottom:10px;">
                    <b style="color:#1f77b4; font-size:16px;">{d_key} ({info['dzien']})</b><br>
                    <span style="color:#28a745; font-weight:bold;">Suma: {info['suma']} pal.</span><hr style="margin:5px 0;">
            """, unsafe_allow_html=True)
            for p in info["p"]:
                st.write(f"**{p['Artykuł']}**: {p['Palety']} pal.")
                st.caption(f"Cel wysyłki: {p['Data Wysyłki']}")
            st.markdown("</div>", unsafe_allow_html=True)

    # 2. PODSUMOWANIE WYSYŁEK (Dół)
    st.divider()
    st.subheader("📊 Podsumowanie Wysyłek (Ile palet na jaki dzień)")
    st.write("Tabela pokazuje łączną ilość towaru, która musi wyjechać z zakładu w danych dniach.")
    st.dataframe(zbiorcza, use_container_width=True)
    
    st.info("💡 Aby wydrukować harmonogram, użyj Ctrl+P i wybierz opcję 'Drukuj tylko wybraną treść' lub wydrukuj całą stronę.")
else:
    st.info("Dodaj pierwsze zamówienie, aby wygenerować plan.")
