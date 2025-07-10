import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
from dotenv import load_dotenv
import os

# Carregando variáveis de ambiente
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Inicializando cliente Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("Dashboard Shopify - All Weather")

# 1) Carrega vendas Shopify
@st.cache_data(ttl=600)
def carregar_shopify():
    resp = supabase.table("Shopify").select("*").execute()
    df = pd.DataFrame(resp.data)
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
    return df

# 2) Carrega estoque atual por SKU
@st.cache_data(ttl=600)
def carregar_estoque():
    resp = supabase.table("estoque").select("*").execute()
    df = pd.DataFrame(resp.data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = (
        df.sort_values("timestamp")
          .groupby("sku", as_index=False)
          .last()[["sku","inventory_quantity"]]
          .rename(columns={"inventory_quantity":"stock"})
    )
    return df

# 3) Carrega vendas totais (tabela vendas)
@st.cache_data(ttl=600)
def carregar_vendas():
    resp = supabase.table("vendas").select("*").execute()
    df = pd.DataFrame(resp.data)
    # Limpa e converte Quantidade
    df["Quantidade"] = df["Quantidade"].fillna("0").str.replace(",", ".")
    df["qty_total"] = (
        pd.to_numeric(df["Quantidade"], errors="coerce")
          .fillna(0).astype(int)
    )
    # renomeia coluna de produto
    df = df.rename(columns={"Código do produto":"sku"})
    return df

df = carregar_shopify()
df_stock = carregar_estoque()
df_vendas = carregar_vendas()

# Filtros de data para Shopify
start_date = st.sidebar.date_input("Data inicial", df['date'].min())
end_date   = st.sidebar.date_input("Data final",   df['date'].max())
filtro     = df[(df['date']>=pd.to_datetime(start_date)) & (df['date']<=pd.to_datetime(end_date))]

# KPIs  
col1,col2,col3 = st.columns(3)
col1.metric("Receita Total", f"R$ {filtro['price'].sum():,.0f}".replace(",", "."))
col2.metric("Ticket Médio", f"R$ {filtro['price'].mean():,.2f}".replace(".",","))
col3.metric("Pedidos", f"{filtro['order_number'].nunique():,}".replace(",", "."))

st.markdown("### Visão Geral")

# Receita por dia
st.subheader("Receita por Dia")
todas_datas = pd.date_range(filtro["date"].min(), filtro["date"].max(), freq="D")
receita_dia = (
    filtro.groupby("date")["price"]
           .sum()
           .reindex(todas_datas, fill_value=0)
)
st.line_chart(receita_dia)

# Receita por mês
st.subheader("Receita por Mês")
filtro["mes"] = filtro["date"].dt.to_period("M").dt.to_timestamp()
receita_mes = filtro.groupby("mes")["price"].sum().sort_index()
fig = px.bar(
    receita_mes.reset_index(),
    x="mes", y="price",
    labels={"mes":"Mês","price":"Receita"},
    text_auto=".2s"
)
fig.update_layout(xaxis_tickformat="%b/%y")
st.plotly_chart(fig, use_container_width=True)

# Tratamento dos SKUs para distribuição
df_sku = filtro[
    filtro['sku'].notnull() &
    filtro['sku'].str.match(r'^AW_ES_[A-Z]{2}_[A-Z]{2}_[A-Z0-9]+$')
].copy()
df_sku['tipo']       = df_sku['sku'].str.extract(r'^AW_ES_([A-Z]{2})_')
df_sku['cor']        = df_sku['sku'].str.extract(r'^AW_ES_[A-Z]{2}_([A-Z]{2})_')
df_sku['tamanho']    = df_sku['sku'].str.extract(r'^AW_ES_[A-Z]{2}_[A-Z]{2}_([A-Z0-9]+)')
df_sku['compressao'] = df_sku['tipo'].map({'LC':'Com','CC':'Com','LS':'Sem','CS':'Sem'})
df_sku['comprimento']= df_sku['tipo'].map({'LC':'Longo','LS':'Longo','CC':'Curto','CS':'Curto'})

# Gráficos de distribuição
st.subheader("Distribuição por Comprimento")
fig = px.pie(df_sku, names='comprimento', hole=0.4)
st.plotly_chart(fig)

st.subheader("Distribuição por Compressão")
fig = px.pie(df_sku, names='compressao', hole=0.4)
st.plotly_chart(fig)

st.subheader("Distribuição por Cor")
fig = px.pie(df_sku, names='cor', hole=0.4)
st.plotly_chart(fig)

st.subheader("Distribuição por Tamanho")
fig = px.pie(df_sku, names='tamanho', hole=0.4)
st.plotly_chart(fig)

# --------------------------------------------------
# Gráfico de % de vendas por SKU (tabela vendas)
# --------------------------------------------------
st.subheader("Percentual de Vendas por SKU (tabela vendas)")

# resumo vendas totais
df_pct = (
    df_vendas.groupby("sku", as_index=False)["qty_total"]
             .sum()
)
total_all = df_pct["qty_total"].sum()
df_pct["percentage"] = df_pct["qty_total"] / total_all * 100

# ordenar e plotar todas as 32 SKUs
df_pct = df_pct.sort_values("percentage", ascending=True)
fig = px.bar(
    df_pct, x="percentage", y="sku",
    orientation="h", title="Percentual de Vendas por SKU",
    text=df_pct["percentage"].map(lambda x: f"{x:.1f}%")
)
fig.update_layout(yaxis=dict(categoryorder="total ascending"))
st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# Previsão Demanda 120d e Reorder Qty
# --------------------------------------------------
st.subheader("Previsão Demanda 120d e Reorder Qty (32 SKUs)")

# agrupa vendas diárias por SKU
df_daily = (
    df.groupby([df['sku'], df['date'].dt.normalize()])
      .size()
      .reset_index(name="y")
      .rename(columns={"date":"ds"})
)

H = 120
hoje = df_daily["ds"].max() if not df_daily.empty else pd.Timestamp.today()
skus = sorted(df_daily["sku"].dropna().unique())

rows = []
for sku in skus:
    df_s = df_daily[df_daily["sku"]==sku].sort_values("ds")
    if not df_s.empty:
        idx = pd.date_range(df_s.ds.min(), hoje, freq="D")
        df_s = df_s.set_index("ds").reindex(idx, fill_value=0).rename_axis("ds").reset_index()
        dias = (df_s.ds.max()-df_s.ds.min()).days + 1
        total = df_s["y"].sum()
        avg = total/dias if dias>0 else 0
    else:
        avg = 0
    demanda = int(round(avg * H))
    estoque = int(df_stock.loc[df_stock.sku==sku, "stock"].squeeze()) \
              if sku in df_stock.sku.values else 0
    reorder = max(0, demanda - estoque)
    rows.append({
        "SKU": sku,
        "Demanda 120d": demanda,
        "Estoque Atual": estoque,
        "Reorder Qty": reorder
    })

df_summary = pd.DataFrame(rows)

st.dataframe(
    df_summary.style.format({
        "Demanda 120d":"{:,}",
        "Estoque Atual":"{:,}",
        "Reorder Qty":"{:,}"
    }),
    use_container_width=True
)

# --------------------------------------------------
# Tabela completa Shopify
# --------------------------------------------------
st.subheader("Tabela Completa · Shopify")
df_visual = df.drop(columns=["id"]) if "id" in df.columns else df
st.dataframe(
    df_visual.sort_values("date", ascending=False).reset_index(drop=True),
    use_container_width=True
)
