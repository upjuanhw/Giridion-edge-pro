import io
import os
import requests
from historical_model import clean_games, predict, backtest
from season_data import fetch_season
from live_model_dashboard import render as render_live_elo, load_recent, fit_elo, project, american_ev
from data_quality import audit_games, is_clean
from odds_provider import fetch_odds
from market_math import implied_probability, no_vig_probabilities, expected_value
from datetime import date, timedelta
from zoneinfo import ZoneInfo
import math
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_panel import render_expert_signals

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
.edge-hero {padding:10px 14px;border:1px solid #31465b;border-radius:14px;background:linear-gradient(110deg,#13243a,#101a28);margin-bottom:8px;}
.edge-kicker {font-size:11px;font-weight:800;letter-spacing:.18em;color:#3ce0b0;}
.edge-headline {font-size:clamp(20px,3vw,27px);font-weight:850;color:#f4f8ff;letter-spacing:-.04em;}
.edge-sub {font-size:13px;color:#b4c6d9;}
.edge-tag {display:inline-block;padding:4px 9px;border:1px solid #3a5369;border-radius:6px;color:#c7d8e9;font-size:11px;font-weight:700;margin-top:10px;}
@media(max-width:650px) {.block-container {padding-left:.8rem;padding-right:.8rem;} .edge-hero{padding:15px;}}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🏈 GRIDIRON EDGE")
    st.caption("PRO • NFL / NCAA")
    st.caption("La navegación principal está siempre visible arriba.")
    st.divider()
    st.caption("Versión beta • Marcadores ESPN (fuente pública no oficial); momios no conectados")

# Mobile-first navigation: always visible, with games as the default.
league = st.segmented_control("Liga", ["NFL", "NCAAF"], default="NFL", key="league_top")
labels = ["Partidos", "Elo 2026", "Modelo", "EV", "Monte Carlo", "Cuotas", "Comparador", "Expertos NFL", "Configuración"]
selection = st.selectbox("Vista", labels, index=0, key="view_top")
section = dict(zip(labels, ["Mercado de partidos", "Elo 2026", "Modelo histórico", "Analizador EV", "Monte Carlo", "Cuotas CSV", "Comparador de mercado", "Expertos NFL", "Estado del sistema"]))[selection]
st.markdown(f"""<div class="edge-hero"><div class="edge-kicker">GRIDIRON EDGE PRO / {league}</div>
<div class="edge-headline">Football Market Terminal</div>
<div class="edge-sub">Partidos · Estadística · Modelos · Valor esperado</div></div>""",unsafe_allow_html=True)

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
            "Estado técnico": status.get("name", ""),
            "Récord visitante": (away.get("records") or [{}])[0].get("summary", "N/D"),
            "Logo visitante": away.get("team", {}).get("logo", ""),
            "Logo local": home.get("team", {}).get("logo", ""),
            "Récord local": (home.get("records") or [{}])[0].get("summary", "N/D"),
            "Abreviatura visitante": away.get("team", {}).get("abbreviation", ""),
            "Abreviatura local": home.get("team", {}).get("abbreviation", ""),
            "Visitante": away.get("team", {}).get("displayName", ""),
            "Puntos visitante": away.get("score", "—"),
            "Local": home.get("team", {}).get("displayName", ""),
            "Puntos local": home.get("score", "—"),
            "Estado": status.get("shortDetail", status.get("description", "")),
            "ESPN": (event.get("links") or [{}])[0].get("web", {}).get("href", "")
        })
    return pd.DataFrame(rows)

if section == "Comparador de mercado":
    st.subheader("Comparador de mercado · ML")
    st.caption("Momios introducidos manualmente; NO son cuotas en vivo. Modelo y mercado deben corresponder al mismo partido y momento.")
    c1, c2 = st.columns(2)
    with c1:
        home_odds = st.number_input("Momio ML local (americano)", value=-110, step=5, key="compare_home")
    with c2:
        away_odds = st.number_input("Momio ML visitante (americano)", value=-110, step=5, key="compare_away")
    probability_pct = st.slider("Probabilidad estimada de victoria local (%)", 0.0, 100.0, 50.0, 0.5, key="compare_probability")
    try:
        market = no_vig_probabilities([home_odds, away_odds])
        estimate = probability_pct / 100
        results = pd.DataFrame([
            {"Selección": "Local", "Momio": home_odds, "Prob. implícita": implied_probability(home_odds),
             "Mercado sin margen": market[0], "Modelo": estimate, "EV por unidad": expected_value(estimate, home_odds)},
            {"Selección": "Visitante", "Momio": away_odds, "Prob. implícita": implied_probability(away_odds),
             "Mercado sin margen": market[1], "Modelo": 1-estimate, "EV por unidad": expected_value(1-estimate, away_odds)},
        ])
        st.dataframe(results.style.format({"Prob. implícita": "{:.1%}", "Mercado sin margen": "{:.1%}",
                                           "Modelo": "{:.1%}", "EV por unidad": "{:+.1%}"}),
                     hide_index=True, use_container_width=True)
        st.metric("Margen implícito de la casa", f"{(implied_probability(home_odds) + implied_probability(away_odds) - 1):+.2%}")
        st.warning("EV teórico, no validado. La estimación introducida puede estar mal calibrada; no implica ventaja comprobada.")
    except ValueError as exc:
        st.error(f"Momios inválidos: {exc}")

elif section == "Expertos NFL":
    if league == "NFL":
        render_expert_signals()
    else:
        st.info("El panel de expertos está disponible únicamente para NFL.")

elif section == "Elo 2026":
    render_live_elo(league, fetch_scoreboard)

elif section == "Mercado de partidos":
    st.caption("Marcadores ESPN · caché 5 min · Cuotas Caliente pendientes")
    a,b = st.columns([2,1])
    with a:
        day = st.date_input("Jornada / fecha", value=date.today(), min_value=date(2020,1,1), max_value=date.today()+timedelta(days=365))
    with b:
        if st.button("↻ Actualizar partidos", use_container_width=True):
            fetch_scoreboard.clear()
    show_projections = st.toggle("Proyecciones Elo en cada partido", value=True, key=f"inline_elo_{league}")
    elo_state = None
    if show_projections:
        try:
            with st.spinner("Cargando historial de 2025–2026..."):
                history, missing = load_recent(league, date.today().year)
            history = history[pd.to_datetime(history["date"], utc=True, errors="coerce").dt.date < day]
            if not history.empty:
                ratings, scored, conceded, counts = fit_elo(history)
                elo_state = (ratings, scored, conceded, counts)
            if missing:
                st.warning(f"Histórico parcial: {missing} semanas sin datos.")
        except Exception as exc:
            st.warning(f"No se pudo cargar Elo ({type(exc).__name__}); la cartelera sigue disponible.")
    try:
        games = fetch_scoreboard(league, day)
        if games.empty:
            st.info("Sin encuentros registrados en esta fecha. Selecciona otro día.")
        else:
            completed = games["Estado técnico"].astype(str).str.upper().eq("STATUS_FINAL").sum()
            f1,f2 = st.columns(2)
            with f1:
                status_filter = st.selectbox("Estado", ["Todos", "Programados", "En vivo", "Finalizados"])
            with f2:
                team_filter = st.selectbox("Equipo", ["Todos"] + sorted(set(games["Local"]) | set(games["Visitante"])))
            if team_filter != "Todos":
                games = games[(games["Local"] == team_filter) | (games["Visitante"] == team_filter)]
            if status_filter != "Todos":
                names = games["Estado técnico"].astype(str).str.upper()
                if status_filter == "Finalizados":
                    games = games[names.eq("STATUS_FINAL")]
                elif status_filter == "En vivo":
                    games = games[names.isin(["STATUS_IN_PROGRESS", "STATUS_HALFTIME"])]
                else:
                    games = games[names.eq("STATUS_SCHEDULED")]
            games = games.reset_index(drop=True)
            a,b = st.columns(2)
            a.metric("Encuentros filtrados",len(games))
            b.metric("Finalizados",int(completed))
            st.markdown("#### Cartelera")
            for idx,game in games.iterrows():
                with st.container(border=True):
                    st.markdown(f"**{game['Visitante']}**  @  **{game['Local']}**")
                    if elo_state is not None:
                        ratings, scored, conceded, counts = elo_state
                        home_name, away_name = game["Local"], game["Visitante"]
                        if counts[home_name] >= 4 and counts[away_name] >= 4:
                            ph, margin, total, sample = project(home_name, away_name, ratings, scored, conceded, counts)
                            e1,e2,e3 = st.columns(3)
                            e1.metric("ML local · Elo", f"{ph:.1%}")
                            e2.metric("Margen local", f"{margin:+.1f}")
                            e3.metric("Total proyectado", f"{total:.1f}")
                            with st.expander("Comparar moneyline con cuota real"):
                                side = st.radio("Selección", ["Local", "Visitante"], horizontal=True, key=f"card_side_{league}_{idx}")
                                odd = st.number_input("Momio americano", -10000, 10000, 200, 10, key=f"card_odds_{league}_{idx}")
                                ev = american_ev(ph if side == "Local" else 1-ph, odd)
                                if ev is not None:
                                    st.metric("EV teórico", f"{ev:+.1%}")
                                st.caption("Proyección experimental; no validada frente al mercado.")
                        else:
                            st.caption("Elo: historial insuficiente para uno o ambos equipos.")
                    c1,c2,c3 = st.columns([2,1,2])
                    with c1:
                        if str(game["Logo visitante"]).startswith("https://"):
                            st.image(game["Logo visitante"], width=42)
                        st.markdown(f"### {game['Abreviatura visitante'] or 'VIS'}")
                        st.caption("Visitante · " + str(game["Récord visitante"]))
                    with c2:
                        st.markdown(f"### {game['Puntos visitante']} : {game['Puntos local']}")
                    with c3:
                        if str(game["Logo local"]).startswith("https://"):
                            st.image(game["Logo local"], width=42)
                        st.markdown(f"### {game['Abreviatura local'] or 'LOC'}")
                        st.caption("Local · " + str(game["Récord local"]))
                    try:
                        kickoff = pd.to_datetime(game["Fecha (UTC)"], utc=True).tz_convert(ZoneInfo("America/Mexico_City"))
                        kickoff_label = kickoff.strftime("%d/%m · %H:%M CDMX")
                    except (ValueError, TypeError):
                        kickoff_label = "Horario no disponible"
                    st.caption(kickoff_label + " · " + str(game["Estado"]))
                    with st.expander("Ficha del partido · estadísticas y mercados"):
                        st.markdown("**Comparación de equipos**")
                        st.write("Récord visitante: " + str(game["Récord visitante"]) + " · Récord local: " + str(game["Récord local"]))
                        st.caption("Récord provisto por ESPN cuando está disponible; no es una calificación predictiva.")
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
            audit = audit_games(history)
            with st.expander("Auditoría de integridad del histórico"):
                st.write("Registros:", audit["rows"])
                st.write("Fechas inválidas:", audit["invalid_dates"])
                st.write("Marcadores inválidos:", audit["invalid_scores"])
                st.write("Equipos faltantes / idénticos:", audit["missing_teams"])
                st.write("Duplicados por fecha y equipos:", audit["duplicate_matchups"])
                if "event_id" in history.columns:
                    st.write("IDs duplicados:", audit["duplicate_ids"])
            if not is_clean(audit):
                st.error("El histórico presenta problemas de integridad. Corrige el origen antes de ejecutar el modelo.")
                st.stop()
            history = clean_games(history)
            if len(history) < 10:
                st.warning("Se requieren al menos 10 juegos finalizados para empezar a explorar; para backtesting hacen falta más.")
            else:
                st.metric("Partidos válidos", len(history))
                st.caption(f"Período: {history.date.min().date()} a {history.date.max().date()}. Fuente: {source}. Cobertura e integridad sujetas a revisión.")
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
    st.markdown("#### Momios publicados · NFL / NCAAF")
    st.caption("Proveedor independiente TheOddsAPI; las cuotas NO son de Caliente. Requiere clave de acceso y plan compatible.")
    provider_key = os.environ.get("THEODDSAPI_KEY", "")
    if not provider_key:
        provider_key = st.text_input("Clave The Odds API (opcional, solo en esta sesión)", type="password", key="odds_key_session")
    if provider_key:
        @st.cache_data(ttl=900, show_spinner=False)
        def provider_prices(selected_league, key):
            return fetch_odds(selected_league, key)
        if st.button("Actualizar momios publicados"):
            provider_prices.clear()
        try:
            market_rows = provider_prices(league, provider_key)
            if market_rows.empty:
                st.info("El proveedor no reporta mercados disponibles para esta liga.")
            else:
                st.dataframe(market_rows, hide_index=True, use_container_width=True)
                st.download_button("Exportar cuotas publicadas", market_rows.to_csv(index=False).encode(),
                                   "cuotas_proveedor.csv", mime="text/csv")
        except requests.RequestException as exc:
            st.warning("No se pudieron consultar cuotas. Comprueba el plan, la clave y la disponibilidad del proveedor.")
            st.caption(type(exc).__name__)
    else:
        st.info("Feed preparado, aún sin clave. Configura THEODDSAPI_KEY en los secretos de Render; no la incluyas en GitHub.")
        st.link_button("Obtener clave del proveedor ↗", "https://theoddsapi.com/pricing")
    st.markdown("#### Registrar momio de Caliente")
    st.caption("Captura manual a partir de una cuota que hayas comprobado en Caliente. No es un feed en vivo ni accede a tu cuenta.")
    with st.form("caliente_manual"):
        game_name = st.text_input("Partido", placeholder="Pittsburgh Steelers @ Cleveland Browns")
        market_name = st.selectbox("Mercado", ["ML local", "ML visitante", "Spread local", "Spread visitante", "Over", "Under"])
        american = st.number_input("Momio americano", value=-110, step=5)
        line = st.number_input("Línea (puntos, si aplica)", value=0.0, step=0.5)
        captured = st.text_input("Fecha/hora de captura (ISO 8601 con zona)", value=pd.Timestamp.now(tz="America/Mexico_City").isoformat(timespec="seconds"))
        submitted = st.form_submit_button("Añadir a mi registro")
    if submitted:
        try:
            stamp = pd.Timestamp(captured)
            if stamp.tzinfo is None:
                raise ValueError("Incluye zona horaria, por ejemplo -06:00.")
            if not game_name.strip() or american == 0 or abs(american) < 100:
                raise ValueError("Indica un partido y un momio americano válido (mínimo ±100).")
            row = {"league": league, "game": game_name.strip(), "market": market_name,
                   "line": line if market_name.startswith(("Spread", "Over", "Under")) else None,
                   "american_odds": int(american), "captured_at": stamp.isoformat(),
                   "source": "Caliente (captura manual, sin verificación automática)"}
            st.session_state.setdefault("manual_caliente", []).append(row)
            st.success("Momio registrado en esta sesión. Descarga el CSV para conservarlo.")
        except (ValueError, TypeError) as exc:
            st.error(str(exc))
    saved = pd.DataFrame(st.session_state.get("manual_caliente", []))
    if not saved.empty:
        st.dataframe(saved, hide_index=True, use_container_width=True)
        st.download_button("Exportar mis momios Caliente", saved.to_csv(index=False).encode("utf-8"),
                           "caliente_capturas.csv", mime="text/csv")
        st.caption("El registro en memoria se pierde al reiniciar la sesión o el servidor; exporta el CSV.")
    st.link_button("Consultar cuotas en Caliente ↗", "https://sports.caliente.mx/es_MX/Futbol-Americano")
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
    status_rows = pd.DataFrame([
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
    ])
    for _, item in status_rows.iterrows():
        with st.container(border=True):
            st.markdown(f"**{item['Componente']}**")
            st.caption(item["Estado"])
    st.caption("No almacenar credenciales en el repositorio. Usar secretos del proveedor de hosting.")
