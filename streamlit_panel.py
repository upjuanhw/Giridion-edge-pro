"""Drop-in Streamlit panel: call render_expert_signals() from app.py."""
import streamlit as st
from expert_signals import NFL_EXPERTS, SquawkaSignal, nfl_expert_consensus, blend_probabilities, expected_value


def render_expert_signals():
    st.subheader("Squawka Signal + NFL.com Expert Consensus")
    st.caption("Entradas manuales y atribuidas. No son feeds automáticos ni cuotas en vivo.")
    home = st.text_input("Equipo local", "Pittsburgh Steelers")
    away = st.text_input("Equipo visitante", "Cleveland Browns")
    st.markdown("#### Squawka Signal")
    p = st.number_input("Probabilidad local Squawka (%)", 0.0, 100.0, 77.0, 0.5) / 100
    margin = st.number_input("Margen proyectado local Squawka", value=7.8, step=0.5)
    url = st.text_input("URL fuente Squawka", "https://www.squawka.com/us/nfl/")
    as_of = st.text_input("Fecha/hora del pronóstico (con zona)", "2026-10-30")
    signal = SquawkaSignal(p, margin, url, as_of)
    st.info(f"{home}: {signal.home_win_probability:.1%} · Margen {signal.projected_home_margin:+.1f}")
    st.markdown("#### NFL.com · cinco pronósticos")
    st.caption("Introduce los marcadores de NFL.com en orden LOCAL / VISITANTE; deja ambos en 0 para omitir.")
    picks = {}
    for expert in NFL_EXPERTS:
        a, b = st.columns(2)
        with a: hs = st.number_input(f"{expert} · {home}", 0, 100, 0, key=f"nfl_{expert}_home")
        with b: vs = st.number_input(f"{expert} · {away}", 0, 100, 0, key=f"nfl_{expert}_away")
        if hs or vs:
            picks[expert] = (hs, vs)
    if picks:
        c = nfl_expert_consensus(picks)
        st.metric("Expertos a favor del local", f"{c['home_picks']}/{c['experts_count']}")
        st.metric("Margen promedio NFL.com", f"{c['average_home_margin']:+.1f}")
        st.metric("Total promedio NFL.com", f"{c['average_total']:.1f}")
    st.markdown("#### Contraste con Giridion")
    own = st.number_input("Probabilidad local Giridion (%)", 0.1, 99.9, 60.0, 0.5)/100
    weight = st.slider("Peso experimental Squawka (%)", 0, 50, 15)/100
    odds = st.number_input("Momio americano local (manual)", value=-200, step=5)
    combined = blend_probabilities(own, p if 0 < p < 1 else None, weight)
    st.metric("Probabilidad combinada (exploratoria)", f"{combined:.1%}")
    st.metric("EV teórico", f"{expected_value(combined, odds):+.1%}")
    st.warning("No certifica EV positivo: validar calibración, fechas, dependencia y momios antes de apostar.")
    st.markdown(f"Fuentes: [Squawka]({url}) · [NFL.com](https://www.nfl.com/news/nfl-picks-week-8-2026-nfl-season)")
