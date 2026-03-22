import streamlit as st
import datetime
import pandas as pd

# 1. Dane stałe
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

st.set_page_config(page_title="Planista Produkcji", layout="wide")

if 'kolejka' not in st.session_state:
    st.session_state.kolejka = []

# --- ZOPTYMALIZOWANA LOGIKA (SZYBSZA) ---
@st.cache_data
def generuj_plan_szybki(kolejka_tuple, data_dzis):
    if not kolejka_tuple: return {}, []

    zadania = sorted([dict(z) for z in kolejka_tuple], key=lambda x: x['termin'])
    plan_dni = {}
    raport_produkcji = []
    data_kursora = data_dzis
    LIMIT = 480 # 8h

    for z in zadania:
        ile = z['ile']
        wyd = WYDAJNOSC.get(z["art"], 70)
        
        while ile > 0:
            d_key = data_kursora.strftime("%Y-%m-%d")
            if data_kursora > z['termin']: data_kursora = data_dzis
            
            if d_key not in plan_dni: plan_dni[d_key] = LIMIT
            
            wolny = plan_dni[d_key]
            if wolny >= wyd:
                produkcja = min(wolny // wyd, ile)
                if produkcja > 0:
                    raport_produkcji.append({
                        "Data": data_kursora.strftime("%d.%m"),
                        "Dzień": DNI_PL.get(data_kursora.strftime("%A")),
                        "Art": z["art"],
                        "Palety": int(produkcja),
                        "Kraj": z.get("kraj", "Czechy"),
                        "Wysyłka": z["termin"].strftime("%d.%m"),
                        "Miesiac": data_kursora.month,
                        "dt_sort": data_kursora
                    })
                    ile -= produkcja
                    plan_dni[d_key] -= (produkcja * wyd)
            
            if ile > 0: # Jeśli towar został, a zmiana pełna -> następny dzień
                data_kursora += datetime.timedelta(days=1)
                if data_kursora.weekday() == 6: data_kursora += datetime.timedelta(days=1)
            else:
                break # Zamówienie gotowe
                
    # Grupowanie
    dni_widok = {}
    for r in raport_produkcji:
        dk = r['Data']
        if dk not in dni_widok: dni_widok[dk] = {"dzien": r['Dzień'], "suma": 0, "p": []}
        dni_widok[dk]["p"].append(r)
        dni_widok[dk]["suma"] += r["Palety"]
    
    return dni_widok, raport_produkcji

# --- WIDOK ---
st.title("🥛 Planista Produkcji - Optymalizacja Zmian")

with st.sidebar:
    st.header("Zarządzanie")
    if st.button("➕ DODAJ ZAMÓWIENIE", type="primary"): st.session_state.pokaz_form = True
    if st.button("🗑️ WYCZYŚĆ WSZYSTKO"):
        st.session_state.kolejka = []
        st.cache_data.clear()
        st.rerun()

if st.session_state.get('pokaz_form'):
    with st.form("form"):
        c1, c2 = st.columns(2)
        kraj = c1.selectbox("Kraj:", ["Czechy", "Słowacja"])
        termin = c2.date_input("Wysyłka:", datetime.date.today() + datetime.timedelta(days=2))
        cols = st.columns(3)
        nowe = []
        for i, art in enumerate(WYDAJNOSC.keys()):
            with cols[i % 3]:
                v = st.number_input(f"Art {art}", min_value=0)
                if v > 0: nowe.append({"art": art, "ile": v})
        if st.form_submit_button("DODAJ"):
            for n in nowe: st.session_state.kolejka.append({"art": n['art'], "ile": n['ile'], "termin": termin, "kraj": kraj})
            st.session_state.pokaz_form = False
            st.rerun()

if st.session_state.kolejka:
    k_tuple = tuple(tuple(d.items()) for d in st.session_state.kolejka)
    dni, raport = generuj_plan_szybki(k_tuple, datetime.date.today())

    # 1. KAFELKI
    st.subheader("🗓️ Harmonogram Dzienny")
    cols = st.columns(5)
    sorted_days = sorted(dni.keys(), key=lambda x: datetime.datetime.strptime(x, "%d.%m"))
    for i, dk in enumerate(sorted_days):
        with cols[i % 5]:
            d_info = dni[dk]
            st.markdown(f"""<div style="border:1px solid #ddd; border-radius:10px; padding:10px; background-color:white;">
                <b style="color:#1f77b4;">{dk} ({d_info['dzien']})</b><br>
                <b style="color:green;">Suma: {d_info['suma']} pal.</b><hr style="margin:5px 0;">""", unsafe_allow_html=True)
            for p in d_info["p"]:
                bg = "#d4edda" if p["Kraj"] == "Słowacja" else "#f8f9fa"
                st.markdown(f"""<div style="background-color:{bg}; padding:4px; border-radius:4px; margin-bottom:4px; border:1px solid #eee; font-size:13px;">
                    <b>{p['Art']}</b>: {p['Palety']} pal.<br><small>📦 Wysyłka: {p['Wysyłka']}</small></div>""", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # 2. PODSUMOWANIE MIESIĘCZNE
    st.divider()
    st.subheader("📊 Podsumowanie Miesięczne Asortymentu")
    df = pd.DataFrame(raport)
    df["Miesiąc"] = df["Miesiac"].map(MIESIACE_PL)
    
    col_cz, col_sk = st.columns(2)
    with col_cz:
        st.write("#### 🇨🇿 CZECHY")
        df_cz = df[df["Kraj"] == "Czechy"]
        if not df_cz.empty:
            st.dataframe(df_cz.pivot_table(index="Art", columns="Miesiąc", values="Palety", aggfunc="sum", fill_value=0), use_container_width=True)
    with col_sk:
        st.write("#### 🇸🇰 SŁOWACJA")
        df_sk = df[df["Kraj"] == "Słowacja"]
        if not df_sk.empty:
            st.dataframe(df_sk.pivot_table(index="Art", columns="Miesiąc", values="Palety", aggfunc="sum", fill_value=0), use_container_width=True)
else:
    st.info("Brak zamówień.")
