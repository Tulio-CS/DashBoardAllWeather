import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
from dotenv import load_dotenv
import os
from auth import login

# Carregar variáveis de ambiente
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Criar cliente Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

if not login():
    st.stop()

st.title('Dashboard Instagram - All Weather')

@st.cache_data(ttl=600)
def carregar_dados_instagram():
    response = supabase.table("Posts").select("*").execute()
    df = pd.DataFrame(response.data)

    # Conversão de timestamp e timezone
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    if df["timestamp"].dt.tz is None:
        df["timestamp"] = df["timestamp"].dt.tz_localize('UTC').dt.tz_convert('America/Sao_Paulo')
    else:
        df["timestamp"] = df["timestamp"].dt.tz_convert('America/Sao_Paulo')

    # Colunas auxiliares
    df["Data"] = df["timestamp"].dt.date
    df["dia_semana"] = df["timestamp"].dt.day_name()
    df["hora"] = df["timestamp"].dt.hour

    # Conversão de métricas para numérico
    metricas = ["reach", "likes", "comments", "saved", "shares"]
    df[metricas] = df[metricas].apply(pd.to_numeric, errors='coerce')

    return df

df = carregar_dados_instagram()
df = df.sort_values(by="timestamp", ascending=False)
# Filtros de data
start_date = st.sidebar.date_input("Data inicial", df['Data'].min())
end_date = st.sidebar.date_input("Data final", df['Data'].max())
filtro = df[(df['Data'] >= start_date) & (df['Data'] <= end_date)]

# KPIs
total_reach = filtro['reach'].sum()
total_likes = filtro['likes'].sum()
total_comments = filtro['comments'].sum()
total_saved = filtro['saved'].sum()
total_shares = filtro['shares'].sum()
engajamento = (total_likes + total_comments + total_saved + total_shares) / total_reach * 100 if total_reach > 0 else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Alcance Total", f"{total_reach}")
col2.metric("Engajamento (%)", f"{engajamento:.2f}%")
col3.metric("Curtidas", f"{total_likes}")
col4.metric("Comentários", f"{total_comments}")

col5, col6, col7 = st.columns(3)
col5.metric("Salvamentos", f"{total_saved}")
col6.metric("Compartilhamentos", f"{total_shares}")
col7.metric("Total Posts", f"{len(filtro)}")

# Tabela de dados
st.subheader("Tabela de Dados")
tabela = pd.DataFrame({
    "Data": filtro["Data"],
    "Tipo de Post": filtro["media_type"],
    "Tema/Descrição": filtro["caption"],
    "Formato (Feed, Reels, etc.)": filtro["media_type"],
    "Alcance": filtro["reach"],
    "Impressões": filtro["reach"],
    "Curtidas": filtro["likes"],
    "Comentários": filtro["comments"],
    "Salvamentos": filtro["saved"],
    "Compartilhamentos": filtro["shares"],
    "Interação / Impressões (%)": (
        ((filtro["likes"] + filtro["comments"] + filtro["shares"]) / filtro["reach"]) * 100
    ).round(2)
})
st.dataframe(tabela)

# Evolução das métricas
st.subheader("Evolução Diária")
agrupado = filtro.groupby('Data').sum(numeric_only=True).reset_index()
fig = px.line(agrupado, x='Data', y=['reach', 'likes', 'comments', 'saved', 'shares'], markers=True)
st.plotly_chart(fig)

# Performance média por tipo de post
st.subheader("Performance Média por Tipo de Post")
agrupado_tipo = filtro.groupby('media_type').agg({
    'reach': 'mean', 'likes': 'mean', 'comments': 'mean', 'shares': 'mean'
}).reset_index()
agrupado_tipo['Interação (%)'] = ((agrupado_tipo['likes'] + agrupado_tipo['comments'] + agrupado_tipo['shares']) / agrupado_tipo['reach'] * 100).round(2)
fig = px.bar(agrupado_tipo.melt(id_vars='media_type'), x='media_type', y='value', color='variable', barmode='group')
st.plotly_chart(fig)

# Performance média por dia da semana
st.subheader("Performance Média por Dia da Semana")
ordem_dias = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
agrupado_dia = filtro.groupby('dia_semana').agg({
    'reach': 'mean', 'likes': 'mean', 'comments': 'mean', 'shares': 'mean'
}).reindex(ordem_dias).reset_index()
agrupado_dia['Interação (%)'] = ((agrupado_dia['likes'] + agrupado_dia['comments'] + agrupado_dia['shares']) / agrupado_dia['reach'] * 100).round(2)
fig = px.bar(agrupado_dia.melt(id_vars='dia_semana'), x='dia_semana', y='value', color='variable', barmode='group')
st.plotly_chart(fig)

# Performance média por horário
st.subheader("Performance Média por Horário de Postagem")
agrupado_hora = filtro.groupby('hora').agg({
    'reach': 'mean', 'likes': 'mean', 'comments': 'mean', 'shares': 'mean'
}).reset_index()
agrupado_hora['Interação (%)'] = ((agrupado_hora['likes'] + agrupado_hora['comments'] + agrupado_hora['shares']) / agrupado_hora['reach'] * 100).round(2)
fig = px.bar(agrupado_hora.melt(id_vars='hora'), x='hora', y='value', color='variable', barmode='group')
st.plotly_chart(fig)

# Top posts
st.subheader("Top 10 Posts - Alcance vs Curtidas (Tamanho = Comentários)")
top_alcance = filtro.sort_values(by="reach", ascending=False).head(10).copy()
fig = px.scatter(top_alcance, x="reach", y="likes", size="comments", color="permalink")
st.plotly_chart(fig)

# Links clicáveis
st.subheader("Links dos Top 10 Posts")
top_alcance["Link"] = top_alcance["permalink"].apply(lambda x: f"[Abrir Post]({x})")
st.markdown(
    top_alcance[["Link", "reach", "likes", "comments"]]
    .rename(columns={"reach": "Alcance", "likes": "Curtidas", "comments": "Comentários"})
    .to_markdown(index=False),
    unsafe_allow_html=True
)
