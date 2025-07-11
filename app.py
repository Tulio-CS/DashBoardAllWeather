import streamlit as st
from auth import login

st.set_page_config(
    page_title="Resumo Técnico · All Weather",
    layout="wide",
)

if not login():
    st.stop()

st.title("All Weather · Visão Geral do Projeto")

st.markdown("---")

st.subheader("Funcionalidades do Dashboard")

st.markdown("""
- **Shopify**: 
    - Análise de vendas por SKU, cor, tamanho e compressão.
    - Métricas de receita total, ticket médio e número de pedidos.
- **Google Analytics**:
    - Visualização de ROAS, CTR, CPC e CPM.
    - Gráficos diários com dados consolidados de campanhas.
- **Instagram**:
    - Métricas de alcance, curtidas, salvamentos, compartilhamentos e comentários.
    - Performance por tipo de post, horário e dia da semana.
    - Tabela com links diretos para os top posts.
- **Chat AW**:
    - Assistente virtual com IA para perguntas sobre dados ou suporte analítico automatizado.
""")

st.markdown("---")

st.subheader("APIs Utilizadas")

st.markdown("### 1. [Google Analytics API](https://console.cloud.google.com/apis/api/drive.googleapis.com/metrics?project=n8naw-462822&inv=1&invt=Ab06vA)")
st.markdown("""
- Coleta dados como sessões, impressões, receita e conversões.
- **Autenticação**: OAuth 2.0 com chave de serviço (não expira).
- **Custo**: Pago conforme uso no [Google Cloud Platform](https://cloud.google.com/pricing).
""")

st.markdown("### 2. [Google Drive API](https://developers.google.com/drive)")
st.markdown("""
- Armazenamento de planilhas e relatórios.
- **Autenticação**: OAuth 2.0 com chave de serviço (sem expiração).
- **Custo**: Gratuito até o limite de 15 GB.
""")

st.markdown("### 3. [Meta Graph API (Instagram)](https://developers.facebook.com/docs/instagram-api/guides/insights/)")
st.markdown("""
- Extrai métricas de alcance, curtidas, comentários e outros insights.
- **Autenticação**: Access Token de App vinculado a conta comercial.
- **Validade**: 60 dias (tokens long-lived).
- **Custo**: Gratuito.
""")

st.markdown("### 4. [OpenAI API](https://platform.openai.com/docs)")
st.markdown("""
- Usada para transcrição de áudio (Whisper) e respostas inteligentes com agentes GPT.
- **Autenticação**: API Key.
- **Expiração**: Tokens persistentes (uso controlado por limite).
- **Custo**: Pago por requisição ([ver preços](https://openai.com/pricing)).
""")

st.markdown("### 5. [Supabase](https://supabase.com/docs)")
st.markdown("""
- Backend com banco PostgreSQL usado para centralizar os dados do projeto.
- **Autenticação**: API Key.
- **Expiração**: Sem expiração.
- **Custo**: Gratuito (limites: 500 MB e 500 mil requisições/mês).
""")

st.markdown("---")

st.subheader("🧰 Serviços Auxiliares (Não são APIs)")

st.markdown("### [n8n (Automação)](https://docs.n8n.io/)")
st.markdown("""
- Utilizado para ETLs e atualização programada de dados.
- **Custo**: Gratuito se auto-hospedado. Há custos de hospedagem em servidor (Digital Ocean).
""")

st.markdown("### [Railway (Hospedagem)](https://docs.railway.app/)")
st.markdown("""
- Utilizado para hospedar o dashboard
- **Custo**: Plano gratuito com limite de horas; planos pagos sob demanda.
""")

st.markdown("---")

st.caption("Projeto desenvolvido por Túlio · All Weather © 2025")
