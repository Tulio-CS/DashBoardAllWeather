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

# ==============================
# Gráficos básicos
# ==============================

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

# ==========================================
# Gráfico acumulado correto: base 5%
# ==========================================

st.subheader("Percentual de visitantes que chegaram até pelo menos X% de scroll (Funil)")
df_pct = []

for label, df in df_combined_scroll.groupby("Período"):
    # Organize para o funil: do topo para o fundo (descendente)
    df_sorted = df.sort_values("Scroll depth", ascending=False).copy()
    df_sorted["Visitantes acumulados"] = df_sorted["No of visitors"].cumsum()
    # O total correto é o número de visitantes na menor faixa (normalmente 5%)
    total_visitas = df_sorted["No of visitors"].iloc[-1] if not df_sorted.empty else 1
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

# ===================================
# Teste de Proporções faixa a faixa (5 em 5)
# ===================================
st.subheader("Análise de Proporções por Faixas de Scroll (5 em 5%)")

resultados = []
faixas = sorted(df_combined_scroll["Scroll depth"].unique())
# Considere as faixas em ordem crescente e de 5 em 5%
for depth in faixas:
    faixa = df_combined_scroll[df_combined_scroll["Scroll depth"] == depth]
    # total de visitantes = visitantes na menor faixa (topo do funil)
    total_a = df_combined_scroll[(df_combined_scroll["Período"] == "Período A") & 
                                (df_combined_scroll["Scroll depth"] == faixas[0])]["No of visitors"].sum()
    total_b = df_combined_scroll[(df_combined_scroll["Período"] == "Período B") & 
                                (df_combined_scroll["Scroll depth"] == faixas[0])]["No of visitors"].sum()
    faixa_a = faixa[faixa["Período"] == "Período A"]["No of visitors"].sum()
    faixa_b = faixa[faixa["Período"] == "Período B"]["No of visitors"].sum()

    if total_a > 0 and total_b > 0:
        prop_a = faixa_a / total_a
        prop_b = faixa_b / total_b

        count = [faixa_a, faixa_b]
        nobs = [total_a, total_b]

        if all(n > 0 for n in nobs):
            stat, pval = proportions_ztest(count, nobs)
            if pval < 0.05:
                if prop_b > prop_a:
                    status = "✅ Melhorou"
                else:
                    status = "❌ Piorou"
            else:
                status = "⚖️ Inconclusivo"
            resultados.append({
                "Faixa": f"{depth}%",
                "Período A (%)": f"{prop_a:.2%}",
                "Período B (%)": f"{prop_b:.2%}",
                "Valor-p": round(pval, 4),
                "Resultado": status
            })

# Mostrar resultados em tabela
df_resultados = pd.DataFrame(resultados)
st.dataframe(df_resultados, use_container_width=True)

# Mostrar resumo
melhorou = df_resultados[df_resultados["Resultado"] == "✅ Melhorou"]
piorou = df_resultados[df_resultados["Resultado"] == "❌ Piorou"]

st.markdown("### 📊 Resumo da Análise")
st.markdown(f"- Faixas que **melhoraram**: {', '.join(melhorou['Faixa']) if not melhorou.empty else 'Nenhuma'}")
st.markdown(f"- Faixas que **pioraram**: {', '.join(piorou['Faixa']) if not piorou.empty else 'Nenhuma'}")

# Teste interativo faixa customizada (opcional)
st.subheader("Teste de Proporções por Faixa de Scroll (customizável)")

scroll_value = st.slider(
    "Selecione a profundidade de scroll (%) para o teste",
    min_value=int(min(faixas)), max_value=int(max(faixas)), value=int(faixas[2]), step=5
)

# total no topo do funil
total_a = df_combined_scroll[(df_combined_scroll["Período"] == "Período A") & 
                            (df_combined_scroll["Scroll depth"] == faixas[0])]["No of visitors"].sum()
total_b = df_combined_scroll[(df_combined_scroll["Período"] == "Período B") & 
                            (df_combined_scroll["Scroll depth"] == faixas[0])]["No of visitors"].sum()
# visitantes na faixa
faixa_a = df_combined_scroll[(df_combined_scroll["Período"] == "Período A") & 
                            (df_combined_scroll["Scroll depth"] == scroll_value)]["No of visitors"].sum()
faixa_b = df_combined_scroll[(df_combined_scroll["Período"] == "Período B") & 
                            (df_combined_scroll["Scroll depth"] == scroll_value)]["No of visitors"].sum()

prop_a = faixa_a / total_a if total_a > 0 else 0
prop_b = faixa_b / total_b if total_b > 0 else 0

st.markdown(f"""
### Visitantes que chegaram até {scroll_value}% de scroll:

- **Período A:** {faixa_a} de {total_a} visitantes → **{prop_a:.2%}**
- **Período B:** {faixa_b} de {total_b} visitantes → **{prop_b:.2%}**
""")

count = [faixa_a, faixa_b]
nobs = [total_a, total_b]

if all(n > 0 for n in nobs):
    stat, pval = proportions_ztest(count, nobs)
    st.markdown(f"""
    - Estatística z: `{stat:.4f}`
    - Valor-p: `{pval:.4f}`
    """)
    if pval < 0.05:
        if prop_b > prop_a:
            st.success("✅ O teste foi um sucesso: houve **melhora significativa** no engajamento nessa faixa de scroll.")
        else:
            st.error("❌ O teste **piorou significativamente** o engajamento nessa faixa de scroll.")
    else:
        st.info("ℹ️ O teste não apresentou mudança estatisticamente significativa. Resultado inconclusivo.")
else:
    st.warning("Não há dados suficientes para realizar o teste nesta faixa.")

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
