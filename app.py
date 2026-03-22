import streamlit as st
import datetime
import pandas as pd

# 1. Słownik tłumaczeń dni tygodnia
DNI_PL = {
    "Monday": "Poniedziałek",
    "Tuesday": "Wtorek",
    "Wednesday": "Środa",
    "Thursday": "Czwartek",
    "Friday": "Piątek",
    "Saturday": "Sobota",
    "Sunday": "Niedziela"
}

# 2. Baza wydajności (minuty na 1 paletę)
WYDAJNOSC = {
    "232": 70, "233": 60, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Planista Produkcji", layout="wide")

if 'kolejka' not in st.session_state:
    st.session_state.kolejka = []

# --- FUNKCJA OKIENKA (DIALOG) ---
@st.dialog("📦 Dodaj Nowe Zamówienie")
def otworz_okno_zamowienia():
    st.write("Wpisz ilości palet dla artykułów:")
    
    nowe_pozycje = []
    cols = st.columns(2)
    for i, (art_id, czas) in enumerate(WYDAJNOSC.items()):
        with cols[i % 2]:
            n = st.number_input(f"Art {art_id}", min_value=0, step=1, value=0, key=f"popup_{art_id}")
            if n > 0:
                nowe_pozycje.append({"art": art_id, "ile": n})
    
    st.write("---")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        d_start = st.date_input("Start produkcji:", datetime.date.today())
    with col_d2:
        d_deadline = st.date_input("Termin (Deadline):", datetime.date.today() + datetime.timedelta(days=3))
    
    if st.button("ZATWIERDŹ I DODAJ", use_container_width=True, type="primary"):
        if nowe_pozycje:
            for p in nowe_pozycje:
                st.session_state.kolejka.append({
                    "art": p["art"], "ile": p["ile"], 
                    "start": d_start, "termin": d_deadline
                })
            st.rerun()
        else:
            st.warning("Wpisz ilość chociaż dla jednego artykułu!")

# --- GŁÓWNY INTERFEJS ---
st.title("🥛 Harmonogram Konfekcji - Mleczarnia")

c1, c2 = st.columns([1, 4])
with c1:
    if st.button("➕ NOWE ZAMÓWIENIE", use_container_width=True, type="primary"):
        otworz_okno_zamowienia()
with c2:
    if st.button("🗑️ WYCZYŚĆ WSZYSTKO", use_container_width=True):
        st.session_state.kolejka = []
        st.rerun()

# --- LOGIKA OBLICZEŃ ---
def przelicz(kolejka_raw):
    if not kolejka_raw: return {}, []
    zadania = sorted([dict(z) for z in kolejka_raw], key=lambda x: (x['start'], x['termin']))
    dni_planu, raport, LIMIT = {}, [], 840
    aktualna_data = min(z["start"] for z in zadania)
    wolny_czas = LIMIT

    while zadania:
        d_key = aktualna_data.strftime("%Y-%m-%d")
        if d_key not in dni_planu:
            # Pobieramy nazwę dnia i tłumaczymy na polski
            dzien_en = aktualna_data.strftime("%A")
            dzien_pl = DNI_PL.get(dzien_en, dzien_en)
            dni_planu[d_key] = {"data": aktualna_data, "dzien_pl": dzien_pl, "p": []}
        
        dostepne = [z for z in zadania if z["start"] <= aktualna_data]
        if not dostepne:
            aktualna_data += datetime.timedelta(days=1)
            wolny_czas = LIMIT
            continue
            
        z = dostepne[0]
        wyd = WYDAJNOSC.get(z["art"], 70)
        ile_dzis = min(wolny_czas // wyd, z["ile"])
        
        if ile_dzis > 0:
            spoznienie = aktualna_data > z["termin"]
            wpis = {
                "Data": aktualna_data.strftime("%d.%m"),
                "Dzień": dni_planu[d_key]["dzien_pl"],
                "Art": z["art"],
                "Palety": int(ile_dzis),
                "Termin": z["termin"].strftime("%d.%m"),
                "Status": "⚠️" if spoznienie else "OK"
            }
            dni_planu[d_key]["p"].append(wpis)
            raport.append(wpis)
            z["ile"] -= ile_dzis
            wolny_czas -= (ile_dzis * wyd)
        
        if z["ile"] <= 0: zadania.remove(z)
        if wolny_czas < 52 or not dostepne:
            aktualna_data += datetime.timedelta(days=1)
            wolny_czas = LIMIT
        if len(dni_planu) > 90: break
    return dni_planu, raport

# --- WIDOK ---
if st.session_state.kolejka:
    dni, rep = przelicz(st.session_state.kolejka)
    
    st.subheader("🗓️ Plan Produkcji")
    siatka = st.columns(5)
    for i, dk in enumerate(sorted(dni.keys())):
        with siatka[i % 5]:
            d_info = dni[dk]
            st.markdown(f"""
                <div style="border:1px solid #ddd; border-radius:10px; padding:10px; background-color:#f9f9f9; margin-bottom:10px;">
                    <b style="color:#007BFF; font-size:16px;">{d_info['data'].strftime('%d.%m')}</b><br>
                    <small style="color:#555;">{d_info['dzien_pl']}</small><hr style="margin:5px 0;">
            """, unsafe_allow_html=True)
            for p in d_info["p"]:
                st.write(f"**{p['Art']}**: {p['Palety']} pal.")
            st.markdown("</div>", unsafe_allow_html=True)

    st.write("---")
    st.subheader("🖨️ Tabela do wydruku")
    st.table(pd.DataFrame(rep))
else:
    st.info("Kliknij niebieski przycisk u góry, aby dodać zamówienie.")
