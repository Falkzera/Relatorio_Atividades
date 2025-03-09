import os
import calendar
import pandas as pd
import streamlit as st
import Scripts.utils as utils
from datetime import datetime
from Scripts.google_drive_utils import authenticate_service_account, create_folder_in_drive, upload_file_to_drive,  remove_duplicate_files_in_subfolders

def RELATORIO():

    @st.cache_data(ttl= 60 * 60 * 24)
    def carregamento():

        df_atividade, df_alunos, df_email = utils.data_load()
        return df_atividade, df_alunos, df_email
    
    df_atividade, df_alunos, df_email = carregamento()

    ano_atual = datetime.now().year
    ano_passado = ano_atual - 1
    mes_antes = datetime.now().month - 1 if datetime.now().month > 1 else 12
    ano_antes = ano_atual if datetime.now().month > 1 else ano_passado
    mes_atual = datetime.now().month
    
    st.sidebar.write('---')
    st.sidebar.title('Preencha as informações: ')
    aluno = st.sidebar.selectbox('Selecione o Aluno:', df_alunos['NOME'])
    st.title(f'**Discente:** *{aluno}*')
    st.info('Preencha os campos abaixo.')
    
    with st.container():  # FORMULARIO
        col1, col2, col3 = st.columns(3)
        
        with col1:
            quantas_atividades = st.sidebar.number_input('Quantas atividades você vai preencher?', 1, 10, 1)
            ano = st.sidebar.number_input('Selecione o ano:', 2020, ano_atual, value=ano_atual)
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

        with col3:
            dias = []
            max_dia = calendar.monthrange(ano, selecione_mes)[1] 
            opcoes_dias = ['Durante o mês'] + list(range(1, max_dia + 1))

            for i in range(quantas_atividades):
                dia = st.multiselect(
                    f'Selecione o(s) dia(s) da atividade {i + 1}:',
                    options=opcoes_dias,
                    key=f'dia_{i + 1}',
                    default=['Durante o mês']
                )
                dias.append(", ".join(map(str, dia)))

    with st.container():  # RELATÓRIO

        relatorio_pronto = pd.DataFrame(
            {'ANO': ano, 
            'MES': selecione_mes, 
            'ALUNO': aluno,
            'ATIVIDADE': atividades, 
            'JUSTIFICATIVA': '', 
            'RESULTADO': '',
            'HORAS': horas, 
            'Período de Execução': dias})
        
        relatorio_pronto['HORAS'] = relatorio_pronto['HORAS'].astype(int)

        for i, atividade in enumerate(relatorio_pronto['ATIVIDADE']):
            row = df_atividade[df_atividade['ATIVIDADES'] == atividade]

            if not row.empty:
                relatorio_pronto.at[i, 'JUSTIFICATIVA'] = row['JUSTIFICATIVA'].iloc[0]
                relatorio_pronto.at[i, 'RESULTADO'] = row['RESULTADO'].iloc[0]
            else:
                st.sidebar.warning(f"A atividade '{atividade}' não foi encontrada no DataFrame df_atividades.")

    with st.container(): # VALIDAÇÃO
        
        erros = False
        for i, dia in enumerate(dias):
            if 'Durante o mês' in dia.split(", ") and len(dia.split(", ")) > 1:
                erros = True
        
        if relatorio_pronto['ATIVIDADE'].duplicated().any():
            st.sidebar.error(f'Atividades duplicadas: {relatorio_pronto["ATIVIDADE"].duplicated().sum()}')
            duplicated_activities = relatorio_pronto[relatorio_pronto["ATIVIDADE"].duplicated()]["ATIVIDADE"].tolist()
            st.sidebar.error(f'Nome da(s) atividade(s) duplicada(s): **{", ".join(duplicated_activities)}**')
        
        elif erros:
            st.sidebar.error(f"A atividade {i + 1} não pode ter 'Durante o mês' selecionado junto com outros dias.")

        elif relatorio_pronto['HORAS'].isnull().any():
            st.sidebar.error('Horas não preenchidas.')

        elif relatorio_pronto['HORAS'].eq(0).any():
            st.sidebar.error('Atividade(s) sem horas preenchidas: **{}**'.format(', '.join(relatorio_pronto[relatorio_pronto['HORAS'].eq(0)]['ATIVIDADE'].tolist())))
        
        elif relatorio_pronto['Período de Execução'].isnull().any():
            st.sidebar.error('Dia não preenchido.')

        elif relatorio_pronto['Período de Execução'].eq('').any():
            st.sidebar.error('Atividade(s) sem dia preenchido: **{}**'.format(', '.join(relatorio_pronto[relatorio_pronto['DIA'].eq('')]['ATIVIDADE'].tolist())))
                            
        elif relatorio_pronto['HORAS'].sum() < 3:
            st.sidebar.warning('Total de horas menor que 3.')

        else:
            st.write('---')
            st.sidebar.write(f'**Período de referência:** {selecione_mes}/{ano}')
            st.sidebar.write(f'**Total de horas:** {relatorio_pronto["HORAS"].sum()}h')
            st.sidebar.info(f'Relatório pronto.')

            st.title('Visualização do relatório')
            st.info('Verifique se as informações estão corretas antes de enviar.')

            st.data_editor(relatorio_pronto, hide_index=True)

            with st.container(): # ENVIO
                FOLDER_ID = "1d0KqEyocTO1lbnWS1u7hooSVJgv5Fz6Q"
                if st.sidebar.button('Enviar', help='Clique para enviar o relatório', icon='📨', use_container_width=True, type='primary'):

                    service = authenticate_service_account()
                    aluno_folder_id = create_folder_in_drive(service, aluno,FOLDER_ID)
                    local_path = f'{aluno}_{selecione_mes}_{ano}.parquet'
                    relatorio_pronto.to_parquet(local_path, index=False)
                    file_id = upload_file_to_drive(service, local_path, os.path.basename(local_path), aluno_folder_id)
                    os.remove(local_path)
                    remove_duplicate_files_in_subfolders(service, aluno_folder_id)

                    st.sidebar.success(f'Relatório enviado com sucesso! ID do arquivo: {file_id}')
                    st.balloons()
