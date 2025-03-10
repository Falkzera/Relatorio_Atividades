import streamlit as st
import importlib
import Scripts.utils as utils

utils.display_sidebar()
utils.display_header("Relatório Consolidado 📊")
utils.setup_page("consolidado")

# Criando lista dinâmica de abas com base nas permissões do usuário
tabs = []
tab_modules = {}

if "relatorio" in st.session_state.tab_access:
    tabs.append("Relatório de Atividades 📝")
    tab_modules["Relatório de Atividades 📝"] = "Modulos.RELATORIO"

if "consolidado" in st.session_state.tab_access:
    tabs.append("Relatório Consolidado")
    tab_modules["Relatório Consolidado"] = "Modulos.CONSOLIDADO"

if "dashboards" in st.session_state.tab_access:
    tabs.append("Dashboards 📊")
    tab_modules["Dashboards 📊"] = "Modulos.DASHBOARDS"

# Inicializa o estado da aba selecionada se não existir
if 'selected_tab' not in st.session_state:
    st.session_state.selected_tab = tabs[0] if tabs else None

# Criando as abas dinâmicas apenas com as permitidas
if tabs:
    try:
        # Usando st.selectbox para seleção de abas (pode ser substituído por st.tabs se preferir)
        selected_tab = st.sidebar.selectbox("Selecione a aba:", tabs, index=tabs.index(st.session_state.selected_tab))
    except ValueError:
        # Redireciona o usuário para a primeira aba que ele tem acesso
        st.session_state.selected_tab = tabs[0]
        selected_tab = st.session_state.selected_tab

    # Atualiza o estado da aba selecionada
    # st.session_state.selected_tab = selected_tab

    # Carrega o conteúdo da aba selecionada
    if selected_tab in tab_modules:
        module_path = tab_modules[selected_tab]
        module = importlib.import_module(module_path)
        getattr(module, module_path.split(".")[-1])()  # Executa a função principal do módulo
else:
    st.error("🚫 Você não tem acesso a nenhum relatório.")

utils.outro_usuario()
utils.display_links()