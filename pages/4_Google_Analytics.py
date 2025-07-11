import streamlit as st
import pandas as pd
from supabase import create_client
from dotenv import load_dotenv
import os
from auth import login

# Carrega variáveis de ambiente
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Inicializa cliente Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

if not login():
    st.stop()

st.title('Dashboard de Performance - Google Analytics (All Weather)')

@st.cache_data(ttl=600)
def carregar_dados():
    response = supabase.table("googleAnalytics").select("*").execute()
    df = pd.DataFrame(response.data)
    df["date"] = pd.to_datetime(df["date"], format='%Y%m%d')
    colunas_numericas = ["adCost", "adClicks", "conversoes", "receitaCompras", "adImpressions"]
    df[colunas_numericas] = df[colunas_numericas].apply(pd.to_numeric, errors='coerce')
    return df

df = carregar_dados()

# Filtro por datas
data_inicio = st.sidebar.date_input("Data inicial", df['date'].min())
data_fim = st.sidebar.date_input("Data final", df['date'].max())
df_filtrado = df[(df['date'] >= pd.to_datetime(data_inicio)) & (df['date'] <= pd.to_datetime(data_fim))]

# KPIs principais
receita = df_filtrado['receitaCompras'].sum()
custo = df_filtrado['adCost'].sum()
cliques = df_filtrado['adClicks'].sum()
impressoes = df_filtrado['adImpressions'].sum()

roas = receita / custo if custo > 0 else 0
ctr = (cliques / impressoes) * 100 if impressoes > 0 else 0
cpm = (custo / impressoes) * 1000 if impressoes > 0 else 0
cpc = custo / cliques if cliques > 0 else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("ROAS", f"{roas:.2f}x")
col2.metric("CTR", f"{ctr:.2f}%")
col3.metric("CPM", f"R$ {cpm:.2f}")
col4.metric("CPC", f"R$ {cpc:.2f}")

# Gráficos de Métricas Diárias
with st.expander("Análise Diária"):
    df_filtrado["ROAS"] = df_filtrado.apply(lambda x: x['receitaCompras']/x['adCost'] if x['adCost'] > 0 else 0, axis=1)
    df_filtrado["CTR"] = df_filtrado.apply(lambda x: (x['adClicks']/x['adImpressions'])*100 if x['adImpressions'] > 0 else 0, axis=1)
    df_filtrado["CPM"] = df_filtrado.apply(lambda x: (x['adCost']/x['adImpressions'])*1000 if x['adImpressions'] > 0 else 0, axis=1)
    df_filtrado["CPC"] = df_filtrado.apply(lambda x: x['adCost']/x['adClicks'] if x['adClicks'] > 0 else 0, axis=1)

    for kpi in ["ROAS", "CTR", "CPM", "CPC"]:
        st.subheader(f"{kpi} Diário")
        diario = df_filtrado.groupby("date")[kpi].mean().reset_index()
        st.line_chart(diario.set_index("date"))
