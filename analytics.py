import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def analytics_page():
    st.title('Dashboard Google Analytics - All Weather')

    @st.cache_data
    def carregar_dados_google():
        response = supabase.table("googleAnalytics").select("*").execute()
        df = pd.DataFrame(response.data)
        df["date"] = pd.to_datetime(df["date"], format='%Y%m%d')
        df[["adCost", "adClicks", "conversoes", "receitaCompras", "adImpressions"]] = \
            df[["adCost", "adClicks", "conversoes", "receitaCompras", "adImpressions"]].apply(pd.to_numeric, errors='coerce')
        return df

    df = carregar_dados_google()

    # Filtros
    start_date = st.sidebar.date_input("Data inicial", df['date'].min())
    end_date = st.sidebar.date_input("Data final", df['date'].max())
    filtro = df[(df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))]

    # KPIs
    total_receita = filtro['receitaCompras'].sum()
    total_custo = filtro['adCost'].sum()
    total_cliques = filtro['adClicks'].sum()
    total_impressao = filtro['adImpressions'].sum()

    roas = total_receita / total_custo if total_custo > 0 else 0
    ctr = (total_cliques / total_impressao) * 100 if total_impressao > 0 else 0
    cpm = (total_custo / total_impressao) * 1000 if total_impressao > 0 else 0
    cpc = total_custo / total_cliques if total_cliques > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("ROAS", f"{roas:.2f}x")
    col2.metric("CTR", f"{ctr:.2f}%")
    col3.metric("CPM", f"R$ {cpm:.2f}")
    col4.metric("CPC", f"R$ {cpc:.2f}")

    # ROAS diário
    st.subheader("ROAS Diário")
    filtro['ROAS'] = filtro.apply(lambda x: x['receitaCompras']/x['adCost'] if x['adCost'] > 0 else 0, axis=1)
    roas_diario = filtro.groupby('date')['ROAS'].mean().reset_index()
    st.line_chart(roas_diario.set_index('date'))

    # CTR diário
    st.subheader("CTR Diário (%)")
    filtro['CTR'] = filtro.apply(lambda x: (x['adClicks']/x['adImpressions'])*100 if x['adImpressions'] > 0 else 0, axis=1)
    ctr_diario = filtro.groupby('date')['CTR'].mean().reset_index()
    st.line_chart(ctr_diario.set_index('date'))

    # CPM diário
    st.subheader("CPM Diário (R$)")
    filtro['CPM'] = filtro.apply(lambda x: (x['adCost']/x['adImpressions'])*1000 if x['adImpressions'] > 0 else 0, axis=1)
    cpm_diario = filtro.groupby('date')['CPM'].mean().reset_index()
    st.line_chart(cpm_diario.set_index('date'))

    # CPC diário
    st.subheader("CPC Diário (R$)")
    filtro['CPC'] = filtro.apply(lambda x: x['adCost']/x['adClicks'] if x['adClicks'] > 0 else 0, axis=1)
    cpc_diario = filtro.groupby('date')['CPC'].mean().reset_index()
    st.line_chart(cpc_diario.set_index('date'))
