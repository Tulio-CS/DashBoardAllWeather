import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px

# Configurações do Supabase
SUPABASE_URL = "https://zktlbouraeqciijgzahn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InprdGxib3VyYWVxY2lpamd6YWhuIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTg0MjE2NSwiZXhwIjoyMDY1NDE4MTY1fQ.anqnVo2QyK6BZ88_kJIXs7wBNaDUtjlHVZ1ZLPGrtKg"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Carregar dados da tabela Shopify
@st.cache_data
def carregar_dados():
    response = supabase.table("Shopify").select("*").execute()
    df = pd.DataFrame(response.data)
    df["date"] = pd.to_datetime(df["date"],format="%Y-%m-%d")
    return df

df = carregar_dados()

st.title("Dashboard Shopify - All Weather")

# Filtros de data
start_date = st.sidebar.date_input("Data inicial", df['date'].min())
end_date = st.sidebar.date_input("Data final", df['date'].max())
filtro = df[(df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))]

# KPIs principais com formatação adequada
col1, col2, col3, col4 = st.columns(4)
col1.metric("Receita Total", f"R$ {filtro['price'].sum():,.0f}".replace(",", "."))
col2.metric("Ticket Médio", f"R$ {filtro['price'].mean():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
col3.metric("Pedidos", f"{filtro['order_number'].nunique():,}".replace(",", "."))
#col4.metric("Descontos", f"R$ {filtro['discount'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))


# Texto explicativo
st.markdown("###  Visão Geral")
st.write("Acompanhe abaixo os principais indicadores de desempenho de vendas. Os dados consideram o período selecionado no filtro lateral.")

# Gráfico de receita diária
st.subheader("Receita por Dia")
receita_dia = filtro.groupby("date")["price"].sum()
st.line_chart(receita_dia)

# Gráfico de receita mensal com nome dos meses
st.subheader("Receita por Mês")
filtro["mes"] = filtro["date"].dt.strftime("%b/%y")  # Ex: "Jun/25"
receita_mes = filtro.groupby("mes")["price"].sum().sort_index()
st.bar_chart(receita_mes)



# Extrair corretamente os componentes da SKU
df = df[df['sku'].notnull() & df['sku'].str.match(r'^AW_ES_[A-Z]{2}_[A-Z]{2}_[A-Z]+$')].copy()

df['tipo'] = df['sku'].str.extract(r'^AW_ES_([A-Z]{2})_')
df['cor'] = df['sku'].str.extract(r'^AW_ES_[A-Z]{2}_([A-Z]{2})_')
df['tamanho'] = df['sku'].str.extract(r'^AW_ES_[A-Z]{2}_[A-Z]{2}_([A-Z0-9]+)')

# Categorias auxiliares
df['compressao'] = df['tipo'].map({'LC': 'Com', 'CC': 'Com', 'LS': 'Sem', 'CS': 'Sem'})
df['comprimento'] = df['tipo'].map({'LC': 'Longo', 'LS': 'Longo', 'CC': 'Curto', 'CS': 'Curto'})



st.subheader("Distribuição por Comprimento")
fig = px.pie(df, names='comprimento', title='Vendas por Comprimento', hole=0.4)
st.plotly_chart(fig)

st.subheader("Distribuição por Compressão")
fig = px.pie(df, names='compressao', title='Vendas por Compressão', hole=0.4)
st.plotly_chart(fig)

st.subheader("Distribuição por Cor")
fig = px.pie(df, names='cor', title='Vendas por Cor', hole=0.4)
st.plotly_chart(fig)

st.subheader("Distribuição por Tamanho")
fig = px.pie(df, names='tamanho', title='Vendas por Tamanho', hole=0.4)
st.plotly_chart(fig)

st.subheader("Top 10 SKUs Vendidas")

sku_counts = df['sku'].value_counts().head(10).reset_index()
sku_counts.columns = ['sku', 'vendas']

fig = px.bar(sku_counts, 
              x='vendas', y='sku', 
              orientation='h', 
              title='Top 10 SKUs Vendidas',
              text='vendas')

fig.update_layout(yaxis={'categoryorder':'total ascending'})  # Ordena do menor para maior na horizontal
st.plotly_chart(fig)
