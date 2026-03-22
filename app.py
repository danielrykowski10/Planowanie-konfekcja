import streamlit as st
import datetime
import pandas as pd

# 1. Słownik tłumaczeń dni tygodnia
DNI_PL = {
    "Monday": "Poniedziałek", "Tuesday": "Wtorek", "Wednesday": "Środa",
    "Thursday": "Czwartek", "Friday": "Piątek", "Saturday": "Sobota", "Sunday": "Niedziela"
}

# 2. Baza wydajności
WYDAJNOSC = {
    "232": 70, "233": 60, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Planista Produkcji PRO", layout="wide")

if 'kolejka' not in st.session_state:
    st.session_state.kolejka = []

# --- SZYBKA LOGIKA OBLICZENIOWA ---
@st.cache_data
def generuj_harmonogram(kolejka_tuple):
    if not kolejka_tuple:
        return {}, []
    
    zadania = [dict(z) for z in kolejka_tuple]
    zadania = sorted(zadania, key=lambda x: (x['start'], x['termin']))
    
    dni_planu = {}
    LIMIT_MINUT = 840  # 14h
    aktualna_data = min(z["start"] for z in zadania)
    wolny_czas = LIMIT_MINUT
    raport = []

    while zadania:
        d_key = aktualna_data.strftime("%Y-%m-%d")
        if d_key not in dni_planu:
            dzien_en = aktualna_data.strftime("%A")
            dni_planu[d_key] = {
                "data": aktualna_data, 
                "dzien_pl": DNI_PL.get(dzien_en, dzien_en), 
                "p": [],
                "suma_palet": 0
            }
        
        dostepne = [z for z in zadania if z["start"] <= aktualna_data]
        
        if not dostepne:
            aktualna_data += datetime.timedelta(days=1)
            wolny_czas = LIMIT_MINUT
            continue
            
        z = dostepne[0]
        wyd = WYDAJNOSC.get(z["art"], 70)
        ile_dzis = min(wolny_czas // wyd, z["ile"])
        
        if ile_dzis > 0:
            spoznienie = aktualna_data > z["termin"]
            wpis = {
                "Data": aktualna_data.strftime("%d.%m"),
                "Dzień": dni_planu[d_key]["dzien_pl"],
                "Artykuł": z["art"],
                "Palety": int(ile_dzis),
                "Termin": z["termin"].strftime("%d.%m"),
                "Opóźnienie": "TAK" if spoznienie else "NIE"
            }
            dni_planu[d_key]["p"].append(wpis)
            dni_planu[d_key]["suma_palet"] += int(ile_dzis)
            raport.append(wpis)
            z["ile"] -= ile_dzis
            wolny_czas -= (ile_dzis * wyd)
        
        if z["ile"] <= 0:
            zadania.remove(z)
            
        if wolny_czas < 52 or not dostepne:
            aktualna_data += datetime.timedelta(days=1)
            wolny_czas = LIMIT_MINUT
            
        if len(dni_planu) > 120: break
        
    return dni_planu, raport

# --- OKNO DIALOGOWE ---
@st.dialog("➕ Dodaj Zamówienie")
def okno_dodawania():
    st.write("Wpisz ilości palet:")
    nowe = []
    cols = st.columns(2)
    for i, art_id in enumerate(WYDAJNOSC.keys()):
        with cols[i % 2]:
            n = st.number_input(f"Art {art_id}", min_value=0, step=1, key=f"p_{art_id}")
            if n > 0:
                nowe.append({"art": art_id, "ile": n})
    
    st.divider()
    c1, c2 = st.columns(2)
    ds = c1.date_input("Start produkcji:", datetime.date.today())
    dt = c2.date_input("Termin dostawy:", datetime.date.today() + datetime.timedelta(days=2))
    
    if st.button("ZATWIERDŹ", use_container_width=True, type="primary"):
        if nowe:
            # Poprawione wcięcie - teraz pętla jest wewnątrz bloku 'if'
            for item in nowe:
                st.session_state.kolejka.append({
                    "art": item["art"], 
                    "ile": item["ile"], 
                    "start": ds, 
                    "termin": dt
                })
            st.rerun()
        else:
            st.error("Musisz wpisać przynajmniej jedną ilość!")

# --- INTERFEJS GŁÓWNY ---
st.title("🥛 Planista Produkcji v6")

col1, col2 = st.columns([1, 4])
if col1.button("➕ NOWE ZAMÓWIENIE", use_container_width=True, type="primary"):
    okno_dodawania()
if col2.button("🗑️ WYCZYŚĆ WSZYSTKO"):
    st.session_state.kolejka = []
    st.cache_data.clear()
    st.rerun()

if st.session_state.kolejka:
    k_tuple = tuple(tuple(d.items()) for d in st.session_state.kolejka)
    dni, raport_dane = generuj_harmonogram(k_tuple)
    
    st.subheader("🗓️ Widok Harmonogramu")
    siatka = st.columns(5)
    for i, dk in enumerate(sorted(dni.keys())):
        with siatka[i % 5]:
            d_info = dni[dk]
            st.markdown(f"""
                <div style="border:1px solid #ddd; border-radius:10px; padding:10px; background-color:#fff;">
                    <b style="font-size:16px;">{d_info['data'].strftime('%d.%m')}</b> ({d_info['dzien_pl']})<br>
                    <span style="color:blue; font-weight:bold;">Łącznie: {d_info['suma_palet']} pal.</span>
                    <hr style="margin:5px 0;">
            """, unsafe_allow_html=True)
            for p in d_info["p"]:
                st.write(f"**{p['Artykuł']}**: {p['Palety']} pal.")
            st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    st.subheader("🖨️ Raport końcowy")
    df = pd.DataFrame(raport_dane)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 Pobierz raport CSV", data=csv, file_name="harmonogram.csv", mime="text/csv")
else:
    st.info("Brak zamówień. Kliknij przycisk powyżej, aby dodać dane.")
