import streamlit as st
from shopify import shopify_page
from analytics import analytics_page
from instagram import instagram_page
from chat_allweather import chat_page

st.set_page_config(page_title="Dashboard All Weather", layout="wide", page_icon="AW")

# Definir a página inicial se não existir no estado
if "current_page" not in st.session_state:
    st.session_state.current_page = "Chat AW"

# Sidebar para navegação
with st.sidebar:
    st.title("AllWeather Dashboard")

    pagina = st.radio(
        "Selecione a Página", 
        ["Chat AW", "Shopify", "Google Analytics", "Posts Instagram"],
        index=["Chat AW", "Shopify", "Google Analytics", "Posts Instagram"].index(st.session_state.current_page)
    )

    st.session_state.current_page = pagina

# Roteamento das páginas
if st.session_state.current_page == "Shopify":
    shopify_page()

elif st.session_state.current_page == "Google Analytics":
    analytics_page()

elif st.session_state.current_page == "Posts Instagram":
    instagram_page()

elif st.session_state.current_page == "Chat AW":
    chat_page()
