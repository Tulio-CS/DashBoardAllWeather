import streamlit as st
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def _logout():
    supabase.auth.sign_out()
    st.session_state.pop("user", None)

def login() -> bool:
    """Display login form and authenticate using Supabase."""
    if st.session_state.get("user"):
        st.sidebar.button("Logout", on_click=_logout)
        return True

    with st.form("login"):
        email = st.text_input("Email")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")

    if submitted:
        try:
            user = supabase.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state["user"] = user
            st.sidebar.success("Bem-vindo!")
            st.sidebar.button("Logout", on_click=_logout)
            return True
        except Exception:
            st.error("Usuário ou senha incorretos")
            return False

    st.warning("Por favor, insira suas credenciais")
    return False
