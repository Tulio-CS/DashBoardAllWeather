import streamlit as st
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
from supabase import create_client
import os
from statsmodels.stats.proportion import proportions_ztest
from auth import login

# Configuração da página
st.set_page_config(page_title="Clarity Insights", layout="wide")
st.title("Clarity Insights")

# Conectar ao Supabase
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

if not login():
    st.stop()

@st.cache_data(ttl=600)
def carregar_dados_scroll():
    scrolls = supabase.table("scrollData").select("*").execute()
    df_scroll = pd.DataFrame(scrolls.data or [])
    df_scroll["timestamp"] = pd.to_datetime(df_scroll["timestamp"], errors="coerce")

    for col in ["Scroll depth", "No of visitors", "% drop off"]:
        df_scroll[col] = pd.to_numeric(df_scroll[col], errors="coerce")

    return df_scroll

@st.cache_data(ttl=600)
def carregar_dados_atencao():
    attention = supabase.table("attentionData").select("*").execute()
    df_attention = pd.DataFrame(attention.data or [])
    df_attention["timestamp"] = pd.to_datetime(df_attention["timestamp"], errors="coerce")

    # Convertendo 'Avg time spent' de formato de tempo para segundos (numérico)
    # Exemplo: '00:02:22' -> 142 segundos
    def time_to_seconds(time_str):
        if pd.isna(time_str) or not isinstance(time_str, str):
            return None
        parts = time_str.split(":")
        if len(parts) == 3:
            h, m, s = map(int, parts)
            return h * 3600 + m * 60 + s
        return None

    df_attention["Avg time spent"] = df_attention["Avg time spent"].apply(time_to_seconds)

    # Convertendo '% of session length' de string para float
    # Exemplo: '9.56%' -> 9.56
    df_attention["% of session length"] = df_attention["% of session length"].str.replace("%", "", regex=False).astype(float)

    for col in ["Scroll depth", "Avg time spent", "% of session length"]:
        df_attention[col] = pd.to_numeric(df_attention[col], errors="coerce")

    return df_attention

df_scroll = carregar_dados_scroll()
df_attention = carregar_dados_atencao()

# Filtros
st.sidebar.header("Filtro de Períodos")
ver_tudo = st.sidebar.checkbox("Ver todos os dados", value=False)

if ver_tudo:
    df_combined_scroll = df_scroll.copy()
    df_combined_scroll["Período"] = "Todos os dados"
    df_combined_attention = df_attention.copy()
    df_combined_attention["Período"] = "Todos os dados"
else:
    # Garantir que min_date e max_date sejam calculados apenas se os dataframes não estiverem vazios
    all_timestamps = pd.Series(dtype='datetime64[ns]')
    if not df_scroll.empty:
        all_timestamps = pd.concat([all_timestamps, df_scroll["timestamp"]])
    if not df_attention.empty:
        all_timestamps = pd.concat([all_timestamps, df_attention["timestamp"]])

    if not all_timestamps.empty:
        min_date = all_timestamps.min().date()
        max_date = all_timestamps.max().date()
    else:
        st.warning("Não há dados disponíveis para os períodos selecionados.")
        st.stop()

    st.sidebar.markdown("### Período A")
    periodo_a = st.sidebar.date_input("Data A", [min_date, min_date], min_value=min_date, max_value=max_date, key='periodo_a')

    st.sidebar.markdown("### Período B")
    periodo_b = st.sidebar.date_input("Data B", [max_date, max_date], min_value=min_date, max_value=max_date, key='periodo_b')

    if isinstance(periodo_a, tuple) and isinstance(periodo_b, tuple):

        df_a_scroll = df_scroll[
            (df_scroll["timestamp"].dt.date >= periodo_a[0]) & (df_scroll["timestamp"].dt.date <= periodo_a[1])
        ].copy()
        df_b_scroll = df_scroll[
            (df_scroll["timestamp"].dt.date >= periodo_b[0]) & (df_scroll["timestamp"].dt.date <= periodo_b[1])
        ].copy()

        df_a_attention = df_attention[
            (df_attention["timestamp"].dt.date >= periodo_a[0]) & (df_attention["timestamp"].dt.date <= periodo_a[1])
        ].copy()
        df_b_attention = df_attention[
            (df_attention["timestamp"].dt.date >= periodo_b[0]) & (df_attention["timestamp"].dt.date <= periodo_b[1])
        ].copy()

        df_a_scroll["Período"] = "Período A"
        df_b_scroll["Período"] = "Período B"
        df_a_attention["Período"] = "Período A"
        df_b_attention["Período"] = "Período B"

        df_combined_scroll = pd.concat([df_a_scroll, df_b_scroll])
        df_combined_attention = pd.concat([df_a_attention, df_b_attention])
    else:
        st.error("Selecione ambos os períodos corretamente.")
        st.stop()

# ==============================
# Gráficos básicos - Scroll
# ==============================

st.subheader("Visitantes por profundidade de scroll")
if not df_combined_scroll.empty:
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
else:
    st.info("Não há dados de scroll para exibir.")

# ==========================================
# Gráfico acumulado correto: base 5% - Scroll
# ==========================================

st.subheader("Percentual de visitantes que chegaram até pelo menos X% de scroll")
if not df_combined_scroll.empty:
    # Agrupar visitantes por faixa de scroll e período
    df_scroll_grouped = (
        df_combined_scroll
        .groupby(["Scroll depth", "Período"], as_index=False)["No of visitors"]
        .sum()
    )

    df_pct = []
    for label, df in df_scroll_grouped.groupby("Período"):
        df_sorted = df.sort_values("Scroll depth")
        # Adicionar verificação para evitar IndexError se a faixa mínima não existir
        if not df_sorted[df_sorted["Scroll depth"] == df_sorted["Scroll depth"].min()]["No of visitors"].empty:
            total_5 = df_sorted[df_sorted["Scroll depth"] == df_sorted["Scroll depth"].min()]["No of visitors"].values[0]
            if total_5 > 0:
                df_sorted["% visitantes"] = (df_sorted["No of visitors"] / total_5) * 100
                df_sorted["Período"] = label
                df_pct.append(df_sorted)

    if df_pct:
        df_scroll_pct = pd.concat(df_pct)

        fig_pct = px.line(
            df_scroll_pct,
            x="Scroll depth",
            y="% visitantes",
            color="Período",
            title="% de visitantes que chegaram até cada faixa de scroll",
            labels={"Scroll depth": "Scroll (%)", "% visitantes": "Visitantes (%)"},
            markers=True
        )
        fig_pct.update_traces(mode="lines+markers")
        fig_pct.update_layout(yaxis_ticksuffix="%")
        st.plotly_chart(fig_pct, use_container_width=True)
    else:
        st.info("Não há dados de scroll suficientes para o gráfico acumulado.")
else:
    st.info("Não há dados de scroll para exibir o gráfico acumulado.")


# Taxa de abandono - Scroll
st.subheader("Taxa de Abandono por profundidade")
if not df_combined_scroll.empty:
    fig_drop = px.line(
        df_combined_scroll.sort_values("Scroll depth"),
        x="Scroll depth",
        y="% drop off",
        color="Período",
        markers=True,
        title="% de abandono por faixa de scroll"
    )
    st.plotly_chart(fig_drop, use_container_width=True)
else:
    st.info("Não há dados de abandono de scroll para exibir.")

# ===================================
# Teste de Proporções faixa a faixa (5 em 5) - Scroll
# ===================================
st.subheader("Análise de Proporções por Faixas de Scroll (5 em 5%)")

resultados_scroll = []
if not df_combined_scroll.empty:
    faixas_scroll = sorted(df_combined_scroll["Scroll depth"].unique())
    # Considere as faixas em ordem crescente e de 5 em 5%
    for depth in faixas_scroll:
        faixa = df_combined_scroll[df_combined_scroll["Scroll depth"] == depth]
        # total de visitantes = visitantes na menor faixa (topo do funil)
        total_a = df_combined_scroll[(df_combined_scroll["Período"] == "Período A") & 
                                    (df_combined_scroll["Scroll depth"] == faixas_scroll[0])]["No of visitors"].sum()
        total_b = df_combined_scroll[(df_combined_scroll["Período"] == "Período B") & 
                                    (df_combined_scroll["Scroll depth"] == faixas_scroll[0])]["No of visitors"].sum()
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
                resultados_scroll.append({
                    "Faixa": f"{depth}%",
                    "Período A (%)": f"{prop_a:.2%}",
                    "Período B (%)": f"{prop_b:.2%}",
                    "Valor-p": round(pval, 4),
                    "Resultado": status
                })

if resultados_scroll:
    # Mostrar resultados em tabela
    df_resultados_scroll = pd.DataFrame(resultados_scroll)
    st.dataframe(df_resultados_scroll, use_container_width=True)

    # Mostrar resumo
    melhorou_scroll = df_resultados_scroll[df_resultados_scroll["Resultado"] == "✅ Melhorou"]
    piorou_scroll = df_resultados_scroll[df_resultados_scroll["Resultado"] == "❌ Piorou"]

    st.markdown("### 📊 Resumo da Análise de Scroll")
    st.markdown(f"- Faixas que **melhoraram**: {", ".join(melhorou_scroll["Faixa"]) if not melhorou_scroll.empty else "Nenhuma"}")
    st.markdown(f"- Faixas que **pioraram**: {", ".join(piorou_scroll["Faixa"]) if not piorou_scroll.empty else "Nenhuma"}")
else:
    st.info("Não há dados de scroll suficientes para realizar a análise de proporções.")

# Teste interativo faixa customizada (opcional) - Scroll
st.subheader("Teste de Proporções por Faixa de Scroll (customizável)")
if not df_combined_scroll.empty and faixas_scroll:
    scroll_value_scroll = st.slider(
        "Selecione a profundidade de scroll (%) para o teste",
        min_value=int(min(faixas_scroll)), max_value=int(max(faixas_scroll)), value=int(faixas_scroll[0]), step=5, key='scroll_value_scroll'
    )

    # total no topo do funil
    total_a_scroll = df_combined_scroll[(df_combined_scroll["Período"] == "Período A") & 
                                (df_combined_scroll["Scroll depth"] == faixas_scroll[0])]["No of visitors"].sum()
    total_b_scroll = df_combined_scroll[(df_combined_scroll["Período"] == "Período B") & 
                                (df_combined_scroll["Scroll depth"] == faixas_scroll[0])]["No of visitors"].sum()
    # visitantes na faixa
    faixa_a_scroll = df_combined_scroll[(df_combined_scroll["Período"] == "Período A") & 
                                (df_combined_scroll["Scroll depth"] == scroll_value_scroll)]["No of visitors"].sum()
    faixa_b_scroll = df_combined_scroll[(df_combined_scroll["Período"] == "Período B") & 
                                (df_combined_scroll["Scroll depth"] == scroll_value_scroll)]["No of visitors"].sum()

    prop_a_scroll = faixa_a_scroll / total_a_scroll if total_a_scroll > 0 else 0
    prop_b_scroll = faixa_b_scroll / total_b_scroll if total_b_scroll > 0 else 0

    st.markdown(f"""
    ### Visitantes que chegaram até {scroll_value_scroll}% de scroll:

    - **Período A:** {faixa_a_scroll} de {total_a_scroll} visitantes → **{prop_a_scroll:.2%}**
    - **Período B:** {faixa_b_scroll} de {total_b_scroll} visitantes → **{prop_b_scroll:.2%}**
    """)

    count_scroll = [faixa_a_scroll, faixa_b_scroll]
    nobs_scroll = [total_a_scroll, total_b_scroll]

    if all(n > 0 for n in nobs_scroll):
        stat_scroll, pval_scroll = proportions_ztest(count_scroll, nobs_scroll)
        st.markdown(f"""
        - Estatística z: {stat_scroll:.4f}
        - Valor-p: {pval_scroll:.4f}
        """)
        if pval_scroll < 0.05:
            if prop_b_scroll > prop_a_scroll:
                st.success("✅ O teste foi um sucesso: houve **melhora significativa** no engajamento nessa faixa de scroll.")
            else:
                st.error("❌ O teste **piorou significativamente** o engajamento nessa faixa de scroll.")
        else:
            st.info("ℹ️ O teste não apresentou mudança estatisticamente significativa. Resultado inconclusivo.")
    else:
        st.warning("Não há dados suficientes para realizar o teste nesta faixa.")
else:
    st.info("Não há dados de scroll para realizar o teste customizável.")


# ==============================
# Gráficos básicos - Atenção
# ==============================

st.subheader("Tempo médio gasto por profundidade de scroll (Atenção)")
if not df_combined_attention.empty:
    fig_attention_time = px.bar(
        df_combined_attention.sort_values("Scroll depth"),
        x="Scroll depth",
        y="Avg time spent",
        color="Período",
        barmode="group",
        title="Tempo médio gasto por faixa de scroll",
        labels={"Scroll depth": "Scroll (%)", "Avg time spent": "Tempo Médio Gasto (segundos)"}
    )
    st.plotly_chart(fig_attention_time, use_container_width=True)
else:
    st.info("Não há dados de atenção para exibir o gráfico de tempo médio gasto.")

st.subheader("Percentual do tempo de sessão por profundidade de scroll (Atenção)")
if not df_combined_attention.empty:
    fig_attention_session = px.bar(
        df_combined_attention.sort_values("Scroll depth"),
        x="Scroll depth",
        y="% of session length",
        color="Período",
        barmode="group",
        title="Percentual do tempo de sessão por faixa de scroll",
        labels={"Scroll depth": "Scroll (%)", "% of session length": "Percentual do Tempo de Sessão (%)"}
    )
    st.plotly_chart(fig_attention_session, use_container_width=True)
else:
    st.info("Não há dados de atenção para exibir o gráfico de percentual do tempo de sessão.")

# ===================================
# Teste de Proporções faixa a faixa (5 em 5) - Atenção
# ===================================
st.subheader("Análise de Proporções por Faixas de Atenção (5 em 5%)")

resultados_attention = []
if not df_combined_attention.empty:
    faixas_attention = sorted(df_combined_attention["Scroll depth"].unique())

    for depth in faixas_attention:
        faixa = df_combined_attention[df_combined_attention["Scroll depth"] == depth]
        
        # total de sessões na faixa 0% (ou a menor faixa de scroll)
        # Usar .get(0, 0) para evitar IndexError se a faixa 0% não existir
        total_sessions_a = df_combined_attention[(df_combined_attention["Período"] == "Período A") & 
                                                (df_combined_attention["Scroll depth"] == faixas_attention[0])]["Avg time spent"].count()
        total_sessions_b = df_combined_attention[(df_combined_attention["Período"] == "Período B") & 
                                                (df_combined_attention["Scroll depth"] == faixas_attention[0])]["Avg time spent"].count()

        # Número de sessões que atingiram a faixa atual com Avg time spent > 0
        sessions_at_depth_a = faixa[faixa["Período"] == "Período A"]["Avg time spent"].count()
        sessions_at_depth_b = faixa[faixa["Período"] == "Período B"]["Avg time spent"].count()

        if total_sessions_a > 0 and total_sessions_b > 0:
            prop_a = sessions_at_depth_a / total_sessions_a
            prop_b = sessions_at_depth_b / total_sessions_b

            count = [sessions_at_depth_a, sessions_at_depth_b]
            nobs = [total_sessions_a, total_sessions_b]

            if all(n > 0 for n in nobs):
                stat, pval = proportions_ztest(count, nobs)
                if pval < 0.05:
                    if prop_b > prop_a:
                        status = "✅ Melhorou"
                    else:
                        status = "❌ Piorou"
                else:
                    status = "⚖️ Inconclusivo"
                resultados_attention.append({
                    "Faixa": f"{depth}%",
                    "Período A (%)": f"{prop_a:.2%}",
                    "Período B (%)": f"{prop_b:.2%}",
                    "Valor-p": round(pval, 4),
                    "Resultado": status
                })

if resultados_attention:
    # Mostrar resultados em tabela
    df_resultados_attention = pd.DataFrame(resultados_attention)
    st.dataframe(df_resultados_attention, use_container_width=True)

    # Mostrar resumo
    melhorou_attention = df_resultados_attention[df_resultados_attention["Resultado"] == "✅ Melhorou"]
    piorou_attention = df_resultados_attention[df_resultados_attention["Resultado"] == "❌ Piorou"]

    st.markdown("### 📊 Resumo da Análise de Atenção")
    st.markdown(f"- Faixas que **melhoraram**: {", ".join(melhorou_attention["Faixa"]) if not melhorou_attention.empty else "Nenhuma"}")
    st.markdown(f"- Faixas que **pioraram**: {", ".join(piorou_attention["Faixa"]) if not piorou_attention.empty else "Nenhuma"}")
else:
    st.info("Não há dados de atenção suficientes para realizar a análise de proporções.")

# Teste interativo faixa customizada (opcional) - Atenção
st.subheader("Teste de Proporções por Faixa de Atenção (customizável)")

if not df_combined_attention.empty and faixas_attention:
    attention_value_scroll = st.slider(
        "Selecione a profundidade de scroll (%) para o teste de atenção",
        min_value=int(min(faixas_attention)), max_value=int(max(faixas_attention)), value=int(faixas_attention[0]), step=5, key='attention_value_scroll'
    )

    # total de sessões na faixa 0% (ou a menor faixa de scroll)
    total_sessions_a_custom = df_combined_attention[(df_combined_attention["Período"] == "Período A") & 
                                                (df_combined_attention["Scroll depth"] == faixas_attention[0])]["Avg time spent"].count()
    total_sessions_b_custom = df_combined_attention[(df_combined_attention["Período"] == "Período B") & 
                                                (df_combined_attention["Scroll depth"] == faixas_attention[0])]["Avg time spent"].count()

    # Número de sessões que atingiram a faixa atual com Avg time spent > 0
    sessions_at_depth_a_custom = df_combined_attention[(df_combined_attention["Período"] == "Período A") & 
                                                    (df_combined_attention["Scroll depth"] == attention_value_scroll)]["Avg time spent"].count()
    sessions_at_depth_b_custom = df_combined_attention[(df_combined_attention["Período"] == "Período B") & 
                                                    (df_combined_attention["Scroll depth"] == attention_value_scroll)]["Avg time spent"].count()

    prop_a_attention_custom = sessions_at_depth_a_custom / total_sessions_a_custom if total_sessions_a_custom > 0 else 0
    prop_b_attention_custom = sessions_at_depth_b_custom / total_sessions_b_custom if total_sessions_b_custom > 0 else 0

    st.markdown(f"""
    ### Sessões que atingiram {attention_value_scroll}% de scroll (com tempo de atenção > 0):

    - **Período A:** {sessions_at_depth_a_custom} de {total_sessions_a_custom} sessões → **{prop_a_attention_custom:.2%}**
    - **Período B:** {sessions_at_depth_b_custom} de {total_sessions_b_custom} sessões → **{prop_b_attention_custom:.2%}**
    """)

    count_attention_custom = [sessions_at_depth_a_custom, sessions_at_depth_b_custom]
    nobs_attention_custom = [total_sessions_a_custom, total_sessions_b_custom]

    if all(n > 0 for n in nobs_attention_custom):
        stat_attention_custom, pval_attention_custom = proportions_ztest(count_attention_custom, nobs_attention_custom)
        st.markdown(f"""
        - Estatística z: {stat_attention_custom:.4f}
        - Valor-p: {pval_attention_custom:.4f}
        """)
        if pval_attention_custom < 0.05:
            if prop_b_attention_custom > prop_a_attention_custom:
                st.success("✅ O teste foi um sucesso: houve **melhora significativa** na atenção nessa faixa de scroll.")
            else:
                st.error("❌ O teste **piorou significativamente** a atenção nessa faixa de scroll.")
        else:
            st.info("ℹ️ O teste não apresentou mudança estatisticamente significativa. Resultado inconclusivo.")
    else:
        st.warning("Não há dados suficientes para realizar o teste nesta faixa de atenção.")
else:
    st.info("Não há dados de atenção para realizar o teste customizável.")