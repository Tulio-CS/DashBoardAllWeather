import streamlit as st
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
from supabase import create_client
import os

# Configuração da página
st.set_page_config(page_title="Clarity Insights", layout="wide")
st.title("Clarity Insights")

# Conectar ao Supabase
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_data(ttl=600)
def carregar_dados():
    # Tabela clarityInsights
    insights = supabase.table("clarityInsights").select("*").execute()
    df_insights = pd.DataFrame(insights.data or [])
    df_insights["timestamp"] = pd.to_datetime(df_insights["timestamp"], errors="coerce")

    for col in ["sessionsCount", "totalBotSessionCount", "distinctUserCount", "averageScrollDepth", "totalTime"]:
        df_insights[col] = pd.to_numeric(df_insights[col], errors="coerce")

    df_insights = df_insights.dropna(subset=["sessionsCount"])

    # Tabela scrollData
    scrolls = supabase.table("scrollData").select("*").execute()
    df_scroll = pd.DataFrame(scrolls.data or [])
    df_scroll["timestamp"] = pd.to_datetime(df_scroll["timestamp"], errors="coerce")

    for col in ["Scroll depth", "No of visitors", "% drop off"]:
        df_scroll[col] = pd.to_numeric(df_scroll[col], errors="coerce")

    return df_insights, df_scroll

df_insights, df_scroll = carregar_dados()

# Filtro por data
st.sidebar.header("Filtro por Data")
min_date = min(df_insights["timestamp"].min(), df_scroll["timestamp"].min()).date()
max_date = max(df_insights["timestamp"].max(), df_scroll["timestamp"].max()).date()
start, end = st.sidebar.date_input("Intervalo", [min_date, max_date], min_value=min_date, max_value=max_date)

df_insights = df_insights[(df_insights["timestamp"].dt.date >= start) & (df_insights["timestamp"].dt.date <= end)]
df_scroll   = df_scroll[(df_scroll["timestamp"].dt.date >= start) & (df_scroll["timestamp"].dt.date <= end)]

# Gráfico: Sessões vs Tempo Total
st.subheader("Sessões vs Tempo Total por Métrica")
fig_scatter = px.scatter(
    df_insights,
    x="sessionsCount",
    y="totalTime",
    color="metricName",
    title="Relação entre Sessões e Tempo Total",
    labels={"sessionsCount": "Sessões", "totalTime": "Tempo Total (s)"},
    hover_data=["metricName"]
)
st.plotly_chart(fig_scatter, use_container_width=True)


# Gráfico scroll: Visitantes por profundidade
st.subheader("Visitantes por profundidade de scroll")
fig_scroll = px.bar(
    df_scroll.sort_values("Scroll depth"),
    x="Scroll depth",
    y="No of visitors",
    title="Visitantes por faixa de scroll",
    labels={"Scroll depth": "Scroll (%)", "No of visitors": "Visitantes"}
)
st.plotly_chart(fig_scroll, use_container_width=True)

# Gráfico scroll: Taxa de abandono
st.subheader("Taxa de Abandono por profundidade")
fig_drop = px.line(
    df_scroll.sort_values("Scroll depth"),
    x="Scroll depth",
    y="% drop off",
    markers=True,
    title="% de abandono por faixa de scroll"
)
st.plotly_chart(fig_drop, use_container_width=True)

# Agrupar por data (dia)
df_scroll["date"] = df_scroll["timestamp"].dt.date

# 1. Profundidade média por dia
scroll_avg = df_scroll.groupby("date").apply(
    lambda x: (x["Scroll depth"] * x["No of visitors"]).sum() / x["No of visitors"].sum()
).reset_index(name="avg_scroll")

st.subheader("Profundidade média de scroll por dia")
fig_avg_scroll = px.line(
    scroll_avg,
    x="date",
    y="avg_scroll",
    title="Profundidade média de scroll ao longo do tempo",
    labels={"date": "Data", "avg_scroll": "Scroll médio (%)"},
    markers=True
)
st.plotly_chart(fig_avg_scroll, use_container_width=True)

# 2. Total de visitantes por dia
visitors_daily = df_scroll.groupby("date")["No of visitors"].sum().reset_index()

st.subheader("Visitantes por dia")
fig_visitors = px.line(
    visitors_daily,
    x="date",
    y="No of visitors",
    title="Evolução do número de visitantes",
    labels={"date": "Data", "No of visitors": "Visitantes"},
    markers=True
)
st.plotly_chart(fig_visitors, use_container_width=True)

# 3. Taxa média de abandono por dia
drop_avg = df_scroll.groupby("date")["% drop off"].mean().reset_index()

st.subheader("Taxa média de abandono por dia")
fig_dropoff = px.line(
    drop_avg,
    x="date",
    y="% drop off",
    title="Evolução da taxa média de abandono",
    labels={"date": "Data", "% drop off": "% de abandono"},
    markers=True
)
st.plotly_chart(fig_dropoff, use_container_width=True)

# 4. Múltiplas linhas por faixa de scroll
st.subheader("Visitantes por faixa de scroll ao longo do tempo")
scroll_lines = df_scroll.groupby(["date", "Scroll depth"])["No of visitors"].sum().reset_index()
fig_lines = px.line(
    scroll_lines,
    x="date",
    y="No of visitors",
    color="Scroll depth",
    title="Visitantes por faixa de scroll ao longo do tempo",
    labels={"date": "Data", "No of visitors": "Visitantes", "Scroll depth": "Scroll (%)"}
)
st.plotly_chart(fig_lines, use_container_width=True)


# Tabelas
st.subheader("Tabela de Clarity Insights")
st.dataframe(df_insights.sort_values("sessionsCount", ascending=False).reset_index(drop=True), use_container_width=True)

st.subheader("Tabela de Scroll")
st.dataframe(df_scroll.sort_values("Scroll depth").reset_index(drop=True), use_container_width=True)


