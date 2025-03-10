import streamlit as st
import Scripts.utils as utils

st.set_page_config(page_title="Sistema de Login", page_icon="🔐", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "page_access" not in st.session_state:
    st.session_state.page_access = []
if "tab_access" not in st.session_state:
    st.session_state.tab_access = []
if "selected_page" not in st.session_state:
    st.session_state.selected_page = "🏠 Home"

utils.display_sidebar()

st.markdown("""
    <style>
    [data-testid="stSidebarNav"] {display: none;}
    </style>
""", unsafe_allow_html=True)

def login(username, password):
    users = st.secrets["users"]
    page_access = st.secrets["page_access"]
    tab_access = st.secrets["tab_access"]

    if username in users and users[username] == password:
        return page_access.get(username, []), tab_access.get(username, [])
    return None, None

st.markdown("<h1 style='text-align: center;'>🔐 Sistema de Login 🔐</h1>", unsafe_allow_html=True)

username = st.text_input("Usuário")
password = st.text_input("Senha", type="password")

if st.button("Entrar", help="Clique para fazer login", icon="🚪", use_container_width=True, type='primary'):
    page_access, tab_access = login(username, password)

    if page_access:
        # Armazena permissões na sessão do usuário
        st.session_state.logged_in = True
        st.session_state.username = username
        st.session_state.page_access = page_access
        st.session_state.tab_access = tab_access

        # **Etapa 1: Verificar se o usuário tem acesso a todas as páginas**
        if {"consolidado", "qualquercoisa"}.issubset(set(page_access)):
            st.session_state.selected_page = "🏠 Home"
            st.switch_page("HOME.py")

        # **Se o usuário tem acesso APENAS a uma página, redirecioná-lo diretamente**
        elif len(page_access) == 1:
            only_page = page_access[0]
            if only_page == "consolidado":
                st.switch_page("pages/consolidado.py")


        # **Se não cair em nenhum dos casos anteriores, joga para Home**
        else:
            st.switch_page("HOME.py")

    else:
        st.error("Usuário ou senha incorretos.")

utils.display_links()

