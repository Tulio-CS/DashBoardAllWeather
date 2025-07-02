import streamlit as st
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
from supabase import create_client
import os
from statsmodels.stats.proportion import proportions_ztest


# Configuração da página
st.set_page_config(page_title="Clarity Insights", layout="wide")
st.title("Clarity Insights")

# Conectar ao Supabase
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_data(ttl=600)
def carregar_dados():
    insights = supabase.table("clarityInsights").select("*").execute()
    df_insights = pd.DataFrame(insights.data or [])
    df_insights["timestamp"] = pd.to_datetime(df_insights["timestamp"], errors="coerce")

    for col in ["sessionsCount", "totalBotSessionCount", "distinctUserCount", "averageScrollDepth", "totalTime"]:
        df_insights[col] = pd.to_numeric(df_insights[col], errors="coerce")

    df_insights = df_insights.dropna(subset=["sessionsCount"])

    scrolls = supabase.table("scrollData").select("*").execute()
    df_scroll = pd.DataFrame(scrolls.data or [])
    df_scroll["timestamp"] = pd.to_datetime(df_scroll["timestamp"], errors="coerce")

    for col in ["Scroll depth", "No of visitors", "% drop off"]:
        df_scroll[col] = pd.to_numeric(df_scroll[col], errors="coerce")

    return df_insights, df_scroll

df_insights, df_scroll = carregar_dados()

# Filtros
st.sidebar.header("Filtro de Períodos")
ver_tudo = st.sidebar.checkbox("Ver todos os dados", value=False)

if ver_tudo:
    df_combined_insights = df_insights.copy()
    df_combined_scroll = df_scroll.copy()
    df_combined_insights["Período"] = "Todos os dados"
    df_combined_scroll["Período"] = "Todos os dados"
else:
    min_date = min(df_insights["timestamp"].min(), df_scroll["timestamp"].min()).date()
    max_date = max(df_insights["timestamp"].max(), df_scroll["timestamp"].max()).date()

    st.sidebar.markdown("### Período A")
    periodo_a = st.sidebar.date_input("Data A", [min_date, min_date], min_value=min_date, max_value=max_date)

    st.sidebar.markdown("### Período B")
    periodo_b = st.sidebar.date_input("Data B", [max_date, max_date], min_value=min_date, max_value=max_date)

    if isinstance(periodo_a, tuple) and isinstance(periodo_b, tuple):
        df_a_insights = df_insights[
            (df_insights["timestamp"].dt.date >= periodo_a[0]) & (df_insights["timestamp"].dt.date <= periodo_a[1])
        ].copy()
        df_b_insights = df_insights[
            (df_insights["timestamp"].dt.date >= periodo_b[0]) & (df_insights["timestamp"].dt.date <= periodo_b[1])
        ].copy()

        df_a_scroll = df_scroll[
            (df_scroll["timestamp"].dt.date >= periodo_a[0]) & (df_scroll["timestamp"].dt.date <= periodo_a[1])
        ].copy()
        df_b_scroll = df_scroll[
            (df_scroll["timestamp"].dt.date >= periodo_b[0]) & (df_scroll["timestamp"].dt.date <= periodo_b[1])
        ].copy()

        df_a_insights["Período"] = "Período A"
        df_b_insights["Período"] = "Período B"
        df_a_scroll["Período"] = "Período A"
        df_b_scroll["Período"] = "Período B"

        df_combined_insights = pd.concat([df_a_insights, df_b_insights])
        df_combined_scroll = pd.concat([df_a_scroll, df_b_scroll])
    else:
        st.error("Selecione ambos os períodos corretamente.")
        st.stop()


# Gráfico scroll: Visitantes por profundidade
st.subheader("Visitantes por profundidade de scroll")
fig_scroll = px.bar(
    df_combined_scroll.sort_values("Scroll depth"),
    x="Scroll depth",
    y="No of visitors",
    color="Período",
    barmode="group",
    title="Visitantes por faixa de scroll",
    labels={"Scroll depth": "Scroll (%)", "No of visitors": "Visitantes"}
)
st.plotly_chart(fig_scroll, use_container_width=True)

# Gráfico acumulado
st.subheader("Percentual de visitantes que chegaram até pelo menos X% de scroll")
df_pct = []
for label, df in df_combined_scroll.groupby("Período"):
    df_sorted = df.sort_values("Scroll depth", ascending=False).copy()
    df_sorted["Visitantes acumulados"] = df_sorted["No of visitors"].cumsum()
    total_visitas = df_sorted["No of visitors"].sum()
    df_sorted["% acumulado"] = (df_sorted["Visitantes acumulados"] / total_visitas) * 100
    df_sorted["Período"] = label
    df_pct.append(df_sorted.sort_values("Scroll depth"))

df_scroll_pct_acum = pd.concat(df_pct)
fig_pct_acumulado = px.line(
    df_scroll_pct_acum,
    x="Scroll depth",
    y="% acumulado",
    color="Período",
    title="% de visitantes que chegaram até pelo menos cada faixa de scroll",
    labels={"Scroll depth": "Scroll (%)", "% acumulado": "Visitantes (%)"},
    markers=True
)
fig_pct_acumulado.update_traces(mode="lines+markers")
fig_pct_acumulado.update_layout(yaxis_ticksuffix="%")
st.plotly_chart(fig_pct_acumulado, use_container_width=True)

# Taxa de abandono
st.subheader("Taxa de Abandono por profundidade")
fig_drop = px.line(
    df_combined_scroll.sort_values("Scroll depth"),
    x="Scroll depth",
    y="% drop off",
    color="Período",
    markers=True,
    title="% de abandono por faixa de scroll"
)
st.plotly_chart(fig_drop, use_container_width=True)


st.subheader("Teste de Proporções por Faixa de Scroll")

# Slider para selecionar a faixa de scroll
scroll_min, scroll_max = st.slider(
    "Selecione a faixa de profundidade de scroll (%)",
    min_value=0,
    max_value=100,
    value=(20, 30),
    step=5
)

# Filtrar os dados por faixa de scroll
df_intervalo = df_combined_scroll[
    (df_combined_scroll["Scroll depth"] >= scroll_min) &
    (df_combined_scroll["Scroll depth"] <= scroll_max)
]

# Total de visitantes por período
total_a = df_combined_scroll[df_combined_scroll["Período"] == "Período A"]["No of visitors"].sum()
total_b = df_combined_scroll[df_combined_scroll["Período"] == "Período B"]["No of visitors"].sum()

# Visitantes na faixa por período
faixa_a = df_intervalo[df_intervalo["Período"] == "Período A"]["No of visitors"].sum()
faixa_b = df_intervalo[df_intervalo["Período"] == "Período B"]["No of visitors"].sum()

# Cálculo das proporções
prop_a = faixa_a / total_a if total_a > 0 else 0
prop_b = faixa_b / total_b if total_b > 0 else 0

# Exibição formatada
st.markdown(f"""
### Visitantes na faixa de scroll entre {scroll_min}% e {scroll_max}%:

- **Período A:** {faixa_a} de {total_a} visitantes → **{prop_a:.2%}**
- **Período B:** {faixa_b} de {total_b} visitantes → **{prop_b:.2%}**
""")

# Aplicar o teste
count = [faixa_a, faixa_b]
nobs = [total_a, total_b]

if all(n > 0 for n in count):  # Evita erro se não houver dados
    stat, pval = proportions_ztest(count, nobs)

    st.markdown(f"""
    ### Teste de Proporções para faixa de scroll entre {scroll_min}% e {scroll_max}%:

    - Visitantes na faixa:
      - **Período A:** {faixa_a} de {total_a} visitantes → **{prop_a:.2%}**
      - **Período B:** {faixa_b} de {total_b} visitantes → **{prop_b:.2%}**
    - Estatística z: `{stat:.4f}`
    - Valor-p: `{pval:.4f}`
    """)

    if pval < 0.05:
        st.success("✅ Diferença estatisticamente significativa na faixa de scroll!")
    else:
        st.info("ℹ️ Nenhuma diferença estatisticamente significativa na faixa de scroll.")
else:
    st.warning("Não há dados suficientes para realizar o teste nesta faixa.")


st.subheader("Teste de Proporções: Visitantes que chegaram até X% de scroll")

# Seleção do ponto de corte
scroll_cutoff = st.slider("Escolha a profundidade de scroll (%) para o teste", min_value=0, max_value=100, value=75, step=5)

# Filtrar os dados para esse ponto
df_cutoff = df_scroll_pct_acum[df_scroll_pct_acum["Scroll depth"] == scroll_cutoff]

if df_cutoff["Período"].nunique() < 2:
    st.warning("Não há dados suficientes para ambos os períodos nesse ponto de scroll.")
else:
    # Obter os valores para cada período
    a_pct = df_cutoff[df_cutoff["Período"] == "Período A"]["% acumulado"].values[0]
    b_pct = df_cutoff[df_cutoff["Período"] == "Período B"]["% acumulado"].values[0]

    # Obter os totais de visitantes para cada período
    total_a = df_combined_scroll[df_combined_scroll["Período"] == "Período A"]["No of visitors"].sum()
    total_b = df_combined_scroll[df_combined_scroll["Período"] == "Período B"]["No of visitors"].sum()

    # Calcular o número de sucessos (visitantes que chegaram até o ponto)
    success_a = int((a_pct / 100) * total_a)
    success_b = int((b_pct / 100) * total_b)

    # Aplicar o teste z para proporções
    count = [success_a, success_b]
    nobs = [total_a, total_b]
    stat, pval = proportions_ztest(count, nobs)

    st.markdown(f"""
    **Resultados do Teste de Proporções para {scroll_cutoff}% de scroll:**

    - Visitantes que chegaram até {scroll_cutoff}%:
        - Período A: {success_a} de {total_a} visitantes ({a_pct:.2f}%)
        - Período B: {success_b} de {total_b} visitantes ({b_pct:.2f}%)
    - Estatística z: `{stat:.4f}`
    - Valor-p: `{pval:.4f}`
    """)

    if pval < 0.05:
        st.success("✅ Diferença estatisticamente significativa! A mudança no site teve impacto no comportamento de scroll.")
    else:
        st.info("ℹ️ Sem diferença estatisticamente significativa. A mudança pode não ter afetado o comportamento de scroll.")


# Agrupar por data e formatar para string
df_combined_scroll["date"] = df_combined_scroll["timestamp"].dt.date
df_combined_scroll["date_str"] = df_combined_scroll["date"].astype(str)

# Scroll médio por dia
scroll_avg = df_combined_scroll.groupby(["date_str", "Período"]).apply(
    lambda x: (x["Scroll depth"] * x["No of visitors"]).sum() / x["No of visitors"].sum()
).reset_index(name="avg_scroll")

# ===============================
# Comparação de sessionsCount por métrica (excluindo métricas irrelevantes)
# ===============================

metricas_remover = ["PageTitle", "ReferrerUrl", "Device", "OS", "Browser"]

if "metricName" in df_combined_insights.columns and "sessionsCount" in df_combined_insights.columns:
    st.subheader("Soma de Sessões por Métrica (clarityInsights)")

    # Filtrar métricas indesejadas
    df_metricas_filtrado = df_combined_insights[~df_combined_insights["metricName"].isin(metricas_remover)]

    soma_metricas = (
        df_metricas_filtrado
        .groupby(["Período", "metricName"])["sessionsCount"]
        .sum()
        .reset_index(name="Soma de Sessões")
        .sort_values(by="Soma de Sessões", ascending=False)
    )

    fig_metricas_soma = px.bar(
        soma_metricas,
        x="metricName",
        y="Soma de Sessões",
        color="Período",
        barmode="group",
        title="Soma de Sessões por Métrica em cada Período (excluindo métricas irrelevantes)",
        labels={"metricName": "Métrica", "Soma de Sessões": "Total de Sessões"}
    )
    fig_metricas_soma.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_metricas_soma, use_container_width=True)

    with st.expander("Ver tabela detalhada"):
        st.dataframe(soma_metricas, use_container_width=True)


# Tabelas
st.subheader("Tabela de Clarity Insights")
st.dataframe(df_combined_insights.sort_values("sessionsCount", ascending=False).reset_index(drop=True), use_container_width=True)

st.subheader("Tabela de Scroll")
st.dataframe(df_combined_scroll.sort_values(["timestamp", "Scroll depth"]).reset_index(drop=True), use_container_width=True)
