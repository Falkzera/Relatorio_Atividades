import streamlit as st

st.set_page_config(layout='wide', page_title='Relatório de Atividades', page_icon='📊')

st.markdown("""
    <style>
    [data-testid="stSidebarNav"] {display: none;}
    </style>
""", unsafe_allow_html=True)

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.switch_page("pages/login.py")

col1, col2 = st.columns([3, 1])
col1.write("Você está na página inicial do sistema.")

st.sidebar.title("📌 Menu de Navegação")

menu_items = ["🏠 HOME"]
if "page_access" in st.session_state:
    if "consolidado" in st.session_state.page_access:
        menu_items.append("📊 Consolidado")

if "selected_page" not in st.session_state or st.session_state.selected_page not in menu_items:
    st.session_state.selected_page = "🏠 HOME"

selected_page = st.sidebar.selectbox("📌 Escolha uma página:", menu_items, index=menu_items.index(st.session_state.selected_page))

if st.button("**Logar com outro usuário** 🔑"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.page_access = []
    st.session_state.tab_access = []
    st.switch_page("pages/login.py")  # Redireciona para a tela de login