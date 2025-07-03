import os
import streamlit as st
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
from supabase import create_client

# Configuração inicial da página
st.set_page_config(page_title="Meta Ads Dashboard", layout="wide")
st.title("📊 Meta Ads Dashboard · All Weather")

# Conexão Supabase
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_data(ttl=600)
def load_data():
    resp = supabase.table("metaAds").select("*").execute()
    df = pd.DataFrame(resp.data or [])

    # Datas e identificadores
    df["date_start"] = pd.to_datetime(df["date_start"], errors="coerce")
    df["date_stop"] = pd.to_datetime(df["date_stop"], errors="coerce")
    df["date"] = df["date_start"].dt.date
    for col in ["ad_id", "adset_id", "campaign_id", "ad_name", "campaign_name", "adset_name"]:
        df[col] = df[col].astype(str).str.strip()

    # Conversão de numéricos
    num_cols = [
        "impressions", "reach", "frequency", "clicks", "spend", "cpc", "cpm", "cpp", "ctr",
        "video_view_30s", "video_view_3s", "video_p25", "video_p50",
        "video_p75", "video_p95", "video_p100", "hook_rate",
        "add_to_cart", "initiate_checkout", "purchase"
    ]
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce").fillna(0)

    # Métricas derivadas
    df["CTR (%)"] = (df["clicks"] / df["impressions"] * 100).round(2)
    df["CPC (R$)"] = (df["spend"] / df["clicks"]).replace([float("inf"), pd.NA], 0).round(2)
    df["CPM (R$)"] = (df["spend"] / df["impressions"] * 1000).replace([float("inf"), pd.NA], 0).round(2)
    df["CPA (R$)"] = (df["spend"] / df["add_to_cart"]).replace([float("inf"), pd.NA], 0).round(2)
    df["CPP (R$)"] = (df["spend"] / df["purchase"]).replace([float("inf"), pd.NA], 0).round(2)
    df["CVR (%)"] = (df["purchase"] / df["clicks"] * 100).replace([float("inf"), pd.NA], 0).round(2)
    df["Hook Rate (%)"] = (df["video_view_3s"] / df["impressions"] * 100).replace([float("inf"), pd.NA], 0).round(2)
    df["Hold Rate (%)"] = (df["video_p100"] / df["video_view_3s"] * 100).replace([float("inf"), pd.NA], 0).round(2)
    df["ROAS Real"] = (df["purchase"] / df["spend"]).replace([float("inf"), pd.NA], 0).round(2)
    df["AOV Estimado"] = (df["purchase"] / df["add_to_cart"]).replace([float("inf"), pd.NA], 0).round(2)
    df["ROAS Estimado"] = ((df["add_to_cart"] * df["AOV Estimado"]) / df["spend"]).replace([float("inf"), pd.NA], 0).round(2)

    # Link clicável para Biblioteca de Anúncios
    df["Ver Anúncio"] = df["ad_id"].apply(
        lambda x: f"[🔗 Ver Anúncio](https://www.facebook.com/ads/library/?id={x})"
    )

    return df

# Carregar dados
df = load_data()

# Filtros
st.sidebar.header("Filtros")
min_date, max_date = df["date"].min(), df["date"].max()
start_date, end_date = st.sidebar.date_input("Período", [min_date, max_date], min_value=min_date, max_value=max_date)
campaigns = st.sidebar.multiselect("Campanhas", df["campaign_name"].unique(), default=df["campaign_name"].unique())
df = df[(df["date"] >= start_date) & (df["date"] <= end_date) & (df["campaign_name"].isin(campaigns))]

# KPIs
st.subheader("🔢 Métricas Principais")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Impressões", f"{int(df['impressions'].sum()):,}")
col2.metric("Cliques", f"{int(df['clicks'].sum()):,}")
col3.metric("Compras", f"{int(df['purchase'].sum()):,}")
col4.metric("Gasto Total", f"R$ {df['spend'].sum():,.2f}")

col1, col2, col3, col4 = st.columns(4)
col1.metric("CTR (%)", f"{df['CTR (%)'].mean():.2f}")
col2.metric("CPC (R$)", f"R$ {df['CPC (R$)'].mean():.2f}")
col3.metric("CPP (R$)", f"R$ {df['CPP (R$)'].mean():.2f}")
col4.metric("ROAS Real", f"{df['ROAS Real'].mean():.2f}")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Hook Rate", f"{df['Hook Rate (%)'].mean():.2f}%")
col2.metric("Hold Rate", f"{df['Hold Rate (%)'].mean():.2f}%")
col3.metric("CVR", f"{df['CVR (%)'].mean():.2f}%")
col4.metric("ROAS Estimado", f"{df['ROAS Estimado'].mean():.2f}")

# Tabela com link clicável
st.subheader("📋 Anúncios")
show_cols = ["date", "ad_name", "campaign_name", "CTR (%)", "CPC (R$)", "CPA (R$)", "CPP (R$)", "ROAS Real", "Ver Anúncio"]
st.dataframe(df[show_cols].sort_values("CTR (%)", ascending=False).reset_index(drop=True), use_container_width=True)

# Gráfico de Funil
st.subheader("📉 Funil de Conversão")
funnel_data = {
    "Etapa": ["Impressões", "Cliques", "Carrinhos", "Compras"],
    "Valor": [
        df["impressions"].sum(),
        df["clicks"].sum(),
        df["add_to_cart"].sum(),
        df["purchase"].sum()
    ]
}
fig_funnel = px.funnel(pd.DataFrame(funnel_data), x="Valor", y="Etapa", title="Funil de Conversão")
st.plotly_chart(fig_funnel, use_container_width=True)

# ROAS: Real vs Estimado
st.subheader("📊 ROAS: Real vs Estimado")
fig_roas = px.scatter(
    df, x="ROAS Real", y="ROAS Estimado", hover_data=["ad_name", "campaign_name"],
    title="Comparação ROAS Real vs Estimado", trendline="ols"
)
st.plotly_chart(fig_roas, use_container_width=True)

# Análise de vídeo: Hook x Hold Rate
st.subheader("🎥 Análise de Vídeo: Hook Rate vs Hold Rate")
fig_video = px.scatter(
    df, x="Hook Rate (%)", y="Hold Rate (%)", size="impressions",
    hover_data=["ad_name", "campaign_name"], title="Hook vs Hold Rate"
)
st.plotly_chart(fig_video, use_container_width=True)
