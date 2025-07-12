import streamlit as st
import pandas as pd
from supabase import create_client
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.vectorstores import FAISS
from langchain.docstore.document import Document
from langchain.chains import RetrievalQA
from dotenv import load_dotenv
from auth import login
import os

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)



supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def chat_page():
    if not login():
        st.stop()
    st.title("Chat AllWeather")

    # =============================
    # Configurações
    # ============================

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # =============================
    # Funções auxiliares
    # =============================

    def dataframe_para_documentos_instagram(df):
        documentos = []
        for _, row in df.iterrows():
            texto = (
                f"Post no dia {row.get('timestamp')}, "
                f"tipo {row.get('media_type')}, "
                f"legenda: {row.get('caption', 'sem legenda')}, "
                f"alcance {row.get('reach', 0)}, "
                f"curtidas {row.get('likes', 0)}, "
                f"comentários {row.get('comments', 0)}"
            )
            if 'saved' in df.columns:
                texto += f", salvamentos {row.get('saved', 0)}"
            if 'shares' in df.columns:
                texto += f", compartilhamentos {row.get('shares', 0)}"
            texto += f", link: {row.get('permalink')}."

            documentos.append(Document(page_content=texto, metadata={"source": "instagram"}))
        return documentos


    def dataframe_para_documentos_shopify(df):
        documentos = []
        for _, row in df.iterrows():
            texto = (
                f"Venda na data {row.get('date')}, "
                f"SKU {row.get('sku', 'indefinido')}, "
                f"cor {row.get('cor', 'indefinida')}, "
                f"tamanho {row.get('tamanho', 'indefinido')}, "
                f"comprimento {row.get('comprimento', 'indefinido')}, "
                f"compressao {row.get('compressao', 'indefinida')}, "
                f"preço {row.get('price', 0)} reais, "
                f"pedido número {row.get('order_number', 'N/A')}."
            )
            documentos.append(Document(page_content=texto, metadata={"source": "shopify"}))
        return documentos
    
    # =============================
    # Carregar dados do Supabase
    # =============================

    @st.cache_data
    def carregar_dados():
        shopify_data = supabase.table("Shopify").select("*").execute().data
        instagram_data = supabase.table("Posts").select("*").execute().data

        df_shopify = pd.DataFrame(shopify_data)
        df_instagram = pd.DataFrame(instagram_data)

        df_shopify["date"] = pd.to_datetime(df_shopify["date"], errors="coerce")
        df_instagram["timestamp"] = pd.to_datetime(df_instagram["timestamp"], errors="coerce")
        df_instagram["dia_semana"] = df_instagram["timestamp"].dt.day_name()
        df_instagram["hora"] = df_instagram["timestamp"].dt.hour

        return df_shopify, df_instagram


    df_shopify, df_instagram = carregar_dados()

    # =============================
    # Gerar vector store
    # =============================

    docs_instagram = dataframe_para_documentos_instagram(df_instagram)
    docs_shopify = dataframe_para_documentos_shopify(df_shopify)

    documentos = docs_instagram + docs_shopify

    st.subheader("Documentos carregados")
    st.write(f"Total de documentos: {len(documentos)}")

    embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)

    vectorstore = FAISS.from_documents(documentos, embeddings)

    retriever = vectorstore.as_retriever()

    # =============================
    # LLM + QA Chain
    # =============================

    llm = ChatOpenAI(
        model_name="gpt-4",
        temperature=0.4,
        api_key=OPENAI_API_KEY
    )

    qa = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        chain_type="stuff"
    )

    # =============================
    # Interface do Chat
    # =============================

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    contexto = """
        Você é um analista de dados sênior da AllWeather, uma marca de roupas masculinas premium.

        Seu papel:
        - Gerar respostas extremamente detalhadas, com tom profissional, consultivo e de alto nível analítico.
        - Sempre incluir dados concretos como números, datas, tendências, análises comparativas e insights baseados nos dados disponíveis.
        - Suas respostas devem ser claras, bem estruturadas, como se fossem parte de um relatório executivo ou de Business Intelligence.
        - Quando responder perguntas sobre Instagram, leve em conta dados como: tipo de post (carrossel, reels, feed), alcance, curtidas, comentários, dia da semana, hora de postagem, salvamentos e compartilhamentos (se disponíveis).
        - Quando responder perguntas sobre vendas, leve em conta dados como: tamanho, compressão, comprimento, cor, SKU, ticket médio, quantidade vendida, data da venda e SKU mais vendidos.
        - Se uma informação não estiver presente nos dados, informe claramente que ela não está disponível. Nunca invente dados.
        - Utilize sempre um tom formal, profissional e de consultoria de dados.
        """
    pergunta = st.chat_input("Digite sua pergunta...")

    if pergunta:
        pergunta_com_contexto = contexto + "\n\n" + pergunta

        with st.chat_message("user"):
            st.markdown(pergunta)

        st.session_state.messages.append({"role": "user", "content": pergunta})

        with st.spinner("Consultando dados..."):
            resposta = qa.run(pergunta_com_contexto)

        with st.chat_message("assistant"):
            st.markdown(resposta)

        st.session_state.messages.append({"role": "assistant", "content": resposta})

    # =============================
    # Botão para resetar a conversa
    # =============================

    if st.button("Resetar Conversa"):
        st.session_state.messages = []
        st.rerun()