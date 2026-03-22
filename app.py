import streamlit as st
import datetime
import pandas as pd

# 1. Dane podstawowe
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

st.set_page_config(page_title="Planista JIT - Zmiany 9/12h", layout="wide")

if 'kolejka' not in st.session_state:
    st.session_state.kolejka = []

# --- LOGIKA PLANOWANIA ---
@st.cache_data
def generuj_plan_jit(kolejka_tuple, data_dzis):
    if not kolejka_tuple: return {}, []
    
    zadania = [dict(z) for z in kolejka_tuple]
    # Sortowanie pod minimalizację przejść (wg terminu i art)
    zadania = sorted(zadania, key=lambda x: (x['termin'], x['art']), reverse=True)
    
    NORMA_9H = 540
    plan_roboczy = {} 
    raport_produkcji = []

    for z in zadania:
        do_zrobienia = z['ile']
        wyd = WYDAJNOSC.get(z["art"], 70)
        
        # Planowanie wstecz od daty wysyłki
        dzien = z['termin'] - datetime.timedelta(days=1)
        if dzien < data_dzis: dzien = data_dzis

        while do_zrobienia > 0:
            d_key = dzien.strftime("%Y-%m-%d")
            if d_key not in plan_roboczy: plan_roboczy[d_key] = NORMA_9H
            
            wolny_czas = plan_roboczy[d_key]
            
            if wolny_czas >= wyd:
                ile_dzis = min(wolny_czas // wyd, do_zrobienia)
                raport_produkcji.append({
                    "data_sort": dzien,
                    "Data": dzien.strftime("%d.%m"),
                    "Art": z["art"],
                    "Palety": int(ile_dzis),
                    "Kraj": z.get("kraj", "Czechy"),
                    "Typ": "9H"
                })
                do_zrobienia -= ile_dzis
                plan_roboczy[d_key] -= (ile_dzis * wyd)
            
            # Jeśli to data dzisiejsza i nadal mamy towar -> wrzucamy w nadgodziny
            if dzien <= data_dzis and do_zrobienia > 0:
                raport_produkcji.append({
                    "data_sort": data_dzis,
                    "Data": data_dzis.strftime("%d.%m"),
                    "Art": z["art"],
                    "Palety": int(do_zrobienia),
                    "Kraj": z.get("kraj", "Czechy"),
                    "Typ": "PONAD_9H"
                })
                do_zrobienia = 0
            
            dzien -= datetime.timedelta(days=1)

    # Grupowanie wyników
    dni_widok = {}
    raport_lista = sorted(raport_produkcji, key=lambda x: (x['data_sort'], x['Art']))
    
    for r in raport_lista:
        dk = r['Data']
        if dk not in dni_widok:
            dni_widok[dk] = {"suma": 0, "p": [], "czy_12h": False, "dzien_pl": DNI_PL.get(r['data_sort'].strftime("%A"))}
        dni_widok[dk]["p"].append(r)
        dni_widok[dk]["suma"] += r["Palety"]
        if r["Typ"] == "PONAD_9H": dni_widok[dk]["czy_12h"] = True
    
    return dni_widok, raport_lista

# --- INTERFEJS ---
st.title("🥛 Planista Produkcji - Optymalizacja Pracy")

with st.sidebar:
    st.header("Zarządzanie")
    if st.button("➕ DODAJ ZAMÓWIENIE", type="primary"): st.session_state.show_form = True
    if st.button("🗑️ WYCZYŚĆ PLAN"):
        st.session_state.kolejka = []
        st.rerun()
    st.divider()
    # Edycja
    if st.session_state.kolejka:
        st.subheader("Edycja")
        daty_w = sorted(list(set([z['termin'] for z in st.session_state.kolejka])))
        for d in daty_w:
            with st.expander(f"Wysyłka {d.strftime('%d.%m')}"):
                if st.button("Usuń", key=f"btn_{d}"):
                    st.session_state.kolejka = [z for z in st.session_state.kolejka if z['termin'] != d]
                    st.rerun()

if st.session_state.get('show_form'):
    with st.form("new_order"):
        c1, c2 = st.columns(2)
        kraj = c1.selectbox("Kierunek:", ["Czechy", "Słowacja"])
        termin = c2.date_input("Data wysyłki:", datetime.date.today() + datetime.timedelta(days=2))
        st.write("Ilości palet:")
        cols = st.columns(3)
        nowe = []
        for i, art in enumerate(WYDAJNOSC.keys()):
            with cols[i % 3]:
                v = st.number_input(f"Art {art}", min_value=0, key=f"in_{art}")
                if v > 0: nowe.append({"art": art, "ile": v})
        if st.form_submit_button("DODAJ"):
            for n in nowe: st.session_state.kolejka.append({"art": n['art'], "ile": n['ile'], "termin": termin, "kraj": kraj})
            st.session_state.show_form = False
            st.rerun()

# --- WIDOK ---
if st.session_state.kolejka:
    k_tuple = tuple(tuple(d.items()) for d in st.session_state.kolejka)
    dni, raport = generuj_plan_jit(k_tuple, datetime.date.today())
    
    st.subheader("🗓️ Harmonogram Dzienny")
    cols = st.columns(5)
    for i, dk in enumerate(sorted(dni.keys(), key=lambda x: datetime.datetime.strptime(x, "%d.%m"))):
        with cols[i % 5]:
            d_info = dni[dk]
            label_zmiana = "⚠️ ZMIANA 12H" if d_info["czy_12h"] else "✅ ZMIANA 9H"
            kolor_ramki = "#ff4b4b" if d_info["czy_12h"] else "#ddd"
            
            st.markdown(f"""
                <div style="border:2px solid {kolor_ramki}; border-radius:10px; padding:10px; background-color:white; margin-bottom:10px;">
                    <b style="font-size:18px;">{dk}</b> <small>{d_info['dzien_pl']}</small><br>
                    <span style="color:{'red' if d_info['czy_12h'] else 'green'}; font-weight:bold;">{label_zmiana}</span><br>
                    <b>Suma: {d_info['suma']} pal.</b><hr style="margin:5px 0;">
            """, unsafe_allow_html=True)
            
            for p in d_info["p"]:
                style = "background-color:#d4edda;" if p["Kraj"] == "Słowacja" else ""
                alert = " <span style='color:red; font-size:11px;'>!</span>" if p["Typ"] == "PONAD_9H" else ""
                st.markdown(f"<div style='{style} padding:2px; border-radius:3px;'><b>{p['Art']}</b>: {p['Palety']} pal.{alert}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # Statystyki na dole
    st.divider()
    df = pd.DataFrame(raport)
    df["Miesiąc"] = df["Miesiac"].map(MIESIACE_PL)
    c_cz, c_sk = st.columns(2)
    with c_cz:
        st.write("#### 🇨🇿 CZECHY")
        df_cz = df[df["Kraj"] == "Czechy"]
        if not df_cz.empty: st.dataframe(df_cz.pivot_table(index="Art", columns="Miesiąc", values="Palety", aggfunc="sum", fill_value=0), use_container_width=True)
    with c_sk:
        st.write("#### 🇸🇰 SŁOWACJA")
        df_sk = df[df["Kraj"] == "Słowacja"]
        if not df_sk.empty: st.dataframe(df_sk.pivot_table(index="Art", columns="Miesiąc", values="Palety", aggfunc="sum", fill_value=0), use_container_width=True)

else:
    st.info("Dodaj zamówienie, aby zobaczyć plan.")
