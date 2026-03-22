import streamlit as st
import datetime
import pandas as pd

# Baza wydajności (minuty na 1 paletę)
wydajnosc = {
    "232": 70, "233": 60, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Planista Produkcji", layout="wide")
st.title("🥛 Harmonogram Produkcji z Terminarzem")

if 'kolejka' not in st.session_state:
    st.session_state.kolejka = []

# --- PANEL BOCZNY: FORMULARZ ---
with st.sidebar:
    st.header("📋 Nowe Zamówienie")
    with st.form("form_zbiorczy"):
        dane_wejsciowe = []
        for art_id in wydajnosc.keys():
            c1, c2 = st.columns([1, 1.5])
            with c1:
                ile = st.number_input(f"Art {art_id}", min_value=0, step=1, value=0, key=f"n_{art_id}")
            with c2:
                termin = st.date_input(f"Termin", datetime.date.today() + datetime.timedelta(days=3), key=f"t_{art_id}")
            
            if ile > 0:
                dane_wejsciowe.append({"art": art_id, "ile": ile, "termin": termin})
        
        st.write("---")
        data_startu = st.date_input("Od kiedy zacząć produkcję?", datetime.date.today())
        submit = st.form_submit_button("✅ DODAJ DO PLANU")
        
        if submit and dane_wejsciowe:
            for poz in dane_wejsciowe:
                st.session_state.kolejka.append({
                    "art": poz["art"], "ile": poz["ile"], 
                    "start": data_startu, "termin": poz["termin"]
                })
            st.rerun()

    if st.button("🗑️ WYCZYŚĆ PLAN"):
        st.session_state.kolejka = []
        st.rerun()

# --- LOGIKA PLANOWANIA ---
if not st.session_state.kolejka:
    st.info("👈 Wpisz ilości palet i daty dostaw w panelu bocznym.")
else:
    # Poprawione: pełna nazwa zmiennej zadania
    zadania = sorted([dict(z) for z in st.session_state.kolejka], key=lambda x: (x['start'], x['termin']))
    dni_planu = {}
    limit_minut = 840 
    aktualna_data = min(z["start"] for z in zadania)
    wolny_czas = limit_minut

    raport_lista = []

    while zadania:
        d_key = aktualna_data.strftime("%Y-%m-%d")
        if d_key not in dni_planu:
            dni_planu[d_key] = {"data": aktualna_data, "produkcje": []}
        
        dostepne = [z for z in zadania if z["start"] <= aktualna_data]
        if not dostepne:
            aktualna_data += datetime.timedelta(days=1)
            wolny_czas = limit_minut
            continue
            
        z = dostepne[0]
        wyd = wydajnosc.get(z["art"], 70)
        ile_dzis = min(wolny_czas // wyd, z["ile"])
        
        if ile_dzis > 0:
            spoznienie = aktualna_data > z["termin"]
            wpis = {
                "Data produkcji": aktualna_data.strftime("%d.%m (%A)"),
                "Artykuł": z["art"],
                "Ilość [pal]": int(ile_dzis),
                "Termin dostawy": z["termin"].strftime("%d.%m"),
                "Status": "⚠️ OPÓŹNIENIE" if spoznienie else "OK"
            }
            dni_planu[d_key]["produkcje"].append(wpis)
            raport_lista.append(wpis)
            
            z["ile"] -= ile_dzis
            wolny_czas -= (ile_dzis * wyd)
        
        if z["ile"] <= 0: 
            zadania.remove(z)
            
        if wolny_czas < 52 or not dostepne:
            aktualna_data += datetime.timedelta(days=1)
            wolny_czas = limit_minut
        
        if len(dni_planu) > 100: # Bezpiecznik
            break

    # --- WIDOK HARMONOGRAMU ---
    st.subheader("🗓️ Wizualny Plan Dnia")
    cols = st.columns(4)
    for i, dk in enumerate(sorted(dni_planu.keys())):
        d = dni_planu[dk]
        with cols[i % 4]:
            ma_alert = any(p["Status"] == "⚠️ OPÓŹNIENIE" for p in d["produkcje"])
            if ma_alert:
                st.error(f"**{d['data'].strftime('%d.%m %A')}**")
            else:
                st.warning(f"**{d['data'].strftime('%d.%m %A')}**")
            
            for p in d["produkcje"]:
                st.write(f"📦 **{p['Artykuł']}**: {p['Ilość [pal]']} pal.")
                st.caption(f"➔ Termin: {p['Termin dostawy']}")

    # --- SEKCJA DRUKOWANIA ---
    st.write("---")
    st.subheader("🖨️ Raport do druku / Excela")
    if raport_lista:
        df_raport = pd.DataFrame(raport_lista)
        st.table(df_raport)
        
        csv = df_raport.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Pobierz jako CSV (Excel)",
            data=csv,
            file_name=f"plan_{datetime.date.today()}.csv",
            mime="text/csv",
        )
