import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
from dotenv import load_dotenv
import os
from auth import login

# Carregando variáveis de ambiente
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Inicializando cliente Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

if not login():
    st.stop()

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

# Definindo intervalo de datas manualmente
start_date = pd.to_datetime("2024-04-01")
end_date   = pd.to_datetime("2024-07-11")

# Filtra as vendas pelo intervalo definido
df_filtrado = df_vendas.copy()
df_filtrado["data_manual"] = pd.to_datetime(
    pd.Series([start_date] * len(df_filtrado))
)

# Para simular o agrupamento diário, distribuímos uniformemente
# Isso é opcional caso queira agrupar de forma simples sem data real
df_filtrado = df_filtrado[
    (df_filtrado["data_manual"] >= start_date) &
    (df_filtrado["data_manual"] <= end_date)
]

# Agrupando a quantidade total por SKU
df_qty = df_filtrado.groupby("sku", as_index=False)["qty_total"].sum()

# Cálculo de média diária por SKU
dias_intervalo = (end_date - start_date).days + 1
df_qty["media_diaria"] = df_qty["qty_total"] / dias_intervalo
df_qty["demanda_120d"] = (df_qty["media_diaria"] * 120).round().astype(int)

# Pega estoque atual
df_qty["estoque_atual"] = df_qty["sku"].map(
    df_stock.set_index("sku")["stock"].to_dict()
).fillna(0).astype(int)

# Calcula reorder
df_qty["reorder_qty"] = (df_qty["demanda_120d"] - df_qty["estoque_atual"]).clip(lower=0)

# Renomeia e exibe
df_summary = df_qty.rename(columns={
    "sku": "SKU",
    "demanda_120d": "Demanda 120d",
    "estoque_atual": "Estoque Atual",
    "reorder_qty": "Reorder Qty"
})

st.subheader("Previsão Demanda 120d · usando intervalo manual e tabela vendas")
st.dataframe(
    df_summary[["SKU", "Demanda 120d", "Estoque Atual", "Reorder Qty"]]
    .style.format({
        "Demanda 120d": "{:,}",
        "Estoque Atual": "{:,}",
        "Reorder Qty": "{:,}"
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
