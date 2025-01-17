import pandas as pd
import streamlit as st
from datetime import datetime
from google_drive_utils import authenticate_service_account, upload_file_to_drive
import os

st.set_page_config(layout='wide', page_title='Relatório de Atividades', page_icon='📊')

with st.container(): # DATA_BASE
    @st.cache_data(ttl=84600)
    def data_load():
        atividade = pd.read_excel('data/atividade.xlsx')
        alunos = pd.read_csv('data/alunos.csv')
        return atividade, alunos
    df_atividade, df_alunos = data_load()

with st.container(): # CONFIGURAÇÕES de DATA

    ano_atual = datetime.now().year
    ano_passado = ano_atual - 1
    mes_antes = datetime.now().month - 1 if datetime.now().month > 1 else 12
    ano_antes = ano_atual if datetime.now().month > 1 else ano_passado
    mes_atual = datetime.now().month

with st.container(): # LOGOTIPO/IMAGENS/TÍTULOS

    PET = "imagem/PET.png"
    st.sidebar.image(PET)
    st.sidebar.write('---')
    # Título
    with st.container():
        col1, col2 = st.columns([3, 1])
        col1.title('Relatório de Atividades')
        col2.image(PET)

with st.container(): # TITULO

    aluno = st.sidebar.selectbox('Selecione o Aluno:', df_alunos['NOME'])
    st.title(f'Discente: **{aluno}**')
    st.info('Preencha os campos abaixo.')
    st.sidebar.title('Informações: ')
    
with st.container():  # FORMULARIO
    col1, col2 = st.columns(2)
    
    with col1:
        quantas_atividades = st.sidebar.number_input('Quantas atividades você vai preencher?', 1, 10, 1)
        ano = st.sidebar.number_input('Selecione o ano:', ano_passado, ano_atual, value=ano_atual)
        selecione_mes = st.sidebar.selectbox('Selecione o mês:', range(1, 13), index=mes_antes-1)
        if ano == ano_atual and selecione_mes > mes_atual:
            st.sidebar.error('Não é possível selecionar um mês futuro.')
    atividades = []
    horas = []

    with col1:
        disponiveis = df_atividade['ATIVIDADES'].unique().copy()
        for i in range(quantas_atividades):
            atividade = st.selectbox(f'Selecione a atividade {i + 1}:', disponiveis, key=f'atividade_{i + 1}')
            atividades.append(atividade)

    with col2:
        for i in range(quantas_atividades):
            hora = st.number_input(f'Defina a quantidade de horas {i + 1}:', 0, 100, 0, key=f'horas_{i + 1}')
            horas.append(hora)

with st.container():  # RELATÓRIO
    relatorio_pronto = pd.DataFrame({'ANO': ano, 'MES': selecione_mes, 'ALUNO': aluno,'ATIVIDADE': atividades, 'HORAS': horas})
    relatorio_pronto['HORAS'] = relatorio_pronto['HORAS'].astype(float)

with st.container(): # VALIDAÇÃO

    if relatorio_pronto['ATIVIDADE'].duplicated().any():
        st.sidebar.error(f'Atividades duplicadas: {relatorio_pronto["ATIVIDADE"].duplicated().sum()}')
        duplicated_activities = relatorio_pronto[relatorio_pronto["ATIVIDADE"].duplicated()]["ATIVIDADE"].tolist()
        st.sidebar.error(f'Nome da(s) atividade(s) duplicada(s): **{", ".join(duplicated_activities)}**')

    elif relatorio_pronto['HORAS'].isnull().any():
        st.sidebar.error('Horas não preenchidas.')

    elif relatorio_pronto['HORAS'].eq(0).any():
        st.sidebar.error('Horas não preenchidas.')
        st.sidebar.error('Atividade(s) sem horas preenchidas: **{}**'.format(', '.join(relatorio_pronto[relatorio_pronto['HORAS'].eq(0)]['ATIVIDADE'].tolist())))
    
    elif relatorio_pronto['HORAS'].sum() < 10:
        st.sidebar.warning('Total de horas menor que 10.')

    else:
        st.write('---')
        st.sidebar.write(f'**Período de referência:** {selecione_mes}/{ano}')
        st.sidebar.write(f'**Total de horas:** {relatorio_pronto["HORAS"].sum()}h')
        st.sidebar.info(f'Relatório pronto.')

        st.data_editor(
        relatorio_pronto,
        column_config={
            "HORAS": st.column_config.ProgressColumn(
                "Horas",
                help="Total de horas",
                format="%f",
                min_value=0,
                max_value=relatorio_pronto['HORAS'].max(),
            ),
        },
        hide_index=True,
    )

with st.container(): # ENVIO
    from google_drive_utils import (
        authenticate_service_account,
        create_folder_in_drive,
        upload_file_to_drive,
        remove_duplicate_files_in_subfolders
    )

    TARGET_FOLDER_ID = "1d0KqEyocTO1lbnWS1u7hooSVJgv5Fz6Q"

    if st.sidebar.button('Enviar'):

        service = authenticate_service_account()

        aluno_folder_id = create_folder_in_drive(service, aluno, TARGET_FOLDER_ID)
        local_path = f'{aluno}_{selecione_mes}_{ano}.parquet'
        relatorio_pronto.to_parquet(local_path, index=False)
        file_id = upload_file_to_drive(service, local_path, os.path.basename(local_path), aluno_folder_id)
        os.remove(local_path)
        remove_duplicate_files_in_subfolders(service, aluno_folder_id)

        st.sidebar.success(f'Relatório enviado com sucesso! ID do arquivo: {file_id}')
