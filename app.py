import streamlit as st
import datetime
import pandas as pd

# 1. Baza wydajności (minuty na 1 paletę)
WYDAJNOSC = {
    "232": 70, "233": 60, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Planista Produkcji", layout="wide")

# Inicjalizacja kolejki
if 'kolejka' not in st.session_state:
    st.session_state.kolejka = []

# --- FUNKCJA OKIENKA (DIALOG) ---
@st.dialog("📦 Dodaj Nowe Zamówienie")
def otworz_okno_zamowienia():
    st.write("Wpisz ilości palet dla artykułów:")
    
    with st.container():
        nowe_pozycje = []
        cols = st.columns(2)
        for i, (art_id, czas) in enumerate(WYDAJNOSC.items()):
            with cols[i % 2]:
                n = st.number_input(f"Art {art_id}", min_value=0, step=1, value=0)
                if n > 0:
                    nowe_pozycje.append({"art": art_id, "ile": n})
        
        st.write("---")
        d_start = st.date_input("Kiedy zacząć produkcję?", datetime.date.today())
        d_deadline = st.date_input("Termin dostawy (Deadline):", datetime.date.today() + datetime.timedelta(days=3))
        
        if st.button("ZATWIERDŹ I DODAJ DO PLANU", use_container_width=True):
            if nowe_pozycje:
                for p in nowe_pozycje:
                    st.session_state.kolejka.append({
                        "art": p["art"], "ile": p["ile"], 
                        "start": d_start, "termin": d_deadline
                    })
                st.success("Dodano do kolejki!")
                st.rerun()
            else:
                st.warning("Nie wpisano żadnych ilości!")

# --- GŁÓWNY INTERFEJS ---
st.title("🥛 Inteligentny Harmonogram Produkcji")

col_btns1, col_btns2 = st.columns([1, 4])
with col_btns1:
    if st.button("➕ NOWE ZAMÓWIENIE", type="primary", use_container_width=True):
        otworz_okno_zamowienia()
with col_btns2:
    if st.button("🗑️ WYCZYŚĆ WSZYSTKO", use_container_width=True):
        st.session_state.kolejka = []
        st.rerun()

# --- OBLICZENIA ---
def przelicz(kolejka_raw):
    if not kolejka_raw: return {}, []
    zadania = sorted([dict(z) for z in kolejka_raw], key=lambda x: (x['start'], x['termin']))
    dni_planu, raport, LIMIT = {}, [], 840
    aktualna_data = min(z["start"] for z in zadania)
    wolny_czas = LIMIT

    while zadania:
        d_key = aktualna_data.strftime("%Y-%m-%d")
        if d_key not in dni_planu: dni_planu[d_key] = {"data": aktualna_data, "p": []}
        
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
            wpis = {"Data": aktualna_data.strftime("%d.%m"), "Art": z["art"], "Palety": int(ile_dzis), "Termin": z["termin"].strftime("%d.%m"), "Status": "⚠️" if spoznienie else "OK"}
            dni_planu[d_key]["p"].append(wpis)
            raport.append(wpis)
            z["ile"] -= ile_dzis
            wolny_czas -= (ile_dzis * wyd)
        
        if z["ile"] <= 0: zadania.remove(z)
        if wolny_czas < 52 or not dostepne:
            aktualna_data += datetime.timedelta(days=1)
            wolny_czas = LIMIT
        if len(dni_planu) > 100: break
    return dni_planu, raport

# --- WIDOK ---
if st.session_state.kolejka:
    dni, rep = przelicz(st.session_state.kolejka)
    
    st.subheader("🗓️ Plan Dzienny")
    siatka = st.columns(5)
    for i, dk in enumerate(sorted(dni.keys())):
        with siatka[i % 5]:
            d_info = dni[dk]
            st.markdown(f"""
                <div style="border:1px solid #ddd; border-radius:10px; padding:10px; background-color:#f9f9f9; margin-bottom:10px;">
                    <b style="color:#007BFF;">{d_info['data'].strftime('%d.%m %A')}</b><hr style="margin:5px 0;">
            """, unsafe_allow_html=True)
            for p in d_info["p"]:
                st.write(f"**{p['Art']}**: {p['Palety']} pal.")
            st.markdown("</div>", unsafe_allow_html=True)

    st.write("---")
    st.subheader("🖨️ Tabela do druku")
    st.table(pd.DataFrame(rep))
else:
    st.info("Kliknij niebieski przycisk 'NOWE ZAMÓWIENIE', aby rozpocząć planowanie.")
