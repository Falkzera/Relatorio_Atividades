import json
import streamlit as st
from google.oauth2.service_account import Credentials # type: ignore
from googleapiclient.discovery import build # type: ignore
from googleapiclient.http import MediaIoBaseDownload # type: ignore
import io
import pandas as pd

def authenticate_service_account():
    """
    Autentica no Google Drive usando credenciais do secrets.toml (Streamlit).
    """
    SCOPES = ['https://www.googleapis.com/auth/drive']
    credentials_info = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    credentials = Credentials.from_service_account_info(credentials_info, scopes=SCOPES)
    return build('drive', 'v3', credentials=credentials)

def list_files_in_folder(service, folder_id):
    """
    Lista arquivos de uma pasta no Google Drive.
    """
    query = f"'{folder_id}' in parents and trashed = false"
    results = service.files().list(q=query, fields="files(id, name, modifiedTime)").execute()
    return results.get('files', [])

def download_file(service, file_id):
    """
    Faz o download de um arquivo do Google Drive para um objeto em memória.
    """
    request = service.files().get_media(fileId=file_id)
    file_data = io.BytesIO()
    downloader = MediaIoBaseDownload(file_data, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    file_data.seek(0)
    return file_data

def upload_file_to_drive(service, file_path, file_name, folder_id):
    """
    Faz upload de um arquivo para uma pasta no Google Drive.
    """
    from googleapiclient.http import MediaFileUpload # type: ignore
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }
    media = MediaFileUpload(file_path, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')

def create_folder_in_drive(service, folder_name, parent_folder_id):
    """
    Cria uma pasta no Google Drive. Se já existir, retorna o ID da pasta.
    """
    query = f"'{parent_folder_id}' in parents and name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])
    if items:
        return items[0]['id']
    else:
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_folder_id]
        }
        folder = service.files().create(body=folder_metadata, fields='id').execute()
        return folder.get('id')

def remove_duplicate_files_in_subfolders(service, folder_id):
    """
    Remove arquivos duplicados (.parquet) dentro de uma pasta e suas subpastas no Google Drive.
    Mantém apenas o arquivo mais recente baseado no `modifiedTime`.
    """
    def list_files_and_folders(folder_id):
        """
        Lista arquivos e subpastas dentro de uma pasta no Google Drive.
        """
        query = f"'{folder_id}' in parents and trashed = false"
        results = service.files().list(q=query, fields="files(id, name, mimeType, modifiedTime)").execute()
        return results.get('files', [])

    def process_folder(folder_id):
        """
        Processa uma pasta para verificar duplicatas de arquivos .parquet e as remove.
        """
        items = list_files_and_folders(folder_id)
        parquet_files = [item for item in items if item['name'].endswith('.parquet')]

        files_by_name = {}
        for file in parquet_files:
            name = file['name']
            if name not in files_by_name:
                files_by_name[name] = []
            files_by_name[name].append(file)

        for name, file_list in files_by_name.items():
            if len(file_list) > 1:
                file_list.sort(key=lambda x: x['modifiedTime'], reverse=True) 
                for file in file_list[1:]:
                    service.files().delete(fileId=file['id']).execute()
                    print(f"Excluído: {file['name']} (ID: {file['id']})")

        subfolders = [item for item in items if item['mimeType'] == 'application/vnd.google-apps.folder']
        for subfolder in subfolders:
            process_folder(subfolder['id'])

    # Iniciar o processamento da pasta principal
    process_folder(folder_id)















# #-------------------------------------------------------
# @st.cache_data(ttl=3600)  # Cache de 1 hora (3600 segundos)
# def read_parquet_files_from_drive(_service, folder_id):
#     """
#     Lê todos os arquivos .parquet dentro de uma pasta e suas subpastas no Google Drive,
#     e combina em um único DataFrame (com cache de 1 hora).
#     """
#     def list_files_and_folders_in_drive(folder_id):
#         query = f"'{folder_id}' in parents and trashed = false"
#         results = _service.files().list(q=query, fields="files(id, name, mimeType)").execute()
#         return results.get('files', [])

#     def get_all_parquet_files(folder_id):
#         items = list_files_and_folders_in_drive(folder_id)
#         parquet_files = []

#         for item in items:
#             if item['mimeType'] == 'application/vnd.google-apps.folder':
#                 parquet_files.extend(get_all_parquet_files(item['id']))
#             elif item['name'].endswith('.parquet'):
#                 parquet_files.append(item)

#         return parquet_files
    
#     parquet_files = get_all_parquet_files(folder_id)

#     dfs = []
#     for file in parquet_files:
#         request = _service.files().get_media(fileId=file['id'])
#         file_data = io.BytesIO()
#         downloader = MediaIoBaseDownload(file_data, request)
#         done = False
#         while not done:
#             status, done = downloader.next_chunk()
#         file_data.seek(0)
#         dfs.append(pd.read_parquet(file_data))

#     if dfs:
#         df = pd.concat(dfs, ignore_index=True)
#         # Atualiza o horário da última carga
#         st.session_state.last_updated = pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%d/%m/%Y %H:%M:%S')
#         return df
#     else:
#         return pd.DataFrame()

# # --------------------------------------------------
# # Para usar a função em seu código principal:

# # service = ...  # Sua conexão com o Google Drive
# # folder_id = ... # ID da pasta raiz

# # df = read_parquet_files_from_drive(service, folder_id)

# # --------------------------------------------------








# 2--------------------

# @st.cache_data(ttl=3600)  # Cache de 1 hora (3600 segundos)
# def read_parquet_files_from_drive(_service, folder_id):
#     """
#     Lê todos os arquivos .parquet dentro de uma pasta e suas subpastas no Google Drive,
#     e combina em um único DataFrame (com cache de 1 hora), exibindo o progresso da operação.
#     """
#     def list_files_and_folders_in_drive(folder_id):
#         query = f"'{folder_id}' in parents and trashed = false"
#         results = _service.files().list(q=query, fields="files(id, name, mimeType)").execute()
#         return results.get('files', [])

#     def get_all_parquet_files(folder_id):
#         items = list_files_and_folders_in_drive(folder_id)
#         parquet_files = []
#         for item in items:
#             if item['mimeType'] == 'application/vnd.google-apps.folder':
#                 parquet_files.extend(get_all_parquet_files(item['id']))
#             elif item['name'].endswith('.parquet'):
#                 parquet_files.append(item)
#         return parquet_files

#     # Recupera todos os arquivos .parquet recursivamente
#     parquet_files = get_all_parquet_files(folder_id)
    
#     dfs = []
#     total_files = len(parquet_files)
    
#     # Inicializa a barra de progresso para o processamento dos arquivos
#     progress_bar = st.progress(0)
#     st.write("Iniciando processamento dos arquivos .parquet...")
    
#     for idx, file in enumerate(parquet_files):
#         st.write(f"Baixando e lendo: {file['name']}")
#         request = _service.files().get_media(fileId=file['id'])
#         file_data = io.BytesIO()
#         downloader = MediaIoBaseDownload(file_data, request)
#         done = False
#         while not done:
#             status, done = downloader.next_chunk()
#             # Aqui você pode, se desejar, exibir o progresso do download individual
#             # Por exemplo, exibindo status.progress() ou similares.
#         file_data.seek(0)
#         dfs.append(pd.read_parquet(file_data))
#         # Atualiza a barra de progresso global
#         progress_bar.progress((idx + 1) / total_files)
    
#     if dfs:
#         df = pd.concat(dfs, ignore_index=True)
#         # Atualiza o horário da última carga
#         st.session_state.last_updated = pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%d/%m/%Y %H:%M:%S')
#         st.write("Processamento concluído.")
#         return df
#     else:
#         st.write("Nenhum arquivo .parquet encontrado.")
#         return pd.DataFrame()



@st.cache_data(ttl=3600)
def read_parquet_files_from_drive(_service, folder_id):
    """
    Lê todos os arquivos .parquet dentro de uma pasta e suas subpastas no Google Drive,
    combinando os arquivos já carregados (salvos em cache no session_state) com os novos.
    Se um arquivo for atualizado (ID alterado), ele será recarregado.
    """
    # Inicializa o cache de arquivos, se ainda não existir
    if "cached_parquet_files" not in st.session_state:
        st.session_state["cached_parquet_files"] = {}

    def list_files_and_folders_in_drive(folder_id):
        query = f"'{folder_id}' in parents and trashed = false"
        results = _service.files().list(q=query, fields="files(id, name, mimeType)").execute()
        return results.get('files', [])

    def get_all_parquet_files(folder_id):
        items = list_files_and_folders_in_drive(folder_id)
        parquet_files = []
        for item in items:
            if item['mimeType'] == 'application/vnd.google-apps.folder':
                parquet_files.extend(get_all_parquet_files(item['id']))
            elif item['name'].endswith('.parquet'):
                parquet_files.append(item)
        return parquet_files

    # Recupera todos os arquivos .parquet disponíveis na pasta e subpastas
    parquet_files = get_all_parquet_files(folder_id)

    # Identifica os arquivos que ainda não foram carregados (por ID)
    new_files = [file for file in parquet_files if file["id"] not in st.session_state["cached_parquet_files"]]

    total_new = len(new_files)
    progress_bar = st.progress(0)
    
    if total_new > 0:
        st.sidebar.caption(f"Processando {total_new} novos arquivos .parquet...")
        for idx, file in enumerate(new_files):
            print(f"Baixando e lendo: {file['name']}")
            request = _service.files().get_media(fileId=file['id'])
            file_data = io.BytesIO()
            downloader = MediaIoBaseDownload(file_data, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            file_data.seek(0)
            df_file = pd.read_parquet(file_data)
            # Armazena o DataFrame no cache (session_state) para uso futuro
            st.session_state["cached_parquet_files"][file["id"]] = df_file
            progress_bar.progress((idx + 1) / total_new)
    else:
        st.sidebar.caption("Nenhum novo arquivo .parquet encontrado. Utilizando arquivos previamente carregados.")

    # Combina os DataFrames dos arquivos que estão na pasta atual e foram armazenados no cache
    dfs = []
    current_file_ids = {file["id"] for file in parquet_files}
    for file_id in current_file_ids:
        if file_id in st.session_state["cached_parquet_files"]:
            dfs.append(st.session_state["cached_parquet_files"][file_id])
    
    if dfs:
        df = pd.concat(dfs, ignore_index=True)
        st.session_state.last_updated = pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%d/%m/%Y %H:%M:%S')
        st.sidebar.caption("Processamento concluído.")
        return df
    else:
        st.write("Nenhum arquivo .parquet encontrado.")
        return pd.DataFrame()







# # nova tentativa
# @st.cache_data(ttl=3600)  # Cache de 1 hora (3600 segundos)
# def read_parquet_files_from_drive(_service, folder_id):
#     """
#     Lê todos os arquivos .parquet dentro de uma pasta e suas subpastas no Google Drive,
#     combinando-os em um único DataFrame.
    
#     Melhorias:
#     - Percurso iterativo (fila) para listar arquivos sem usar "in ancestors"
#     - Download e leitura dos arquivos de forma sequencial com retry e backoff exponencial,
#       garantindo maior estabilidade frente a erros SSL.
#     """
#     import io
#     import time
#     import pandas as pd
#     from googleapiclient.http import MediaIoBaseDownload

#     def list_all_parquet_files(root_folder_id):
#         queue = [root_folder_id]
#         parquet_files = []
#         while queue:
#             current_folder = queue.pop(0)
#             query = f"'{current_folder}' in parents and trashed = false"
#             results = _service.files().list(q=query, fields="files(id, name, mimeType)").execute()
#             items = results.get('files', [])
#             for item in items:
#                 if item['mimeType'] == 'application/vnd.google-apps.folder':
#                     queue.append(item['id'])
#                 elif item['name'].endswith('.parquet'):
#                     parquet_files.append(item)
#         return parquet_files

#     # Lista os arquivos .parquet
#     parquet_files = list_all_parquet_files(folder_id)

#     def download_and_read(file):
#         max_attempts = 3
#         for attempt in range(max_attempts):
#             try:
#                 request = _service.files().get_media(fileId=file['id'])
#                 file_data = io.BytesIO()
#                 downloader = MediaIoBaseDownload(file_data, request)
#                 done = False
#                 while not done:
#                     status, done = downloader.next_chunk()
#                 file_data.seek(0)
#                 return pd.read_parquet(file_data)
#             except Exception as e:
#                 print(
#                     f"Tentativa {attempt+1} de {max_attempts} falhou para o arquivo "
#                     f"{file['name']} ({file['id']}): {e}"
#                 )
#                 time.sleep(2 ** attempt)  # Backoff exponencial
#         print(f"Falha ao processar o arquivo {file['name']} ({file['id']}) após {max_attempts} tentativas.")
#         return None

#     # Processa cada arquivo sequencialmente
#     dfs = []
#     for file in parquet_files:
#         df = download_and_read(file)
#         if df is not None:
#             dfs.append(df)

#     if dfs:
#         df_final = pd.concat(dfs, ignore_index=True)
#         st.session_state.last_updated = pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%d/%m/%Y %H:%M:%S')
#         return df_final
#     else:
#         return pd.DataFrame()

















def download_file_by_name(service, folder_id, file_name):
    """
    Busca e baixa um arquivo específico pelo nome dentro de uma pasta no Google Drive.

    Args:
        service: Serviço autenticado da API do Google Drive.
        folder_id: ID da pasta no Google Drive onde o arquivo está localizado.
        file_name: Nome do arquivo a ser buscado.

    Returns:
        Objeto de arquivo em memória (BytesIO) ou None se o arquivo não for encontrado.
    """
    # Listar arquivos na pasta
    files = list_files_in_folder(service, folder_id)
    
    # Filtrar pelo nome do arquivo
    matching_files = [file for file in files if file['name'] == file_name]
    
    if not matching_files:
        st.error(f"Arquivo '{file_name}' não encontrado na pasta.")
        return None
    
    file_id = matching_files[0]['id']
    
    # Fazer o download do arquivo
    file_data = download_file(service, file_id)
    return file_data

