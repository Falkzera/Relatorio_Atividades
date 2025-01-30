import streamlit as st
from Models.marca import display_sidebar, display_header 

st.set_page_config(layout='wide', page_title='Relatório de Atividades', page_icon='📊')

display_sidebar()
display_header("Base de Dados - PETECO 📊")

def login(username, password):
    stored_username = st.secrets["auth"]["USERNAME"]
    stored_password = st.secrets["auth"]["PASSWORD"]
    
    return username == stored_username and password == stored_password

if "logged_in" not in st.session_state:
  st.session_state.logged_in = False

if not st.session_state.logged_in:
  st.title("Login")

  input_username = st.text_input("Usuário")
  input_password = st.text_input("Senha", type="password")

  if st.button("Entrar"):
    if login(input_username, input_password):
      st.session_state.logged_in = True
    else:
      st.error("Usuário ou senha incorretos.")
else:
    st.success("Login efetuado com sucesso!")


 