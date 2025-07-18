import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
from dotenv import load_dotenv
import os
from auth import login

load_dotenv()


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def shopify_page():
    if not login():
        st.stop()
    st.title("Dashboard Shopify - All Weather")

    @st.cache_data(ttl=600)
    def carregar_dados():
        response = supabase.table("Shopify").select("*").execute()
        df = pd.DataFrame(response.data)
        df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
        return df

    df = carregar_dados()

    # Filtros
    start_date = st.sidebar.date_input("Data inicial", df['date'].min())
    end_date = st.sidebar.date_input("Data final", df['date'].max())
    filtro = df[(df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))]

    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Receita Total", f"R$ {filtro['price'].sum():,.0f}".replace(",", "."))
    col2.metric("Ticket Médio", f"R$ {filtro['price'].mean():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col3.metric("Pedidos", f"{filtro['order_number'].nunique():,}".replace(",", "."))
    # col4.metric("Descontos", f"R$ {filtro['discount'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    st.markdown("### Visão Geral")

    # Receita por dia
    st.subheader("Receita por Dia")
    receita_dia = filtro.groupby("date")["price"].sum()
    st.line_chart(receita_dia)

    # Receita por mês
    st.subheader("Receita por Mês")
    filtro["mes"] = filtro["date"].dt.strftime("%b/%y")
    receita_mes = filtro.groupby("mes")["price"].sum().sort_index()
    st.bar_chart(receita_mes)

    # Tratamento SKU
    df_sku = filtro[filtro['sku'].notnull() & filtro['sku'].str.match(r'^AW_ES_[A-Z]{2}_[A-Z]{2}_[A-Z0-9]+$')].copy()
    df_sku['tipo'] = df_sku['sku'].str.extract(r'^AW_ES_([A-Z]{2})_')
    df_sku['cor'] = df_sku['sku'].str.extract(r'^AW_ES_[A-Z]{2}_([A-Z]{2})_')
    df_sku['tamanho'] = df_sku['sku'].str.extract(r'^AW_ES_[A-Z]{2}_[A-Z]{2}_([A-Z0-9]+)')
    df_sku['compressao'] = df_sku['tipo'].map({'LC': 'Com', 'CC': 'Com', 'LS': 'Sem', 'CS': 'Sem'})
    df_sku['comprimento'] = df_sku['tipo'].map({'LC': 'Longo', 'LS': 'Longo', 'CC': 'Curto', 'CS': 'Curto'})

    # Gráficos
    st.subheader("Distribuição por Comprimento")
    fig = px.pie(df_sku, names='comprimento', title='Vendas por Comprimento', hole=0.4)
    st.plotly_chart(fig)

    st.subheader("Distribuição por Compressão")
    fig = px.pie(df_sku, names='compressao', title='Vendas por Compressão', hole=0.4)
    st.plotly_chart(fig)

    st.subheader("Distribuição por Cor")
    fig = px.pie(df_sku, names='cor', title='Vendas por Cor', hole=0.4)
    st.plotly_chart(fig)

    st.subheader("Distribuição por Tamanho")
    fig = px.pie(df_sku, names='tamanho', title='Vendas por Tamanho', hole=0.4)
    st.plotly_chart(fig)

    st.subheader("Top 10 SKUs - Percentual")
    sku_counts = df_sku['sku'].value_counts(normalize=True).head(10).reset_index()
    sku_counts.columns = ['sku', 'percentage']
    sku_counts['percentage'] = sku_counts['percentage'] * 100

    fig = px.bar(sku_counts, 
                 x='percentage', y='sku', 
                 orientation='h',
                 title='Top 10 SKUs - Percentual',
                 text=sku_counts['percentage'].apply(lambda x: f'{x:.1f}%'))

    fig.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig)
