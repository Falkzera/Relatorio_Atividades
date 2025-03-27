import streamlit as st
import os
import sys
import re
from streamlit_tags import st_tags

def BUSCADOR():
    # === Configuração de caminhos ===
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.append(BASE_DIR)
    sys.path.append(os.path.join(BASE_DIR, "buscador"))
    sys.path.append(os.path.join(BASE_DIR, "Scripts"))

    # === Imports ===
    from buscador.indexador import indexar_atas_do_drive, carregar_chroma_memoria_do_cache
    from Scripts.utils import (
        filtrar_resultados_semanticos,
        exibir_resultados_formatados
    )

    # === Sidebar: Atualização da base de dados
    with st.sidebar:
        st.sidebar.write("---")
        if st.button("🔄 Atualizar base de dados do Google Drive", use_container_width=True, type="primary", help='Clique para atualizar novas ATAS.'):
            with st.spinner("🔁 Buscando e indexando atas do Drive..."):
                indexar_atas_do_drive()
            st.success("✅ Base de dados atualizada com sucesso!")

    # === Instruções
    with st.expander("ℹ️ Instruções"):
        st.markdown("Preencha os campos abaixo para realizar a busca nas atas.")
        st.markdown("- **Palavra-chave**: busca literal de termos no texto.")
        st.markdown("- **Busca semântica**: busca inteligente com base no contexto.")
        st.markdown("- **Modo de busca**: escolha se quer buscar por contexto ou por exatidão.")
        st.markdown("- **Filtros**: refine por intervalo de anos.")
    
    st.write('---')

    # === Inputs de busca
    st.subheader('🔍 Busca nas Atas')
    
    palavras_chave = st_tags(
        label="🔡 Palavras-chave (ex: nivelamento)",
        text="Pressione Enter para adicionar uma palavra-chave",
        value=[],  # valor padrão vazio
        key="palavras_chave"
    )
    busca_semantica = st.text_input("🧠 Busca semântica (ex: qual o dia?)").strip().lower()

    palavras_chave = [p for p in palavras_chave if p]

    # === Filtros
    with st.expander("🧰 Filtros"):
        db_filtro = carregar_chroma_memoria_do_cache()
        total_atas = len(db_filtro._collection.get()["documents"]) if db_filtro else 0
        st.write(f"📄 Total de atas disponíveis: **{total_atas}**")

        anos_disponiveis = []
        if db_filtro:
            for meta in db_filtro._collection.get()["metadatas"]:
                match = re.search(r'(\d{4})', meta.get("source", ""))
                if match:
                    anos_disponiveis.append(int(match.group(1)))

        if anos_disponiveis:
            ano_min = min(anos_disponiveis)
            ano_max = max(anos_disponiveis)
        else:
            ano_min, ano_max = 2000, 2030

        ano_range = st.slider("📅 Intervalo de anos", ano_min, ano_max, (ano_min, ano_max), step=1)
        st.session_state["filtro_ano_inicio"] = ano_range[0]
        st.session_state["filtro_ano_fim"] = ano_range[1]

    # === Escolha do modo de busca
    # modo_busca = st.radio(
    #     "🔎 Escolha o modo de busca:",
    #     ["🔍 Por contexto (semântica)", "✅ Exata (palavra igual)"],
    #     horizontal=True
    # )

    modo_busca = "✅ Exata (palavra igual)" if st.toggle("🔎 Modo de busca exata (palavra igual)", value=False) else "🔍 Por contexto (semântica)"

    # === Estados iniciais
    if "limite_resultados" not in st.session_state:
        st.session_state.limite_resultados = 5
    if "docs_filtrados" not in st.session_state:
        st.session_state.docs_filtrados = []
    if "total_ocorrencias" not in st.session_state:
        st.session_state.total_ocorrencias = 0

    # === Botão de buscar
    if st.button("🔎 Buscar", use_container_width=True, type="primary"):
        if not palavras_chave and not busca_semantica:
            st.warning("⚠️ Preencha ao menos um dos campos para realizar a busca.")
        else:
            with st.spinner("📚 Carregando base..."):
                db = carregar_chroma_memoria_do_cache()
                if db is None:
                    st.stop()

            with st.spinner("🔍 Buscando..."):
                try:
                    if modo_busca == "✅ Exata (palavra igual)":
                        # Busca literal direta
                        colecao = db._collection.get()
                        documentos = colecao["documents"]
                        metadatas = colecao["metadatas"]

                        class DummyDoc:
                            def __init__(self, texto, metadata):
                                self.page_content = texto
                                self.metadata = metadata

                        docs_brutos = [DummyDoc(texto, meta) for texto, meta in zip(documentos, metadatas)]
                        docs_filtrados, total_ocorrencias = filtrar_resultados_semanticos(docs_brutos, palavras_chave)

                    else:
                        # Busca semântica via embeddings
                        consulta = busca_semantica if busca_semantica else " ".join(palavras_chave)
                        resultados = db.similarity_search(consulta, k=5000)
                        docs_filtrados, total_ocorrencias = filtrar_resultados_semanticos(resultados, palavras_chave)

                    st.session_state.docs_filtrados = docs_filtrados
                    st.session_state.total_ocorrencias = total_ocorrencias
                    st.session_state.limite_resultados = 5

                except Exception as e:
                    st.error(f"❌ Erro na busca: {e}")
                    st.session_state.docs_filtrados = []
                    st.session_state.total_ocorrencias = 0

    # === Exibição de resultados
    docs_filtrados = st.session_state.docs_filtrados
    total_ocorrencias = st.session_state.total_ocorrencias
    limite = st.session_state.limite_resultados

    if docs_filtrados:
        st.success(f"✅ {len(docs_filtrados)} resultado(s) encontrado(s).")

        if palavras_chave:
            chaves_formatadas = ', '.join([f'**{pc}**' for pc in palavras_chave])
            st.info(f"🔡 As palavras {chaves_formatadas} apareceram **{total_ocorrencias}x** nos resultados.")

        exibir_resultados_formatados(docs_filtrados[:limite], palavra_chave=palavras_chave)

        if limite < len(docs_filtrados):
            if st.button("📄 Mostrar mais resultados", use_container_width=True, type="primary"):
                st.session_state.limite_resultados += 20
                st.rerun()
    else:
        st.warning("⚠️ Nenhum resultado encontrado com os critérios informados.")
