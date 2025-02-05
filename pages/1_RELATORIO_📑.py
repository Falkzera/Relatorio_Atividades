import os
import json
import io
import smtplib
import calendar
import pandas as pd
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload # type: ignore
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
from Scripts.google_drive_utils import (
    authenticate_service_account,
    create_folder_in_drive,
    upload_file_to_drive,
    remove_duplicate_files_in_subfolders,
    download_file_by_name,
    read_parquet_files_from_drive
)
from Models.marca import display_sidebar, display_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

st.set_page_config(layout='wide', page_title='Relatório de Atividades', page_icon='📊')

display_header("Relatório de Atividades 📝")

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("Você precisa fazer login para acessar esta página 🔐.")
    display_sidebar()
    st.stop()

else:

    tabs = st.tabs(["Relatório de Atividades", "Relatório Consolidado"])

    with tabs[0]: # RELATÓRIO DE ATIVIDADES

        with st.container(): # API GOOGLE DRIVE
            
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
            df_atividade, df_alunos, df_email = data_load()

            with st.container(): # CONFIGURAÇÕES de DATA

                ano_atual = datetime.now().year
                ano_passado = ano_atual - 1
                mes_antes = datetime.now().month - 1 if datetime.now().month > 1 else 12
                ano_antes = ano_atual if datetime.now().month > 1 else ano_passado
                mes_atual = datetime.now().month
                
            with st.container(): # TITULO

                aluno = st.sidebar.selectbox('Selecione o Aluno:', df_alunos['NOME'])
                st.title(f'Discente: **{aluno}**')
                st.info('Preencha os campos abaixo.')
                st.sidebar.title('Informações: ')
                
            with st.container():  # FORMULARIO
                col1, col2, col3 = st.columns(3)
                
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
                            st.balloons()














    with tabs[1]: # RELATÓRIO CONSOLIDADO

        with st.container(): # API GOOGLE DRIVE
            FOLDER_ID = "1d0KqEyocTO1lbnWS1u7hooSVJgv5Fz6Q"  # ID da pasta no Google Drive
            service = authenticate_service_account() 
            df = read_parquet_files_from_drive(service, FOLDER_ID)

            if df.empty:
                st.error("Nenhum arquivo .parquet encontrado na pasta do Google Drive.")
                st.stop()
            else:
                st.success("Dados carregados com sucesso!")

        with st.container(): # Funções para verificar envio
        
            def list_files_in_folder(service, folder_id):
                query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder'"
                response = service.files().list(q=query, fields="files(id, name)").execute()
                return response.get('files', [])

            def list_parquet_files(service, folder_id):
                query = f"'{folder_id}' in parents and mimeType='application/octet-stream' and name contains '.parquet'"
                response = service.files().list(q=query, fields="files(id, name)").execute()
                return response.get('files', [])
     
        with st.container():  # FILTROS ALUNO, DATA

            agora = datetime.now()
            ano_atual = agora.year
            mes_atual = agora.month - 1 if agora.month > 1 else 12
            if agora.month == 1: 
                ano_atual -= 1

            filtros = {
                'Aluno': ('ALUNO', ['TODOS'] + sorted(df['ALUNO'].unique().tolist())),
                'Ano': ('ANO', ['TODOS'] + sorted(df['ANO'].unique().tolist())),
                'Mês': ('MES', ['TODOS'] + sorted(df['MES'].unique().tolist()))
            }

            selecoes = {}  
            with st.expander("**:blue[FILTROS]**"):  # FILTROS

                for label, (col, options) in filtros.items():
                    default_value = 'TODOS'
                    if label == 'Ano':
                        default_value = ano_atual if ano_atual in options else 'TODOS'
                    elif label == 'Mês':
                        default_value = mes_atual if mes_atual in options else 'TODOS'

                    selecionado = st.selectbox(
                        f'Selecione o {label}:', 
                        options, 
                        index=options.index(default_value) if default_value in options else 0,  
                        key=f"filtro_{label}" 
                    )
                    selecoes[label] = selecionado 
                    if selecionado != 'TODOS':
                        df = df[df[col] == selecionado]

        df = df.sort_values(by="HORAS", ascending=False)

        with st.container(): # CONSOLIDADO
            df_atividade = df.groupby('ATIVIDADE').agg({
                'JUSTIFICATIVA': 'first',
                'RESULTADO': 'first',
                'ALUNO': lambda x: ', '.join(sorted(set(x)))
            }).reset_index()

            df_atividade = df_atividade.merge(
                df[['ATIVIDADE', 'Período de Execução']].drop_duplicates(),
                on='ATIVIDADE',
                how='left'
            )
            df_atividade = df_atividade[['ATIVIDADE', 'ALUNO','Período de Execução', 'JUSTIFICATIVA', 'RESULTADO']]
            df_atividade.columns = ['Nome da Atividade', 'Discentes Envolvidos', 'Período de Execução', 'Justificativa', 'Resultados Esperados']
            ano_escolhido = selecoes.get('Ano', 'TODOS')
            mes_escolhido = selecoes.get('Mês', 'TODOS')

            df_atividade = df_atividade.groupby('Nome da Atividade').agg({
                'Discentes Envolvidos': lambda x: ', '.join(sorted(set(x))),
                'Período de Execução': lambda x: ', '.join(sorted(set(x))),
                'Justificativa': 'first',
                'Resultados Esperados': 'first'
            }).reset_index()

            def clean_periodo_execucao(row):
                periodo_execucao = row['Período de Execução']
                if 'Durante o mês' in periodo_execucao:
                    dias = [dia for dia in periodo_execucao.split(', ') if dia != 'Durante o mês']
                    if dias:
                        st.warning(f"A atividade '{row['Nome da Atividade']}' teve 'Durante o mês' removido, pois outros dias foram especificados por outros membros.")
                        return ', '.join(dias)   
                return periodo_execucao

            df_atividade['Período de Execução'] = df_atividade.apply(clean_periodo_execucao, axis=1)
            df_atividade['Período de Execução'] = df_atividade['Período de Execução'].apply(lambda x: ', '.join(sorted(x.split(', '))))
            st.subheader(f"Périodo selecionado para o relatório consolidado: {mes_escolhido}/{ano_escolhido}")
            st.caption("Modifique o período selecionando nos filtros a esquerda.")

            df_atividade['Período de Execução'] = df_atividade['Período de Execução'].astype(str)
            df_atividade['Período de Execução'] = df_atividade['Período de Execução'].str.split(', ').apply(lambda x: sorted(set(x)))
            df_atividade['Período de Execução'] = df_atividade['Período de Execução'].apply(lambda x: ', '.join(x))
            st.table(df_atividade)

            def to_excel(df):
                output = io.BytesIO()
                writer = pd.ExcelWriter(output, engine='xlsxwriter')
                df.to_excel(writer, sheet_name='Sheet1', index=False)
                writer.close()
                processed_data = output.getvalue()
                return processed_data

            df_excel = to_excel(df_atividade)
            st.download_button(
                label="Baixar relatório em Excel",
                data=df_excel,
                file_name=f'relatorio_consolidado_{mes_escolhido}-{ano_escolhido}.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

        with st.container(): # Validação de relatorios enviados

            selecione_ano = selecoes['Ano'] 
            selecione_mes = selecoes['Mês']  
            alunos = df_alunos['NOME'].tolist()
            total_alunos = len(alunos)
            pastas_alunos = list_files_in_folder(service, FOLDER_ID)
            nomes_pastas = {pasta['name']: pasta['id'] for pasta in pastas_alunos}
            alunos_enviaram = []
            alunos_faltantes = []

            for aluno in alunos:
                if aluno in nomes_pastas:
                    pasta_aluno_id = nomes_pastas[aluno]
                    arquivos = list_parquet_files(service, pasta_aluno_id)

                    encontrou_relatorio = False
                    for arquivo in arquivos:
                        nome_arquivo = arquivo['name']
                        partes = nome_arquivo.split("_")

                        if len(partes) >= 3:  
                            numero_mes = partes[1]  
                            ano_no_arquivo = partes[2].split(".")[0]  

                            if str(numero_mes) == str(selecione_mes) and str(ano_no_arquivo) == str(selecione_ano):
                                encontrou_relatorio = True
                                break  

                    if encontrou_relatorio:
                        alunos_enviaram.append(aluno)
                    else:
                        alunos_faltantes.append(aluno)
                else:
                    alunos_faltantes.append(aluno)

            enviados = len(alunos_enviaram)
            st.warning(f"📩 Relatórios enviados para {selecione_mes}/{selecione_ano}: **{enviados}/{total_alunos}**")

            if alunos_faltantes:
                st.error(f"🚨 Alunos que ainda não enviaram o relatório de {selecione_mes}/{selecione_ano}:")
                for aluno in alunos_faltantes:
                    st.write(f"- {aluno}")
                    

            if not alunos_faltantes:
                st.success("🎉 Todos os alunos enviaram o relatório!")

                ### 🔹 Função para buscar o JSON de envios no Google Drive
                def get_envios_from_drive():
                    query = f"'{FOLDER_ID}' in parents and name='envios.json' and mimeType='application/json'"
                    results = service.files().list(q=query, fields="files(id, name)").execute()
                    files = results.get("files", [])

                    if files:
                        file_id = files[0]["id"]
                        request = service.files().get_media(fileId=file_id)
                        file_data = request.execute()
                        file_content = json.loads(file_data.decode("utf-8"))
                        return file_content, file_id
                    return {}, None  # Retorna um dicionário vazio se não existir

                ### 🔹 Função para salvar o JSON no Google Drive
                def save_envios_to_drive(data, file_id=None):
                    json_data = json.dumps(data, indent=4)
                    file_stream = io.BytesIO(json_data.encode("utf-8"))

                    media = MediaIoBaseUpload(file_stream, mimetype="application/json")

                    if file_id:
                        service.files().update(fileId=file_id, media_body=media).execute()
                    else:
                        file_metadata = {
                            "name": "envios.json",
                            "mimeType": "application/json",
                            "parents": [FOLDER_ID],
                        }
                        service.files().create(body=file_metadata, media_body=media).execute()

                envios, file_id = get_envios_from_drive()

                nome_relatorio = f"relatorio_consolidado_{mes_escolhido}-{ano_escolhido}.xlsx"

                def enviar_email(df_atividade, mes_escolhido, ano_escolhido):

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

                if nome_relatorio in envios:
                    data_envio = envios[nome_relatorio]
                    st.warning(f"⚠️ O relatório `{nome_relatorio}` já foi enviado em `{data_envio}`. Nenhum e-mail foi enviado novamente.")
                    
                    if st.button("🔄 Reenviar Relatório"):
                        enviar_email(df_atividade, mes_escolhido, ano_escolhido)
                        data_envio = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                        envios[nome_relatorio] = data_envio
                        save_envios_to_drive(envios, file_id)
                        st.success(f"✅ Relatório `{nome_relatorio}` reenviado em `{data_envio}`.")

                else:
                    enviar_email(df_atividade, mes_escolhido, ano_escolhido)
                    data_envio = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    envios[nome_relatorio] = data_envio
                    save_envios_to_drive(envios, file_id)
                    st.success(f"✅ Relatório `{nome_relatorio}` enviado com sucesso em `{data_envio}`.")

    display_sidebar()