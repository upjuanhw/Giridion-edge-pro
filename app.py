import io
import math
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Gridiron Edge Pro", page_icon="🏈", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
.stApp {background: #0b1220; color: #e7edf7;}
[data-testid="stSidebar"] {background: #111d31;}
.block-container {padding-top: 1.6rem; max-width: 1500px;}
h1,h2,h3 {letter-spacing:-.03em;}
div[data-testid="stMetric"] {background:#17253b;border:1px solid #30445f;border-radius:14px;padding:14px;}
div[data-testid="stMetricLabel"] {color:#b8c8df;}
.stButton button {border-radius:12px;}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🏈 GRIDIRON EDGE")
    st.caption("PRO • NFL / NCAA")
    league = st.radio("Liga", ["NFL", "NCAAF"], horizontal=True)
    section = st.radio("Panel", ["Resumen", "Analizador EV", "Monte Carlo", "Cuotas CSV", "Estado del sistema"])
    st.divider()
    st.caption("Versión beta • Datos no conectados en tiempo real")

st.title("Gridiron Edge Pro")
st.caption(f"{league}  /  Análisis cuantitativo  /  Sin señales automáticas de apuestas")
st.warning("Las cuotas y probabilidades deben verificarse. No hay conexión oficial a Caliente ni modelo entrenado con históricos validado.", icon="⚠️")

def decimal_odds(american):
    return 1 + american/100 if american > 0 else 1 + 100/abs(american) if american < 0 else None

def money(amt):
    return f"${amt:,.2f} MXN"

if section == "Resumen":
    a,b,c,d = st.columns(4)
    a.metric("Ligas", "2", "NFL + NCAAF")
    b.metric("Calculadora EV", "Activa")
    c.metric("Simulador", "Disponible")
    d.metric("Momios en vivo", "Pendiente")
    st.subheader("Centro de análisis")
    st.write("Analiza la probabilidad de equilibrio de cada momio, calcula valor esperado y simula marcadores con supuestos transparentes. Importa tus propias líneas en CSV.")
    st.info("Esta versión no emite picks calibrados ni simula acceso en tiempo real a casas de apuestas.")

elif section == "Analizador EV":
    st.subheader("Valor esperado y exposición")
    x,y,z = st.columns(3)
    with x: odds = st.number_input("Momio americano", value=150, step=10, help="Ejemplo: +150 o -110")
    with y: probability = st.number_input("Probabilidad estimada (%)", min_value=0.0, max_value=100.0, value=45.0, step=0.5)
    with z: stake = st.number_input("Apuesta (MXN)", min_value=0.0, value=500.0, step=100.0)
    bankroll = st.number_input("Bankroll total (MXN)", min_value=1.0, value=30000.0, step=500.0)
    dec = decimal_odds(odds)
    if dec is None:
        st.error("El momio americano no puede ser cero.")
    else:
        p = probability / 100
        breakeven = 1 / dec
        ev_unit = p * (dec-1) - (1-p)
        full_kelly = max(0.0, (p*dec-1)/(dec-1))
        a,b,c,d = st.columns(4)
        a.metric("Prob. de equilibrio", f"{breakeven*100:.1f}%")
        b.metric("EV por $100", money(100*ev_unit))
        c.metric("EV de la apuesta", money(stake*ev_unit))
        d.metric("Kelly ¼ (teórico)", f"{full_kelly*25:.2f}%")
        st.progress(min(1.0, stake/bankroll), text=f"Exposición del bankroll: {stake/bankroll*100:.2f}%")
        st.caption("Kelly supone una probabilidad bien calibrada; no debe utilizarse como recomendación de apuesta cuando la probabilidad es subjetiva.")

elif section == "Monte Carlo":
    st.subheader("Simulación de marcador — supuestos manuales")
    st.caption("Modelo exploratorio: dos distribuciones normales independientes, con medias y desviaciones introducidas por ti. No está entrenado con estadísticas reales.")
    home = st.text_input("Equipo local", "Local")
    away = st.text_input("Equipo visitante", "Visitante")
    a,b,c,d = st.columns(4)
    with a: mean_home = st.number_input("Puntos esperados local", min_value=0.0, max_value=80.0, value=24.0)
    with b: mean_away = st.number_input("Puntos esperados visitante", min_value=0.0, max_value=80.0, value=21.0)
    with c: sd_home = st.number_input("Desv. estándar local", min_value=0.1, max_value=30.0, value=10.0)
    with d: sd_away = st.number_input("Desv. estándar visitante", min_value=0.1, max_value=30.0, value=10.0)
    total_line = st.number_input("Línea de total (Over/Under)", min_value=0.0, max_value=150.0, value=45.5, step=0.5)
    spread = st.number_input("Hándicap local (ej. -3.5)", min_value=-50.0, max_value=50.0, value=-3.5, step=0.5)
    n = st.select_slider("Simulaciones", options=[1000,5000,10000,25000,50000], value=10000)
    rng = np.random.default_rng(20261010)
    hs = np.maximum(0, np.rint(rng.normal(mean_home, sd_home, n))).astype(int)
    vs = np.maximum(0, np.rint(rng.normal(mean_away, sd_away, n))).astype(int)
    a,b,c,d = st.columns(4)
    a.metric(f"{home} gana", f"{np.mean(hs>vs)*100:.1f}%")
    b.metric(f"{away} gana", f"{np.mean(vs>hs)*100:.1f}%")
    c.metric("Over", f"{np.mean(hs+vs>total_line)*100:.1f}%")
    d.metric(f"{home} cubre", f"{np.mean(hs+spread>vs)*100:.1f}%")
    st.caption(f"Empate: {np.mean(hs==vs)*100:.1f}% • Push total: {np.mean(hs+vs==total_line)*100:.1f}% • Push spread: {np.mean(hs+spread==vs)*100:.1f}%")
    st.bar_chart(pd.DataFrame({"Puntos totales":hs+vs})["Puntos totales"].value_counts().sort_index())
    st.caption("Simulación ilustrativa, sin posesiones, correlaciones, overtime, lesiones ni fuerza de calendario. No debe interpretarse como pronóstico validado.")

elif section == "Cuotas CSV":
    st.subheader("Importar líneas capturadas")
    sample = pd.DataFrame([{"league":"NFL","game":"Equipo A vs Equipo B","market":"ML local","american_odds":-110,"captured_at":"2026-10-10T12:00:00-06:00"}])
    st.download_button("Descargar plantilla CSV", sample.to_csv(index=False).encode(), "plantilla_momios.csv", "text/csv")
    upload = st.file_uploader("Sube un CSV de cuotas", type=["csv"])
    if upload:
        try:
            df = pd.read_csv(upload)
            required = {"league","game","market","american_odds","captured_at"}
            missing = required-set(df.columns)
            if missing:
                st.error("Faltan columnas: "+", ".join(sorted(missing)))
            else:
                filtered = df[df["league"].astype(str).str.upper().eq(league)].copy()
                filtered["american_odds"] = pd.to_numeric(filtered["american_odds"], errors="coerce")
                filtered["implied_probability_pct"] = filtered["american_odds"].apply(lambda v: round(100/decimal_odds(v),2) if pd.notna(v) and v != 0 else np.nan)
                st.dataframe(filtered, use_container_width=True, hide_index=True)
                st.caption("Cuotas proporcionadas por el usuario. No se validan contra Caliente.")
        except Exception as exc:
            st.error(f"No se pudo leer el CSV: {exc}")

else:
    st.subheader("Integraciones y validación")
    st.dataframe(pd.DataFrame([
        {"Componente":"Dashboard web","Estado":"Implementado"},
        {"Componente":"Cálculo EV","Estado":"Implementado"},
        {"Componente":"Monte Carlo exploratorio","Estado":"Implementado (sin calibración)"},
        {"Componente":"Importación manual de cuotas","Estado":"Implementado"},
        {"Componente":"API estadísticas NFL/NCAAF","Estado":"Pendiente"},
        {"Componente":"Feed de cuotas Caliente","Estado":"Pendiente / sujeto a acceso permitido"},
        {"Componente":"Entrenamiento histórico + backtesting","Estado":"Pendiente"},
        {"Componente":"Despliegue público","Estado":"Pendiente de Streamlit"},
    ]), hide_index=True, use_container_width=True)
    st.caption("No almacenar credenciales en el repositorio. Usar secretos del proveedor de hosting.")
