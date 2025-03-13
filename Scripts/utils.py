import io
import smtplib
import pandas as pd
import streamlit as st
import Scripts.utils as utils
from Scripts.google_drive_utils import authenticate_service_account, download_file_by_name, read_parquet_files_from_drive, baixar_cache_do_drive, baixar_parquet_do_drive
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from Modulos.DASHBOARDS import DASHBOARDS
from Modulos.CONSOLIDADO import CONSOLIDADO

def setup_page(page_name):
    """
    Configura toda a estrutura da página:
    - Oculta a sidebar padrão do Streamlit
    - Verifica se o usuário tem permissão para acessar a página
    - Cria o menu de navegação lateral com base nas permissões
    - Redireciona para a página correta ao selecionar uma nova
    - Adiciona um botão de logout

    Parâmetros:
    - page_name (str): Nome da página atual para verificação de acesso
    """

    # Oculta sidebar automática
    st.markdown("""
        <style>
        [data-testid="stSidebarNav"] {display: none;}
        </style>
    """, unsafe_allow_html=True)

    # Verifica se o usuário tem permissão para acessar esta página
    if "page_access" not in st.session_state or page_name not in st.session_state.page_access:
        st.error("🚫 Você não tem permissão para acessar esta página.")
        utils.outro_usuario()
        st.stop()

    # Criando menu lateral de navegação com base nas permissões do usuário
    menu_items = []
    if "site" in st.session_state.page_access:
        menu_items.append("site")

    # Garantir que selected_page esteja na lista
    if "selected_page" not in st.session_state or st.session_state.selected_page not in menu_items:
        st.session_state.selected_page = menu_items[0] if menu_items else "🏠 HOME"

    # Criando menu lateral com selectbox para navegação

    # st.sidebar.title("📌 - Navegação") 
    # selected_page = st.sidebar.selectbox("Selecione entre as páginas disponíveis:", menu_items, index=menu_items.index(st.session_state.selected_page))

    # # Redirecionar para a página correta
    # if selected_page != st.session_state.selected_page:
    #     st.session_state.selected_page = selected_page
    #     if selected_page == "consolidado":
    #         st.switch_page("pages/consolidado.py")
    #     # elif selected_page == "📜 Relatórios":
    #     #     st.switch_page("pages/relatorios.py")
    #     # elif selected_page == "📊 Dashboards":
    #     #     st.switch_page("pages/dashboards.py")

def outro_usuario():
    st.sidebar.write('---')
    st.sidebar.title("👤 - Alterar o usuário") 
    if st.sidebar.button("**Alterar o usuário** 🔑", help="Clique aqui para logar com outro usuário", key="logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.page_access = []
        st.session_state.tab_access = []
        st.switch_page("pages/login.py")



@st.cache_data(ttl= 60 * 60 * 24)
def data_load():
    service = authenticate_service_account()
    folder_id = "1o0cuz9ltekMieUAPKV556-ncwqW9RIsx"
    file_name_alunos = "alunos.xlsx"
    file_name_atividade = "atividade.xlsx"
    file_name_email = "email.xlsx"
    file_data_alunos = download_file_by_name(service, folder_id, file_name_alunos)
    file_data_atividade = download_file_by_name(service, folder_id, file_name_atividade)
    file_data_email = download_file_by_name(service, folder_id, file_name_email)
    df_alunos = pd.read_excel(file_data_alunos) if file_data_alunos else None
    df_atividade = pd.read_excel(file_data_atividade) if file_data_atividade else None
    df_email = pd.read_excel(file_data_email) if file_data_email else None

    if df_alunos is not None:
        pass
    else:
        st.error(f"Erro ao carregar o arquivo '{file_name_alunos}'.")
    if df_atividade is not None:
        pass
    else:
        st.error(f"Erro ao carregar o arquivo '{file_name_atividade}'.")
    if df_email is not None:
        pass
    else:
        st.error(f"Erro ao carregar o arquivo '{file_name_email}'.")

    return df_atividade, df_alunos, df_email

def list_files_in_folder(service, folder_id):
    query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder'"
    response = service.files().list(q=query, fields="files(id, name)").execute()
    return response.get('files', [])

def list_parquet_files(service, folder_id):
    query = f"'{folder_id}' in parents and mimeType='application/octet-stream' and name contains '.parquet'"
    response = service.files().list(q=query, fields="files(id, name)").execute()
    return response.get('files', [])

def clean_periodo_execucao(row):
    periodo_execucao = row['Período de Execução']
    if 'Durante o mês' in periodo_execucao:
        dias = [dia for dia in periodo_execucao.split(', ') if dia != 'Durante o mês']
        if dias:
            st.warning(f"A atividade '{row['Nome da Atividade']}' teve 'Durante o mês' removido, pois outros dias foram especificados por outros membros.")
            return ', '.join(dias)   
    return periodo_execucao

def to_excel(df):
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Sheet1', index=False)
    writer.close()
    processed_data = output.getvalue()
    return processed_data

def enviar_email(df_atividade, mes_escolhido, ano_escolhido, df_email="df_email"):

    SMTP_SERVER = st.secrets["EMAIL"]["SMTP_SERVER"]
    SMTP_PORT = st.secrets["EMAIL"]["SMTP_PORT"]
    EMAIL_SENDER = st.secrets["EMAIL"]["EMAIL_SENDER"]
    EMAIL_PASSWORD = st.secrets["EMAIL"]["EMAIL_PASSWORD"]
    EMAIL_DESTINATARIO = ", ".join(df_email["EMAIL"].dropna().tolist())

    def to_excel(df):
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        df.to_excel(writer, sheet_name='Sheet1', index=False)
        writer.close()
        return output.getvalue()

    df_excel = to_excel(df_atividade)

    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_DESTINATARIO
    msg["Subject"] = f"Relatório Consolidado {mes_escolhido}/{ano_escolhido}"

    mensagem = f"""
        Este é um e-mail gerado automaticamente. Por favor, não responda a esta mensagem.

        Prezado(a),

        Segue em anexo o relatório consolidado referente a {mes_escolhido}/{ano_escolhido}. Caso haja qualquer inconsistência ou dúvida, entre em contato com a equipe responsável.

        Agradecemos sua atenção.

        Atenciosamente,  
        Programa de Educação Tutorial  
        PET - ECONOMIA
        """
    msg.attach(MIMEText(mensagem, "plain"))

    part = MIMEBase("application", "octet-stream")
    part.set_payload(df_excel)
    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        f"attachment; filename=relatorio_consolidado_{mes_escolhido}-{ano_escolhido}.xlsx"
    )
    msg.attach(part)

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_DESTINATARIO, msg.as_string())
        server.quit()
        st.success("✅ E-mail enviado com sucesso!")
        st.balloons()
    except Exception as e:
        st.error(f"❌ Erro ao enviar o e-mail, entre em contato com o Desenvolvedor. {e}")

def load_data(folder_id):
    service = authenticate_service_account() 
    df = read_parquet_files_from_drive(service, folder_id)
    return df, service

def atualizar_dados():
    # Adiciona o botão de atualização manual no sidebar
    with st.sidebar:
        if st.button('Atualizar Informações', help='Força a atualização imediata dos dados', icon="🔄", use_container_width=True, type="secondary"):
            # Limpa o cache específico desta função
            baixar_parquet_do_drive.clear()
            try:
                DASHBOARDS.load_data.clear()
                CONSOLIDADO.load_data.clear()
            except:
                st.sidebar.caption('Erro no log, contate o desenvolvedor. ( Não interfere no funcionamento do sistema )')

            st.rerun()
        
        # Mensagem de atualização automática
        if 'last_updated' not in st.session_state:
            st.session_state.last_updated = 'Nunca'
            
        st.caption(f"Última atualização: {st.session_state.last_updated}")
        tempo_agora = pd.Timestamp.now()
        tempo_agora = tempo_agora.strftime("%H:%M:%S")
        # st.caption(f"Horário atual: {tempo_agora}")

        # from datetime import datetime

        # ultima_atualizacao = st.session_state.last_updated
        # ultima_atualizacao_dt = datetime.strptime(ultima_atualizacao, "%Y-%m-%d %H:%M:%S")
        # tempo_agora_dt = datetime.now()

        # tempo_que_falta = tempo_agora_dt - ultima_atualizacao_dt

        # horas, remainder = divmod(tempo_que_falta.total_seconds(), 3600)
        # minutos, segundos = divmod(remainder, 60)

        # st.caption(f'Faltam {int(horas)} horas, {int(minutos)} minutos e {int(segundos)} segundos para a próxima atualização')







def display_sidebar():
    """Exibe a imagem do PET e links úteis na sidebar."""
    with st.sidebar:
        st.image('Image/PET.png')
        st.write('---')
def display_links():
    with st.sidebar:
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
        col2.image("Image/PET.png")

