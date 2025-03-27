import io
import smtplib
import re
import os
import pandas as pd # type: ignore
import streamlit as st # type: ignore
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
        st.write('###')
        st.markdown('<p style="text-align: center;">Desenvolvido por: <a href="https://github.com/falkzera" target="_blank">Lucas Falcão</a></p>', unsafe_allow_html=True)

def display_header(title="Relatório de Atividades"):
    """Exibe o título da página com a imagem do PET ao lado."""
    with st.container():
        col1, col2 = st.columns([3, 1])
        col1.title(title)
        col2.image("Image/PET.png")






def limpar_texto(texto: str) -> str:
    """Remove quebras e espaços extras do texto."""
    return ' '.join(texto.split())

def contar_ocorrencias(texto: str, termo: str) -> int:
    """Conta quantas vezes a palavra aparece no texto (ignora maiúsculas/minúsculas)."""
    return len(re.findall(re.escape(termo), texto, re.IGNORECASE))

def extrair_data(metadata: dict) -> str:
    """Tenta extrair uma data no formato dd-mm-aaaa, incluindo separadores como '.', '-', '_', '/', ou espaços."""
    filename = metadata.get("source", "")
    match = re.search(r'(\d{2})[.\-_/ ](\d{2})[.\-_/ ](\d{4})', filename)
    if match:
        dia, mes, ano = match.groups()
        return f"{ano}-{mes}-{dia}"  # formato ISO para fácil ordenação
    return "0000-00-00"

def filtrar_resultados_semanticos(resultados, palavras_chave):
    """
    Filtra os resultados que contêm TODAS as palavras-chave no texto
    e estão dentro do intervalo de anos selecionado.
    """
    from Scripts.utils import limpar_texto, contar_ocorrencias, extrair_data
    import streamlit as st

    if isinstance(palavras_chave, str):
        palavras_chave = [palavras_chave]

    docs_filtrados = []
    total_ocorrencias = 0

    # Pega intervalo selecionado no filtro
    ano_inicio = st.session_state.get("filtro_ano_inicio")
    ano_fim = st.session_state.get("filtro_ano_fim")

    for doc in resultados:
        texto = limpar_texto(doc.page_content)
        texto_lower = texto.lower()

        # Aplica filtro de palavras-chave (todas devem estar presentes)
        if not all(palavra.lower() in texto_lower for palavra in palavras_chave):
            continue

        data = extrair_data(doc.metadata)  # no formato YYYY-MM-DD
        ano_doc = int(data[:4]) if data[:4].isdigit() else None

        # Aplica filtro por ano (caso ano extraído seja válido)
        if ano_doc is not None and ano_inicio and ano_fim:
            if not (ano_inicio <= ano_doc <= ano_fim):
                continue

        ocorrencias_doc = sum(contar_ocorrencias(texto, palavra) for palavra in palavras_chave)
        total_ocorrencias += ocorrencias_doc

        docs_filtrados.append({
            "doc": doc,
            "texto": texto,
            "ocorrencias": ocorrencias_doc,
            "data": data
        })

    docs_filtrados.sort(key=lambda x: x["data"], reverse=True)
    return docs_filtrados, total_ocorrencias


def destacar_palavra(texto, palavras):
    if isinstance(palavras, str):
        palavras = [palavras]

    for palavra in palavras:
        if palavra:
            # Regex para encontrar a palavra inteira, sem quebrar palavras maiores
            pattern = re.compile(rf"\b({re.escape(palavra)})\b", flags=re.IGNORECASE)

            # Substituição com preservação do original (case) e sem sobrescrever tags
            texto = pattern.sub(r"<mark>\1</mark>", texto)
    
    return texto

def formatar_data(data_iso):
    """Converte AAAA-MM-DD para DD/MM/AAAA."""
    try:
        ano, mes, dia = data_iso.split("-")
        return f"{dia}/{mes}/{ano}"
    except:
        return data_iso

import re

def extrair_frase_relevante(texto, palavras_chave):
    import re

    if isinstance(palavras_chave, str):
        palavras_chave = [palavras_chave]

    frases = re.split(r'(?<=[.!?])\s+', texto)
    
    for frase in frases:
        for palavra in palavras_chave:
            if palavra and palavra.lower() in frase.lower():
                return frase.strip()

    # Se nenhuma palavra for encontrada, retorna o início do texto como fallback
    return frases[0].strip() if frases else texto[:300]

def exibir_resultados_formatados(docs_filtrados, palavra_chave=None, limite=5):
    import streamlit as st
    import os

    # Garante que as palavras-chave estejam em formato de lista
    if isinstance(palavra_chave, str):
        palavras_chave = [palavra_chave]
    elif isinstance(palavra_chave, list):
        palavras_chave = palavra_chave
    else:
        palavras_chave = []

    st.markdown("<style>mark {background-color: #ffd54f; padding: 2px 4px; border-radius: 4px;}</style>", unsafe_allow_html=True)

    total = len(docs_filtrados)
    limite_atual = st.session_state.get("limite_resultados", limite)

    for i, item in enumerate(docs_filtrados[:limite_atual], 1):
        doc = item["doc"]
        texto_completo = item["texto"]

        # Trecho curto + destaque
        texto_curto = extrair_frase_relevante(texto_completo, palavras_chave)
        texto_formatado_curto = destacar_palavra(texto_curto, palavras_chave)
        texto_formatado_completo = destacar_palavra(texto_completo, palavras_chave)

        # Link direto para o Google Drive
        id_drive = doc.metadata.get("id_drive")
        link_drive = f"https://drive.google.com/file/d/{id_drive}/view" if id_drive else "#"



        toggle_key = f"expandir_texto_{i}"
        expandir = st.toggle(f"🔍 Ver mais do resultado {i}", key=toggle_key)

        texto_formatado = texto_formatado_completo if expandir else texto_formatado_curto

        # Caixa com borda + conteúdo formatado
        st.markdown(f"""
        <div style="border:1px solid #ddd; border-radius:10px; padding:15px; margin-bottom:20px;">
            <h4>📄 Resultado {i}</h4>
            <div><strong>🗓 Data:</strong> {formatar_data(item['data'])}</div>
            <div><strong>📌 Fonte:</strong> `{os.path.basename(doc.metadata.get('source', 'Desconhecido'))}`</div>
            <div><strong>🔁 Ocorrências:</strong> {item['ocorrencias']}</div>
            <div><strong>🔗 Acesso completo:</strong> <a href="{link_drive}" target="_blank">Abrir no Google Drive</a></div>
            <p style='text-align: justify;'>[...] {texto_formatado} [...]</p>
        </div>
        """, unsafe_allow_html=True)

    # Botão para mostrar mais resultados
    if limite_atual < total:
        if st.button("🔁 Mostrar mais resultados", use_container_width=True, type="primary"):
            st.session_state.limite_resultados = limite_atual + limite
            st.rerun()



import os
import math

def format_time(horas):
    """
    Converte um valor em horas para uma string formatada considerando:
    - 60 minutos = 1 hora
    - 24 horas = 1 dia

    Exemplo: 1.41 horas -> "1 Hora e 41 Minutos"
    """
    # Converte horas para total de minutos (arredondando)
    total_minutos = round(horas * 60)
    
    # Calcula dias, horas e minutos
    dias = total_minutos // (24 * 60)
    restante = total_minutos % (24 * 60)
    hrs = restante // 60
    minutos = restante % 60

    partes = []
    if dias > 0:
        partes.append(f"{dias} Dia{'s' if dias != 1 else ''}")
    if hrs > 0:
        partes.append(f"{hrs} Hora{'s' if hrs != 1 else ''}")
    # Se minutos for zero e já houver outros componentes, não é necessário exibi-los
    if minutos > 0 or not partes:
        partes.append(f"{minutos} Minuto{'s' if minutos != 1 else ''}")
    
    return " e ".join(partes)



# Função para converter um valor em horas para um formato legível,
# considerando as seguintes conversões:
# 60 min = 1 hora, 24 h = 1 dia, 7 dias = 1 mês, 12 meses = 1 ano.
def format_time_extended(horas):
    # Converte horas para total de minutos (arredondando)
    total_minutos = round(horas * 60)
    # Calcula horas e minutos
    hrs = total_minutos // 60
    minutos = total_minutos % 60
    # Converte horas para dias e horas restantes
    dias = hrs // 24
    horas_restantes = hrs % 24
    # Converte dias para meses e dias restantes (7 dias = 1 mês)
    meses = dias // 7
    dias_restantes = dias % 7
    # Converte meses para anos e meses restantes (12 meses = 1 ano)
    anos = meses // 12
    meses_restantes = meses % 12
    
    partes = []
    if anos > 0:
        partes.append(f"{anos} Ano{'s' if anos != 1 else ''}")
    if meses_restantes > 0:
        partes.append(f"{meses_restantes} Mês{'es' if meses_restantes != 1 else ''}")
    if dias_restantes > 0:
        partes.append(f"{dias_restantes} Dia{'s' if dias_restantes != 1 else ''}")
    if horas_restantes > 0:
        partes.append(f"{horas_restantes} Hora{'s' if horas_restantes != 1 else ''}")
    if minutos > 0 or not partes:
        partes.append(f"{minutos} Minuto{'s' if minutos != 1 else ''}")
    return " e ".join(partes)