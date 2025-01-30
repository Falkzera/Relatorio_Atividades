import streamlit as st

PET_LOGO = "Image/PET.png"

def display_sidebar():
    """Exibe a imagem do PET e links úteis na sidebar."""
    with st.sidebar:
        st.image(PET_LOGO)
        st.write('---')

        links_html = """
                    <div style="text-align: center;">
                        <h2>📌 Links Úteis</h2>
                        <a href="https://drive.google.com/drive/folders/1UANTy5LhulVNMxce5IDKtypje80HiUis" target="_blank">
                            <img src="https://upload.wikimedia.org/wikipedia/commons/d/da/Google_Drive_logo.png" 
                                alt="Google Drive" style="width:50px;height:50px;margin:10px;">
                        </a>
                        <a href="https://trello.com/b/GFUQK4OP/1-reunioes" target="_blank">
                            <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/c/c1/Font_Awesome_5_brands_trello.svg/157px-Font_Awesome_5_brands_trello.svg.png" 
                                alt="Trello" style="width:50px;height:50px;margin:10px;">
                        </a>
                        <a href="https://sites.google.com/view/petecoufal/in%C3%ADcio" target="_blank">
                            <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/b/b0/Website-icon.png/201px-Website-icon.png" 
                                alt="Website" style="width:50px;height:50px;margin:10px;">
                        </a>
                    </div>
                    """
        st.markdown(links_html, unsafe_allow_html=True)

def display_header(title="Relatório de Atividades"):
    """Exibe o título da página com a imagem do PET ao lado."""
    with st.container():
        col1, col2 = st.columns([3, 1])
        col1.title(title)
        col2.image(PET_LOGO)


