import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timezone

st.set_page_config(page_title="Gridiron Edge Pro",page_icon="🏈",layout="wide")
st.title("🏈 Gridiron Edge Pro")
st.caption("NFL + NCAAF | Panel inicial. Las cuotas deben verificarse antes de apostar.")
league=st.selectbox("Liga",["NFL","NCAAF"])
st.subheader("Analizador de momios y valor esperado")
c1,c2,c3=st.columns(3)
with c1: odds=st.number_input("Momio americano",value=150,step=10)
with c2: probability=st.number_input("Probabilidad propia (%)",min_value=0.0,max_value=100.0,value=40.0,step=0.5)
with c3: bankroll=st.number_input("Bankroll (MXN)",min_value=0.0,value=30000.0,step=500.0)
decimal=1+odds/100 if odds>0 else 1+100/abs(odds) if odds<0 else 1
break_even=100/decimal
ev=(probability/100*decimal-1)*100
a,b,c=st.columns(3)
a.metric("Probabilidad de equilibrio",f"{break_even:.1f}%")
b.metric("EV por $100",f"${ev:+.2f}")
c.metric("Límite de 1% de bankroll",f"${bankroll*.01:,.0f}")
st.info("Una probabilidad introducida manualmente no es una estimación calibrada. No hay conexión en vivo a Caliente.")
st.subheader("Importar cuotas verificadas")
upload=st.file_uploader("CSV con columnas league, game, market, american_odds, captured_at",type="csv")
if upload:
    df=pd.read_csv(upload)
    required={"league","game","market","american_odds","captured_at"}
    if not required.issubset(df.columns):
        st.error("Faltan columnas: "+", ".join(sorted(required-set(df.columns))))
    else:
        st.dataframe(df[df["league"].eq(league)],use_container_width=True)
        st.caption("Estos registros proceden del archivo cargado, no de una API en tiempo real.")
st.subheader("Estado del sistema")
st.write("🟢 Dashboard y calculadora EV | 🟡 Importación manual de cuotas | 🔴 Feed automático Caliente y entrenamiento validado pendientes")
st.caption("Gridiron Edge Pro · Prototipo publicado desde GitHub")
