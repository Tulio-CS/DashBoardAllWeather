import os
import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
from dotenv import load_dotenv

# 1. Configuração da página
st.set_page_config(page_title="Meta Ads Dashboard", layout="wide")
st.title("Meta Ads Dashboard · All Weather")

# 2. Conexão com Supabase
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase     = create_client(SUPABASE_URL, SUPABASE_KEY)

# 3. Carregar e tratar dados
@st.cache_data(ttl=600)
def load_data():
    resp = supabase.table("metaAds").select("*").execute()
    df = pd.DataFrame(resp.data or [])

    # converter datas e extrair apenas date
    for col in ["date_start", "date_stop", "date"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")
        if df[col].dt.tz is not None:
            df[col] = df[col].dt.tz_convert("UTC").dt.tz_localize(None)
    df["date"] = df["date"].dt.date

    # IDs e status como string
    df["ad_id"]       = df["ad_id"].astype(str).str.strip()
    df["campaign_id"] = df["campaign_id"].astype(str).str.strip()
    df["ad_status"]   = df["ad_status"].astype(str)

    # colunas numéricas
    num_cols = [
        "impressions","reach","frequency","clicks","spend",
        "omni_add_to_cart","add_payment_info","purchase"
    ]
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce").fillna(0)

    # métricas derivadas
    df["CTR (%)"]               = (df["clicks"]/df["impressions"]*100).round(2).fillna(0)
    df["CPC (R$)"]              = (df["spend"]/df["clicks"]).replace([pd.NA, float("inf")],0).round(2)
    df["CPM (R$)"]              = (df["spend"]/df["impressions"]*1000).replace([pd.NA, float("inf")],0).round(2)
    df["CPA (R$)"]              = (df["spend"]/df["omni_add_to_cart"]).replace([pd.NA, float("inf")],0).round(2)
    df["AOV (R$)"]              = (df["purchase"]/df["omni_add_to_cart"]).replace([pd.NA, float("inf")],0).round(2)
    df["Payment Info Rate (%)"] = (df["add_payment_info"]/df["omni_add_to_cart"]*100)\
                                      .replace([pd.NA, float("inf")],0).round(2)
    df["ROAS Real"]             = (df["purchase"]/df["spend"]).replace([pd.NA, float("inf")],0).round(2)
    df["ROAS Estimado"]         = ((df["omni_add_to_cart"]*df["AOV (R$)"])/df["spend"])\
                                      .replace([pd.NA, float("inf")],0).round(2)
    return df

df = load_data()

# 4. Filtros na sidebar
st.sidebar.header("Filtros")
min_date, max_date = df["date"].min(), df["date"].max()
start_date, end_date = st.sidebar.date_input(
    "Período de ingestão", [min_date, max_date],
    min_value=min_date, max_value=max_date
)
status_sel = st.sidebar.multiselect(
    "Status do anúncio",
    options=df["ad_status"].unique(),
    default=df["ad_status"].unique()
)

df = df[
    (df["date"] >= start_date) &
    (df["date"] <= end_date) &
    (df["ad_status"].isin(status_sel))
]

# 5. KPIs iniciais
tot_imp      = int(df["impressions"].sum())
tot_reach    = int(df["reach"].sum())
avg_freq     = df["frequency"].mean() if not df.empty else 0
tot_click    = int(df["clicks"].sum())
tot_spend    = df["spend"].sum()
tot_cart     = int(df["omni_add_to_cart"].sum())
tot_info     = int(df["add_payment_info"].sum())
tot_rev      = df["purchase"].sum()

ctr       = tot_click/tot_imp*100 if tot_imp else 0
cpc       = tot_spend/tot_click if tot_click else 0
cpm       = tot_spend/tot_imp*1000 if tot_imp else 0
roas_real = tot_rev/tot_spend if tot_spend else 0
roas_est  = (tot_cart*(tot_rev/tot_cart)/tot_spend) if (tot_cart and tot_spend) else 0
avg_cpa   = df["CPA (R$)"].mean()
avg_aov   = df["AOV (R$)"].mean()
avg_pir   = df["Payment Info Rate (%)"].mean()

# Linha de KPIs (4 colunas)
row1 = st.columns(4)
row1[0].metric("Impressões", f"{tot_imp:,}")
row1[1].metric("Alcance", f"{tot_reach:,}")
row1[2].metric("Frequência média", f"{avg_freq:.2f}")
row1[3].metric("Cliques", f"{tot_click:,}")

row2 = st.columns(4)
row2[0].metric("Gasto (R$)", f"R$ {tot_spend:,.2f}")
row2[1].metric("Carrinhos", f"{tot_cart:,}")
row2[2].metric("Add Payment Info", f"{tot_info:,}")
row2[3].metric("Receita (R$)", f"R$ {tot_rev:,.2f}")

row3 = st.columns(4)
row3[0].metric("CTR (%)", f"{ctr:.2f}")
row3[1].metric("CPC (R$)", f"R$ {cpc:.2f}")
row3[2].metric("CPM (R$)", f"R$ {cpm:.2f}")
row3[3].metric("CPA (R$)", f"R$ {avg_cpa:.2f}")

row4 = st.columns(4)
row4[0].metric("AOV (R$)", f"R$ {avg_aov:.2f}")
row4[1].metric("Payment Info Rate (%)", f"{avg_pir:.2f}")
row4[2].metric("ROAS Real (x)", f"{roas_real:.2f}")
row4[3].metric("ROAS Estimado (x)", f"{roas_est:.2f}")

# 6. Tabela completa
st.header("Tabela Completa de Anúncios")
st.dataframe(
    df.sort_values("date_start", ascending=False).reset_index(drop=True),
    use_container_width=True
)

# 7. Evolução Diária
st.subheader("Evolução Diária: Gastos, Cliques, Carrinhos e Receita")
evo = df.groupby("date")[["spend","clicks","omni_add_to_cart","purchase"]].sum().reset_index()
fig1 = px.line(
    evo, x="date", y=["spend","clicks","omni_add_to_cart","purchase"],
    labels={"value":"Total","variable":"Métrica"},
    title="Evolução ao Longo do Tempo"
)
st.plotly_chart(fig1, use_container_width=True)

# 8. Distribuição por Status
st.subheader("Distribuição por Status de Anúncio")
status_df = df["ad_status"].value_counts().rename_axis("Status").reset_index(name="Contagem")
fig2 = px.pie(status_df, names="Status", values="Contagem", hole=0.4)
st.plotly_chart(fig2, use_container_width=True)

# 9. Top 10 Anúncios por Métrica
st.subheader("Top 10 Anúncios por Métrica")
def plot_top(metric, title, asc=False):
    top = df.sort_values(metric, ascending=asc).head(10)
    fig = px.bar(top, x="ad_id", y=metric, text=metric, title=title)
    fig.update_xaxes(type="category")
    st.plotly_chart(fig, use_container_width=True)

plot_top("CTR (%)",      "Top 10 por CTR")
plot_top("CPC (R$)",     "Top 10 por Menor CPC", asc=True)
plot_top("CPM (R$)",     "Top 10 por Menor CPM", asc=True)
plot_top("omni_add_to_cart", "Top 10 por Carrinhos")
plot_top("purchase",     "Top 10 por Receita")
plot_top("ROAS Real",    "Top 10 por ROAS Real")

# 10. Desempenho por Campanha
st.subheader("Desempenho por Campanha")
camp = df.groupby("campaign_id").agg({
    "impressions":"sum","reach":"sum","frequency":"mean",
    "clicks":"sum","spend":"sum","omni_add_to_cart":"sum",
    "add_payment_info":"sum","purchase":"sum"
}).reset_index()
camp["CTR (%)"]               = (camp["clicks"]/camp["impressions"]*100).round(2)
camp["CPC (R$)"]              = (camp["spend"]/camp["clicks"]).replace([pd.NA,float("inf")],0).round(2)
camp["CPM (R$)"]              = (camp["spend"]/camp["impressions"]*1000).round(2)
camp["CPA (R$)"]              = (camp["spend"]/camp["omni_add_to_cart"]).replace([pd.NA,float("inf")],0).round(2)
camp["AOV (R$)"]              = (camp["purchase"]/camp["omni_add_to_cart"]).replace([pd.NA,float("inf")],0).round(2)
camp["Payment Info Rate (%)"]= (camp["add_payment_info"]/camp["omni_add_to_cart"]*100)\
                                   .replace([pd.NA,float("inf")],0).round(2)
camp["ROAS Real"]             = (camp["purchase"]/camp["spend"]).replace([pd.NA,float("inf")],0).round(2)
camp["ROAS Estimado"]         = ((camp["omni_add_to_cart"]*camp["AOV (R$)"])/camp["spend"])\
                                   .replace([pd.NA,float("inf")],0).round(2)

fig3 = px.bar(
    camp.sort_values("ROAS Real", ascending=False),
    x="campaign_id", y="ROAS Real", text="ROAS Real",
    title="ROAS Real por Campanha"
)
fig3.update_xaxes(type="category")
st.plotly_chart(fig3, use_container_width=True)
