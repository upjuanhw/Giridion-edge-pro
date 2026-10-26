"""On-demand 2025-2026 Elo and score baseline UI. No sportsbook odds feed."""
from collections import defaultdict
from datetime import date
import pandas as pd
import streamlit as st
from season_data import fetch_season


@st.cache_data(ttl=21600, show_spinner=False)
def load_recent(league, current_year):
    frames, failures = [], 0
    for year in (current_year - 1, current_year):
        frame, errors = fetch_season(league, year)
        frame = frame.copy()
        frame["season"] = year
        frames.append(frame)
        failures += errors
    result = pd.concat(frames, ignore_index=True).drop_duplicates(subset=["event_id"])
    return result.sort_values("date"), failures


def fit_elo(games, home_adv=55.0, k=24.0):
    ratings = defaultdict(lambda: 1500.0)
    scored = defaultdict(lambda: 22.0)
    conceded = defaultdict(lambda: 22.0)
    count = defaultdict(int)
    for _, group in games.groupby(games["date"].astype(str).str[:10], sort=True):
        changes = defaultdict(float)
        updates = []
        for row in group.itertuples(index=False):
            h, a = row.home, row.away
            if not h or not a or h == a:
                continue
            ph = 1/(1+10**((ratings[a]-ratings[h]-home_adv)/400))
            hs, av = int(row.home_score), int(row.away_score)
            outcome = 0.5 if hs == av else (1 if hs > av else 0)
            changes[h] += k*(outcome-ph)
            changes[a] -= k*(outcome-ph)
            updates.append((h,a,hs,av))
        for team, delta in changes.items():
            ratings[team] += delta
        for h,a,hs,av in updates:
            for team,pts,opp in ((h,hs,av),(a,av,hs)):
                scored[team] = .88*scored[team]+.12*pts
                conceded[team] = .88*conceded[team]+.12*opp
                count[team] += 1
    return ratings, scored, conceded, count


def project(home, away, ratings, scored, conceded, count):
    ph = 1/(1+10**((ratings[away]-ratings[home]-55)/400))
    hp = (scored[home]+conceded[away])/2 + .75
    ap = (scored[away]+conceded[home])/2 - .75
    return ph, hp-ap, hp+ap, min(count[home], count[away])


def american_ev(p, odds):
    if odds == 0:
        return None
    profit = odds/100 if odds > 0 else 100/abs(odds)
    return p*profit-(1-p)


def render(league, scoreboard):
    st.subheader(f"Predicciones Elo 2026 · {league}")
    st.warning("Modelo experimental. No calibrado contra casas de apuestas; no incorpora lesiones, cuotas en vivo ni cambios de plantilla.")
    st.caption("Entrena con partidos finalizados de 2025 y 2026. La fuente es ESPN; no utiliza resultados futuros.")
    if st.button("↻ Cargar/actualizar modelo 2026", type="primary"):
        try:
            with st.spinner("Descargando resultados 2025–2026 de ESPN..."):
                games, failures = load_recent(league, date.today().year)
            st.session_state[f"elo_games_{league}"] = games
            st.session_state[f"elo_failures_{league}"] = failures
        except Exception as exc:
            st.error(f"No fue posible cargar el histórico: {type(exc).__name__}: {exc}")
    games = st.session_state.get(f"elo_games_{league}")
    if games is None:
        st.info("Pulsa «Cargar/actualizar modelo 2026» para comenzar.")
        return
    failures = st.session_state.get(f"elo_failures_{league}", 0)
    st.metric("Partidos de entrenamiento", len(games))
    if failures:
        st.warning(f"{failures} semanas no se pudieron consultar; las proyecciones pueden estar incompletas.")
    ratings, scored, conceded, count = fit_elo(games)
    teams = sorted(set(games.home) | set(games.away))
    c1,c2 = st.columns(2)
    with c1:
        home = st.selectbox("Local", teams, key=f"elo_home_{league}")
    with c2:
        away = st.selectbox("Visitante", teams, index=min(1,len(teams)-1), key=f"elo_away_{league}")
    if home == away:
        st.error("Selecciona equipos diferentes.")
        return
    ph, margin, total, sample = project(home,away,ratings,scored,conceded,count)
    if sample < 4:
        st.warning("Muestra insuficiente para uno de los equipos; no interpretes el porcentaje como confiable.")
    a,b,c = st.columns(3)
    a.metric(f"{home} ML",f"{ph:.1%}")
    b.metric("Margen local esperado",f"{margin:+.1f}")
    c.metric("Puntos totales esperados",f"{total:.1f}")
    st.caption(f"Probabilidad visitante: {1-ph:.1%}. Proyecciones basadas en resultados anteriores; no son momios de Caliente.")
    st.markdown("#### Compara una cuota real")
    side = st.radio("Selección",["Local","Visitante"],horizontal=True,key=f"elo_side_{league}")
    odds = st.number_input("Momio americano (introducido por ti)",min_value=-10000,max_value=10000,value=200,step=10,key=f"elo_odds_{league}")
    p = ph if side=="Local" else 1-ph
    ev = american_ev(p,odds)
    if ev is None:
        st.info("Introduce un momio diferente de cero.")
    else:
        st.metric("EV teórico según el modelo",f"{ev:+.1%}")
        st.caption("EV positivo no garantiza rentabilidad. No hay comparación histórica con el mercado ni validación de ROI.")
