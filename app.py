import io
import requests
from historical_model import clean_games, predict, backtest
from season_data import fetch_season
from datetime import date, timedelta
import math
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Gridiron Edge Pro", page_icon="🏈", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
:root {--ink:#090e16;--panel:#111b29;--edge:#27374b;--accent:#20c997;}
.stApp {background:linear-gradient(145deg,#090e16,#0c1623 65%,#0b1019);color:#edf4fb;}
[data-testid="stSidebar"] {background:#101b2a;border-right:1px solid #24354a;}
.block-container {padding-top:1.1rem;padding-bottom:3rem;max-width:1450px;}
h1,h2,h3 {letter-spacing:-.035em;}
h1 {font-weight:850!important;}
div[data-testid="stMetric"] {background:#121f30;border:1px solid #2b3c50;border-radius:12px;padding:13px;}
div[data-testid="stMetricLabel"] {color:#a5b9ce;}
.stButton button {border-radius:9px;font-weight:700;border:1px solid #31465c;}
[data-testid="stDataFrame"] {border:1px solid #2a3d51;border-radius:12px;overflow:hidden;}
div[data-testid="stAlert"] {border-radius:10px;}
.edge-hero {padding:18px 20px;border:1px solid #31465b;border-radius:14px;background:linear-gradient(110deg,#13243a,#101a28);margin-bottom:18px;}
.edge-kicker {font-size:11px;font-weight:800;letter-spacing:.18em;color:#3ce0b0;}
.edge-headline {font-size:clamp(22px,4vw,34px);font-weight:850;color:#f4f8ff;letter-spacing:-.04em;}
.edge-sub {font-size:13px;color:#b4c6d9;}
.edge-tag {display:inline-block;padding:4px 9px;border:1px solid #3a5369;border-radius:6px;color:#c7d8e9;font-size:11px;font-weight:700;margin-top:10px;}
@media(max-width:650px) {.block-container {padding-left:.8rem;padding-right:.8rem;} .edge-hero{padding:15px;}}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🏈 GRIDIRON EDGE")
    st.caption("PRO • NFL / NCAA")
    league = st.radio("Liga", ["NFL", "NCAAF"], horizontal=True)
    section = st.radio("Panel", ["Mercado de partidos", "Modelo histórico", "Analizador EV", "Monte Carlo", "Cuotas CSV", "Estado del sistema"])
    st.divider()
    st.caption("Versión beta • Marcadores ESPN (fuente pública no oficial); momios no conectados")

st.markdown(f"""<div class="edge-hero"><div class="edge-kicker">GRIDIRON EDGE PRO / {league}</div>
<div class="edge-headline">Mercado & análisis de partidos</div>
<div class="edge-sub">NFL · NCAA · Marcadores · Probabilidades · Valor esperado</div>
<div class="edge-tag">DATOS ESPN · CUOTAS CALIENTE NO CONECTADAS</div></div>""",unsafe_allow_html=True)

def decimal_odds(american):
    return 1 + american/100 if american > 0 else 1 + 100/abs(american) if american < 0 else None

def money(amt):
    return f"${amt:,.2f} MXN"

@st.cache_data(ttl=300, show_spinner=False)
def fetch_scoreboard(selected_league, day):
    sport = "nfl" if selected_league == "NFL" else "college-football"
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/{sport}/scoreboard"
    response = requests.get(url, params={"dates": day.strftime("%Y%m%d"), "limit": 500}, timeout=12,
                            headers={"User-Agent": "GridironEdgePro/0.2"})
    response.raise_for_status()
    payload = response.json()
    rows = []
    for event in payload.get("events", []):
        competition = (event.get("competitions") or [{}])[0]
        competitors = competition.get("competitors", [])
        home = next((c for c in competitors if c.get("homeAway") == "home"), {})
        away = next((c for c in competitors if c.get("homeAway") == "away"), {})
        status = event.get("status", {}).get("type", {})
        rows.append({
            "Fecha (UTC)": event.get("date", ""),
            "Visitante": away.get("team", {}).get("displayName", ""),
            "Puntos visitante": away.get("score", "—"),
            "Local": home.get("team", {}).get("displayName", ""),
            "Puntos local": home.get("score", "—"),
            "Estado": status.get("shortDetail", status.get("description", "")),
            "ESPN": (event.get("links") or [{}])[0].get("web", {}).get("href", "")
        })
    return pd.DataFrame(rows)

if section == "Mercado de partidos":
    st.subheader(f"Mercado de partidos · {league}")
    st.caption("Panel de partidos inspirado en una terminal financiera deportiva. Resultados ESPN (fuente pública no oficial). Los momios y probabilidades del mercado aún no están conectados.")
    a,b = st.columns([2,1])
    with a:
        day = st.date_input("Jornada / fecha", value=date.today(), min_value=date(2020,1,1), max_value=date.today()+timedelta(days=365))
    with b:
        if st.button("↻ Actualizar partidos", use_container_width=True):
            fetch_scoreboard.clear()
    try:
        games = fetch_scoreboard(league, day)
        if games.empty:
            st.info("Sin encuentros registrados en esta fecha. Selecciona otro día.")
        else:
            completed = games["Estado"].astype(str).str.contains("Final",case=False,na=False).sum()
            a,b,c = st.columns(3)
            a.metric("Encuentros",len(games))
            b.metric("Finalizados",int(completed))
            c.metric("Cuotas en vivo","No conectadas")
            st.markdown("#### Cartelera")
            for idx,game in games.iterrows():
                with st.container(border=True):
                    left,right=st.columns([3,1])
                    with left:
                        st.markdown(f"**{game['Visitante']}**  @  **{game['Local']}**")
                        st.caption(str(game["Estado"]))
                    with right:
                        st.markdown(f"### {game['Puntos visitante']} – {game['Puntos local']}")
                    with st.expander("Mercados y análisis"):
                        st.write("**Moneyline:** pendiente · **Spread:** pendiente · **Total:** pendiente")
                        st.caption("No se muestran líneas ficticias. Puedes usar el Analizador EV con cuotas verificadas o el Modelo histórico con datos reales.")
                        if game["ESPN"]:
                            st.link_button("Ficha del encuentro en ESPN ↗",game["ESPN"])
    except (requests.RequestException, ValueError, KeyError) as exc:
        st.error("No se pudieron obtener los encuentros. Intenta actualizar.")
        st.caption(type(exc).__name__)
    st.caption("Actualización en caché: 5 min · Marcadores ESPN sujetos a disponibilidad. No son probabilidades ni cuotas de Caliente.")

elif section == "Modelo histórico":
    st.subheader(f"Modelo histórico y backtesting • {league}")
    st.info("Baseline experimental: medias de puntos a favor/en contra suavizadas, ventaja local manual y Monte Carlo. No incorpora lesiones, fuerza de calendario ni momios. No está calibrado para apostar.")
    st.write("Usa una temporada de resultados públicos de ESPN o carga un CSV de partidos finalizados de una sola liga.")
    @st.cache_data(ttl=86400, show_spinner=False)
    def season_history(selected_league, year):
        return fetch_season(selected_league, year)
    source = st.radio("Origen del histórico", ["ESPN (automático)", "CSV propio"], horizontal=True)
    history = None
    if source == "ESPN (automático)":
        year = st.selectbox("Temporada regular", list(range(2025, 2019, -1)))
        if st.button("Cargar temporada ESPN"):
            with st.spinner("Consultando resultados semanales de ESPN..."):
                try:
                    raw, failures = season_history(league, year)
                    st.session_state["season_history"] = raw
                    st.session_state["season_key"] = (league, year)
                    st.session_state["season_failures"] = failures
                except (ValueError, requests.RequestException) as exc:
                    st.error(f"No fue posible descargar la temporada: {exc}")
        if st.session_state.get("season_key") == (league, year):
            history = st.session_state["season_history"]
            failures = st.session_state.get("season_failures", 0)
            st.caption(f"Temporada {year} • Fuente pública ESPN, no oficial • Semanas con errores: {failures}. La cobertura puede ser incompleta.")
            if failures:
                st.warning("Faltaron algunas semanas: evita interpretar el modelo como validado con la temporada completa.")
            st.download_button("Descargar histórico obtenido", history.to_csv(index=False), f"{league}_{year}_espn.csv", "text/csv")
    else:
        st.caption("Columnas CSV: date, home, away, home_score, away_score. No mezcles NFL y NCAAF.")
    example = pd.DataFrame([
        {"date":"2025-09-07","home":"Equipo A","away":"Equipo B","home_score":27,"away_score":20},
        {"date":"2025-09-14","home":"Equipo B","away":"Equipo A","home_score":17,"away_score":24},
    ])
    st.download_button("Plantilla de resultados", example.to_csv(index=False), "resultados_historicos.csv", "text/csv")
    upload = st.file_uploader("Histórico CSV", type=["csv"], key="history") if source == "CSV propio" else None
    if upload is not None:
        try:
            history = clean_games(pd.read_csv(upload))
        except (ValueError, pd.errors.ParserError) as exc:
            st.error(f"Error al leer el archivo: {exc}")
    if history is not None:
        try:
            history = clean_games(history)
            if len(history) < 10:
                st.warning("Se requieren al menos 10 juegos finalizados para empezar a explorar; para backtesting hacen falta más.")
            else:
                st.metric("Partidos válidos", len(history))
                st.caption(f"Período: {history.date.min().date()} a {history.date.max().date()}. Los datos provienen exclusivamente del archivo cargado.")
                teams = sorted(set(history.home) | set(history.away))
                a, b = st.columns(2)
                with a: home_team = st.selectbox("Equipo local", teams)
                with b: away_team = st.selectbox("Equipo visitante", teams, index=min(1,len(teams)-1))
                a, b = st.columns(2)
                with a: home_adv = st.number_input("Ventaja local (puntos)", -10.0, 10.0, 1.5, 0.5)
                with b: sd = st.number_input("Volatilidad de puntos", 3.0, 25.0, 10.5, 0.5)
                if home_team != away_team:
                    model = predict(history, home_team, away_team, home_adv, sd)
                    a, b, c = st.columns(3)
                    a.metric(f"{home_team} ML (modelo)", f"{model['home_win']*100:.1f}%")
                    b.metric(f"{away_team} ML (modelo)", f"{model['away_win']*100:.1f}%")
                    c.metric("Total esperado", f"{model['total']:.1f}")
                    st.write(f"Marcador medio: {home_team} {model['home_mean']:.1f} – {away_team} {model['away_mean']:.1f}")
                    st.caption(f"Juegos usados: {home_team} {model['home_games']}; {away_team} {model['away_games']}. Empates simulados: {model['tie']*100:.1f}%. No incluye prórroga.")
                    line = st.number_input("Línea total a comparar", 0.0, 120.0, 45.5, 0.5)
                    spread = st.number_input("Spread local a comparar", -50.0, 50.0, -3.5, 0.5)
                    hs, vs = model["home_scores"], model["away_scores"]
                    st.write(f"Over {line}: **{np.mean(hs+vs>line)*100:.1f}%** · Local cubre {spread:+g}: **{np.mean(hs+spread>vs)*100:.1f}%**")
                else:
                    st.warning("Elige dos equipos distintos.")
                st.divider()
                st.subheader("Validación cronológica")
                st.caption("Cada predicción usa únicamente partidos anteriores; excluye encuentros empatados de la métrica ML. Se requiere suficiente historial por equipo.")
                if st.button("Ejecutar backtesting", type="primary"):
                    with st.spinner("Validando predicciones pasadas..."):
                        results = backtest(history)
                    if results.empty:
                        st.warning("No hay suficientes juegos históricos por equipo para validar. Sube más temporadas o partidos.")
                    else:
                        st.metric("Juegos evaluados", len(results))
                        st.metric("Brier score (menor es mejor)", f"{results.brier.mean():.3f}")
                        st.metric("Error absoluto del total", f"{(results.predicted_total-results.actual_total).abs().mean():.1f} puntos")
                        st.dataframe(results, hide_index=True, use_container_width=True)
                        st.caption("Sin comparación contra cuotas de cierre ni benchmark de mercado. Un buen Brier en una muestra pequeña no garantiza rentabilidad.")
        except (ValueError, KeyError, pd.errors.ParserError) as exc:
            st.error(f"Error al procesar el archivo: {exc}")

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
        {"Componente":"Marcadores NFL/NCAAF (ESPN público)","Estado":"Integrado (no oficial; requiere verificación)"},
        {"Componente":"Estadísticas avanzadas / lesiones","Estado":"Pendiente"},
        {"Componente":"Feed de cuotas Caliente","Estado":"Pendiente / sujeto a acceso permitido"},
        {"Componente":"Históricos ESPN por temporada","Estado":"Consulta pública integrada; cobertura no garantizada"},
        {"Componente":"Modelo histórico + backtesting cronológico","Estado":"Baseline experimental; sin validación externa"},
        {"Componente":"Despliegue público","Estado":"Render activo"},
    ]), hide_index=True, use_container_width=True)
    st.caption("No almacenar credenciales en el repositorio. Usar secretos del proveedor de hosting.")
