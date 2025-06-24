import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
from dotenv import load_dotenv
import os

st.set_page_config(page_title="Facebook Ads", layout="wide", page_icon="📣")
st.title("Facebook Ads · All Weather Dashboard")

# Supabase
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
AD_ACCOUNT_ID = os.getenv("AD_ACCOUNT_ID")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_data(ttl=600)
def carregar_ads():
    response = supabase.table("metaAds").select("*").execute()
    df = pd.DataFrame(response.data)

    # Conversão de colunas
    df["date_start"] = pd.to_datetime(df["date_start"])
    df["date"] = pd.to_datetime(df["date"])
    df["ad_id"] = df["ad_id"].astype(str).str.strip()
    df["campaign_id"] = df["campaign_id"].astype(str).str.strip()

    colunas_num = [
        "impressions", "clicks", "spend", "omni_add_to_cart_sum"
    ]
    df[colunas_num] = df[colunas_num].apply(pd.to_numeric, errors="coerce")

    # Métricas
    df["CTR (%)"] = (df["clicks"] / df["impressions"]) * 100
    df["CPC"] = df["spend"] / df["clicks"]
    df["CPM"] = df["spend"] / df["impressions"] * 1000
    df["ROAS Estimado"] = (df["omni_add_to_cart_sum"] * (df["spend"] / df["omni_add_to_cart_sum"])) / df["spend"]
    df["Link"] = df["ad_id"].apply(lambda x: f"[Ver Anúncio](https://facebook.com/adsmanager/manage/ad/{AD_ACCOUNT_ID}/{x})")

    return df

df = carregar_ads()

# Filtro por data de ingestão
st.sidebar.subheader("📅 Filtro por Ingestão")
start, end = st.sidebar.date_input("Intervalo", [df["date"].min(), df["date"].max()])
#df = df[(df["date"] >= pd.to_datetime(start)) & (df["date"] <= pd.to_datetime(end))]

# KPIs totais
st.markdown("### 📊 Métricas Gerais do Período")

total_spend = df["spend"].sum()
total_clicks = df["clicks"].sum()
total_impressions = df["impressions"].sum()
total_convs = df["omni_add_to_cart_sum"].sum()

ctr = (total_clicks / total_impressions * 100) if total_impressions else 0
cpc = total_spend / total_clicks if total_clicks else 0
cpm = total_spend / total_impressions * 1000 if total_impressions else 0
cpr = total_spend / total_convs if total_convs else 0
vmc = total_spend / total_convs if total_convs else 0
roas = (total_convs * vmc) / total_spend if total_spend else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("CTR (%)", f"{ctr:.2f}")
col2.metric("CPC (R$)", f"R$ {cpc:.2f}")
col3.metric("CPM (R$)", f"R$ {cpm:.2f}")
col4.metric("CPR (R$)", f"R$ {cpr:.2f}")

col5, col6, col7 = st.columns(3)
col5.metric("Conversões", f"{int(total_convs)}")
col6.metric("Valor Médio Conversão", f"R$ {vmc:.2f}")
col7.metric("ROAS Estimado", f"{roas:.2f}x")

# Tabela com links
st.subheader("📋 Tabela de Anúncios")
colunas = [
    "date_start", "ad_id", "campaign_id", "impressions", "clicks", "spend",
    "omni_add_to_cart_sum", "CTR (%)", "CPC", "CPM", "ROAS Estimado", "Link"
]
st.dataframe(df[colunas].sort_values("date_start", ascending=False).round(2), use_container_width=True)


top_ads = df.copy()
top_ads = top_ads[top_ads["spend"] > 0]  # garante que ROAS válido
top_ads["ROAS Estimado"] = (top_ads["omni_add_to_cart_sum"] * (top_ads["spend"] / top_ads["omni_add_to_cart_sum"])) / top_ads["spend"]
top_ads = top_ads.sort_values("ROAS Estimado", ascending=False).head(10)

# Criar coluna de links clicáveis
top_ads["🔗 Visualizar"] = top_ads["ad_id"].apply(
    lambda x: f"[Ver Anúncio](https://facebook.com/adsmanager/manage/ad/{AD_ACCOUNT_ID}/{x})"
)


st.subheader("🏅 Melhores Anúncios - ROAS Estimado")
st.markdown(
    top_ads[["date_start", "ad_id", "campaign_id", "ROAS Estimado", "spend", "clicks", "🔗 Visualizar"]]
    .round(2)
    .rename(columns={
        "date_start": "Data",
        "ad_id": "ID do Anúncio",
        "campaign_id": "Campanha",
        "spend": "Investimento (R$)",
        "clicks": "Cliques"
    })
    .to_markdown(index=False),
    unsafe_allow_html=True
)






# Gráfico 1: Evolução por data de ingestão
st.subheader("🕓 Evolução Diária por Data de Ingestão")
evolucao = df.groupby("date")[["spend", "clicks"]].sum().reset_index()
fig = px.line(evolucao, x="date", y=["spend", "clicks"], markers=True)
st.plotly_chart(fig, use_container_width=True)

# Gráfico 2: CTR por ad_id
st.subheader("🎯 CTR por Anúncio")
fig = px.bar(
    df.sort_values("CTR (%)", ascending=False).head(10),
    x="ad_id", y="CTR (%)", text="CTR (%)"
)
fig.update_xaxes(type="category")
st.plotly_chart(fig, use_container_width=True)

# Gráfico 3: CPC por ad_id
st.subheader("💸 CPC por Anúncio")
fig = px.bar(
    df.sort_values("CPC").head(10),
    x="ad_id", y="CPC", text="CPC"
)
fig.update_xaxes(type="category")
st.plotly_chart(fig, use_container_width=True)

# Gráfico 4: ROAS por ad_id
st.subheader("🏆 ROAS Estimado por Anúncio")
fig = px.bar(
    df.sort_values("ROAS Estimado", ascending=False).head(10),
    x="ad_id", y="ROAS Estimado", text="ROAS Estimado"
)
fig.update_xaxes(type="category")
st.plotly_chart(fig, use_container_width=True)

# Gráfico 5: CTR por campanha
st.subheader("🎯 CTR por Campanha")
camp_ctr = df.groupby("campaign_id").agg({"clicks": "sum", "impressions": "sum"}).reset_index()
camp_ctr["CTR (%)"] = (camp_ctr["clicks"] / camp_ctr["impressions"]) * 100
fig = px.bar(camp_ctr.sort_values("CTR (%)", ascending=False), x="campaign_id", y="CTR (%)", text="CTR (%)")
fig.update_xaxes(type="category")
st.plotly_chart(fig, use_container_width=True)

# Gráfico 6: CPC por campanha
st.subheader("💰 CPC por Campanha")
camp_cpc = df.groupby("campaign_id").agg({"spend": "sum", "clicks": "sum"}).reset_index()
camp_cpc["CPC"] = camp_cpc["spend"] / camp_cpc["clicks"]
fig = px.bar(camp_cpc.sort_values("CPC"), x="campaign_id", y="CPC", text="CPC")
fig.update_xaxes(type="category")
st.plotly_chart(fig, use_container_width=True)

# Gráfico 7: ROAS por campanha
st.subheader("📈 ROAS Estimado por Campanha")
camp_roas = df.groupby("campaign_id").agg({
    "spend": "sum",
    "omni_add_to_cart_sum": "sum"
}).reset_index()
camp_roas["ROAS Estimado"] = (camp_roas["omni_add_to_cart_sum"] * (camp_roas["spend"] / camp_roas["omni_add_to_cart_sum"])) / camp_roas["spend"]
fig = px.bar(camp_roas.sort_values("ROAS Estimado", ascending=False), x="campaign_id", y="ROAS Estimado", text="ROAS Estimado")
fig.update_xaxes(type="category")
st.plotly_chart(fig, use_container_width=True)
