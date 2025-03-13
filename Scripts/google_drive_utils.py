import json
import streamlit as st
from google.oauth2.service_account import Credentials # type: ignore
from googleapiclient.discovery import build # type: ignore
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
import io
import pickle
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


CACHE_FILENAME = 'cache_parquet.pkl'
CACHE_FOLDER_ID = "1d0KqEyocTO1lbnWS1u7hooSVJgv5Fz6Q"  # Use o ID informado

def baixar_cache_do_drive(_service):
    query = f"name='{CACHE_FILENAME}' and '{CACHE_FOLDER_ID}' in parents and trashed = false"
    results = _service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])

    if files:
        file_id = files[0]['id']
        request = _service.files().get_media(fileId=file_id)
        file_data = io.BytesIO()
        downloader = MediaIoBaseDownload(file_data, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        file_data.seek(0)
        cache_dict = pickle.load(file_data)
        return cache_dict, file_id
    else:
        # Caso o arquivo não exista ainda
        return {}, None

def salvar_cache_no_drive(_service, cache_dict, file_id=None):
    file_data = io.BytesIO()
    pickle.dump(cache_dict, file_data)
    file_data.seek(0)
    media = MediaIoBaseUpload(file_data, mimetype='application/octet-stream')

    if file_id:
        _service.files().update(fileId=file_id, media_body=media).execute()
    else:
        file_metadata = {'name': CACHE_FILENAME, 'parents': [CACHE_FOLDER_ID]}
        _service.files().create(body=file_metadata, media_body=media).execute()

def get_all_parquet_files(_service, folder_id):
    query = f"'{folder_id}' in parents and trashed = false"
    results = _service.files().list(q=query, fields="files(id, name, mimeType)").execute()
    items = results.get('files', [])
    parquet_files = []
    for item in items:
        if item['mimeType'] == 'application/vnd.google-apps.folder':
            parquet_files += get_all_parquet_files(_service, item['id'])
        elif item['name'].endswith('.parquet'):
            parquet_files.append(item)
    return parquet_files

@st.cache_data(ttl=3600)
def baixar_parquet_do_drive(_service, file_id):
    request = _service.files().get_media(fileId=file_id)
    file_data = io.BytesIO()
    downloader = MediaIoBaseDownload(file_data, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    file_data.seek(0)
    return pd.read_parquet(file_data)

def read_parquet_files_from_drive(_service, folder_id='1d0KqEyocTO1lbnWS1u7hooSVJgv5Fz6Q'):
    # Baixa o cache persistente do Google Drive
    cache_local, cache_file_id = baixar_cache_do_drive(_service)
    if cache_local is None:
        cache_local = {}

    parquet_files = get_all_parquet_files(_service, folder_id)

    arquivos_no_drive = {file['id']: file['name'] for file in parquet_files}
    nomes_no_drive = set(arquivos_no_drive.values())

    # Remover arquivos do cache que não existem mais no drive ou possuem nome duplicado
    ids_para_remover = []
    for cached_id, cached_df in cache_local.items():
        cached_nome = next((file['name'] for file in parquet_files if file['id'] == cached_id), None)
        if cached_nome is None or cached_nome not in nomes_no_drive:
            ids_para_remover.append(cached_id)

    for id_antigo in ids_para_remover:
        del cache_local[id_antigo]

    # Identificar novos arquivos por ID
    novos_arquivos = [f for f in parquet_files if f['id'] not in cache_local]

    total_novos = len(novos_arquivos)
    progress_bar = st.progress(0)

    if total_novos > 0:
        st.sidebar.caption(f"Carregando {total_novos} novos arquivos do Drive...")
        for idx, file in enumerate(novos_arquivos):
            # Remover arquivo antigo (nome duplicado) do cache, se existir
            ids_com_mesmo_nome = [id_ for id_, nome in arquivos_no_drive.items()
                                  if nome == file['name'] and id_ in cache_local]
            for id_dup in ids_com_mesmo_nome:
                del cache_local[id_dup]

            # Adicionar novo arquivo ao cache
            df_novo = baixar_parquet_do_drive(_service, file['id'])
            cache_local[file['id']] = df_novo
            progress_bar.progress((idx + 1) / total_novos)
    else:
        st.sidebar.caption("Nenhum arquivo novo encontrado. Usando cache persistente.")

    # Salva o cache atualizado no Drive
    salvar_cache_no_drive(_service, cache_local, cache_file_id)

    # Junta todos os arquivos carregados
    df_completo = pd.concat(cache_local.values(), ignore_index=True)

    st.session_state.last_updated = pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%d/%m/%Y %H:%M:%S')

    return df_completo

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