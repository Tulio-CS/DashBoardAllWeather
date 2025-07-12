import streamlit as st
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
from supabase import create_client
import os
from auth import login

# Configuração da página
st.set_page_config(page_title="Instagram Stories", layout="wide")
st.title("Desempenho de Stories · Instagram")

# Conexão com Supabase
load_dotenv()
SUPABASE_URL  = os.getenv("SUPABASE_URL")
SUPABASE_KEY  = os.getenv("SUPABASE_KEY")
supabase      = create_client(SUPABASE_URL, SUPABASE_KEY)

if not login():
    st.stop()

@st.cache_data(ttl=600)
def carregar_stories():
    resp = supabase.table("stories").select("*").execute()
    df = pd.DataFrame(resp.data or [])

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df["media_type"] = df["media_type"].astype(str).str.upper()

    for col in ["reach", "replies", "interactions"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    return df

df = carregar_stories()

# Filtro por data
st.sidebar.header("Filtro por período")
start, end = st.sidebar.date_input(
    "Intervalo", [df["date"].min(), df["date"].max()],
    min_value=df["date"].min(), max_value=df["date"].max()
)
filtrados = df[(df["date"] >= start) & (df["date"] <= end)]

if filtrados.empty:
    st.warning("Nenhum story no intervalo selecionado.")
    st.stop()

# Métricas gerais
alc_medio = filtrados["reach"].mean()
melhor_dia = filtrados.groupby("date")["reach"].sum().idxmax()
melhor_valor = filtrados.groupby("date")["reach"].sum().max()

col1, col2, col3 = st.columns(3)
col1.metric("Total de Stories", len(filtrados))
col2.metric("Alcance médio por Story", f"{alc_medio:.1f}")
col3.metric("Melhor dia (alcance)", f"{melhor_dia} · {melhor_valor} alcances")

# Gráfico 1 — Alcance médio por dia
st.subheader("Alcance médio por dia")
media_diaria = filtrados.groupby("date")["reach"].mean().reset_index()
fig = px.line(media_diaria, x="date", y="reach", title="Alcance médio diário")
st.plotly_chart(fig, use_container_width=True)

# Gráfico 2 — Interações por tipo de mídia
st.subheader("Interações por tipo de mídia")
mídia = filtrados.groupby("media_type")[["reach", "interactions", "replies"]].sum().reset_index()
fig = px.bar(mídia.melt(id_vars="media_type", var_name="Métrica", value_name="Total"),
             x="media_type", y="Total", color="Métrica", barmode="group")
st.plotly_chart(fig, use_container_width=True)

# Gráfico 3 — Distribuição de interações
st.subheader("Distribuição de interações por story")
fig = px.histogram(filtrados, x="interactions", nbins=20)
st.plotly_chart(fig, use_container_width=True)

# Gráfico 4 — Respostas por dia
st.subheader("Respostas recebidas por dia")
respostas = filtrados.groupby("date")["replies"].sum().reset_index()
fig = px.bar(respostas, x="date", y="replies", title="Respostas totais por dia")
st.plotly_chart(fig, use_container_width=True)

# Tabela resumo
st.subheader("Resumo dos Stories")
st.dataframe(
    filtrados[["date", "media_type", "reach", "replies", "interactions"]]
        .sort_values("date", ascending=False)
        .reset_index(drop=True),
    use_container_width=True
)
