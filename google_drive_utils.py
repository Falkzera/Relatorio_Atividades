import json
import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
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
    from googleapiclient.http import MediaFileUpload
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

def read_parquet_files_from_drive(service, folder_id):
    """
    Lê todos os arquivos `.parquet` dentro de uma pasta e suas subpastas no Google Drive,
    e combina em um único DataFrame.
    """
    def list_files_and_folders_in_drive(folder_id):
        """
        Lista arquivos e pastas dentro de uma pasta no Google Drive.
        """
        query = f"'{folder_id}' in parents and trashed = false"
        results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
        return results.get('files', [])

    def get_all_parquet_files(folder_id):
        """
        Busca recursivamente todos os arquivos `.parquet` dentro da pasta e subpastas.
        """
        items = list_files_and_folders_in_drive(folder_id)
        parquet_files = []

        for item in items:
            if item['mimeType'] == 'application/vnd.google-apps.folder':
                parquet_files.extend(get_all_parquet_files(item['id'])) 
            elif item['name'].endswith('.parquet'):
                parquet_files.append(item)

        return parquet_files
    
    parquet_files = get_all_parquet_files(folder_id)

    dfs = []
    for file in parquet_files:
        request = service.files().get_media(fileId=file['id'])
        file_data = io.BytesIO()
        downloader = MediaIoBaseDownload(file_data, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        file_data.seek(0) 
        dfs.append(pd.read_parquet(file_data)) 

    if dfs:
        return pd.concat(dfs, ignore_index=True)
    else:
        return pd.DataFrame()


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

