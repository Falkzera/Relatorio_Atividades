import json
import io
import streamlit as st
import Scripts.utils as utils
from googleapiclient.http import MediaIoBaseUpload # type: ignore
from datetime import datetime
from Scripts.google_drive_utils import authenticate_service_account, read_parquet_files_from_drive


def CONSOLIDADO():

    with st.container(): # API GOOGLE DRIVE
        FOLDER_ID = "1d0KqEyocTO1lbnWS1u7hooSVJgv5Fz6Q"  # ID da pasta no Google Drive
        service = authenticate_service_account() 
        df = read_parquet_files_from_drive(service, FOLDER_ID)

        if df.empty:
            st.error("Nenhum arquivo .parquet encontrado na pasta do Google Drive.")
            st.stop()
        else:
            pass

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

        with st.expander("ℹ️ Informação", expanded=False):
            df_atividade['Período de Execução'] = df_atividade.apply(utils.clean_periodo_execucao, axis=1)
        df_atividade['Período de Execução'] = df_atividade['Período de Execução'].apply(lambda x: ', '.join(sorted(x.split(', '))))
        st.subheader(f"Périodo selecionado para o relatório consolidado: {mes_escolhido}/{ano_escolhido}")
        st.caption("Modifique o período selecionando nos filtros.")

        df_atividade['Período de Execução'] = df_atividade['Período de Execução'].astype(str)
        df_atividade['Período de Execução'] = df_atividade['Período de Execução'].str.split(', ').apply(lambda x: sorted(set(x)))
        df_atividade['Período de Execução'] = df_atividade['Período de Execução'].apply(lambda x: ', '.join(x))





        st.data_editor(df_atividade, hide_index=True)







        df_excel = utils.to_excel(df_atividade)
        st.download_button(
            label="Baixar relatório em Excel",
            data=df_excel,
            file_name=f'relatorio_consolidado_{mes_escolhido}-{ano_escolhido}.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            use_container_width=True,
            type="primary",
            icon="📥"
        )
        
    with st.container(): # Validação de relatorios enviados

        df_atividade, df_alunos, df_email = utils.data_load()

        selecione_ano = selecoes['Ano'] 
        selecione_mes = selecoes['Mês']  
        alunos = df_alunos['NOME'].tolist()
        total_alunos = len(alunos)
        pastas_alunos = utils.list_files_in_folder(service, FOLDER_ID)
        nomes_pastas = {pasta['name']: pasta['id'] for pasta in pastas_alunos}
        alunos_enviaram = []
        alunos_faltantes = []

        for aluno in alunos:
            if aluno in nomes_pastas:
                pasta_aluno_id = nomes_pastas[aluno]
                arquivos = utils.list_parquet_files(service, pasta_aluno_id)

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
        st.write('---')
        st.warning(f"📩 No período {selecione_mes}/{selecione_ano}, {enviados} de um total de {total_alunos} discentes enviaram seus relatórios.")

        if alunos_faltantes:
            st.error(f"🚨 Alunos que não enviaram o relatório para o período: {selecione_mes}/{selecione_ano}:")
            col1, col2, col3 = st.columns(3)
            for i, aluno in enumerate(alunos_faltantes):
                if i % 3 == 0:
                    col1.write(f"- {aluno}")
                elif i % 3 == 1:
                    col2.write(f"- {aluno}")
                else:
                    col3.write(f"- {aluno}")

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

            # def enviar_email(df_atividade, mes_escolhido, ano_escolhido):

            #     SMTP_SERVER = st.secrets["EMAIL"]["SMTP_SERVER"]
            #     SMTP_PORT = st.secrets["EMAIL"]["SMTP_PORT"]
            #     EMAIL_SENDER = st.secrets["EMAIL"]["EMAIL_SENDER"]
            #     EMAIL_PASSWORD = st.secrets["EMAIL"]["EMAIL_PASSWORD"]
            #     EMAIL_DESTINATARIO = ", ".join(df_email["EMAIL"].dropna().tolist())

            #     def to_excel(df):
            #         output = io.BytesIO()
            #         writer = pd.ExcelWriter(output, engine='xlsxwriter')
            #         df.to_excel(writer, sheet_name='Sheet1', index=False)
            #         writer.close()
            #         return output.getvalue()

            #     df_excel = to_excel(df_atividade)

            #     msg = MIMEMultipart()
            #     msg["From"] = EMAIL_SENDER
            #     msg["To"] = EMAIL_DESTINATARIO
            #     msg["Subject"] = f"Relatório Consolidado {mes_escolhido}/{ano_escolhido}"

            #     mensagem = f"""
            #         Este é um e-mail gerado automaticamente. Por favor, não responda a esta mensagem.

            #         Prezado(a),

            #         Segue em anexo o relatório consolidado referente a {mes_escolhido}/{ano_escolhido}. Caso haja qualquer inconsistência ou dúvida, entre em contato com a equipe responsável.

            #         Agradecemos sua atenção.

            #         Atenciosamente,  
            #         Programa de Educação Tutorial  
            #         PET - ECONOMIA
            #         """
            #     msg.attach(MIMEText(mensagem, "plain"))

            #     part = MIMEBase("application", "octet-stream")
            #     part.set_payload(df_excel)
            #     encoders.encode_base64(part)
            #     part.add_header(
            #         "Content-Disposition",
            #         f"attachment; filename=relatorio_consolidado_{mes_escolhido}-{ano_escolhido}.xlsx"
            #     )
            #     msg.attach(part)

            #     try:
            #         server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            #         server.starttls()
            #         server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            #         server.sendmail(EMAIL_SENDER, EMAIL_DESTINATARIO, msg.as_string())
            #         server.quit()
            #         st.success("✅ E-mail enviado com sucesso!")
            #         st.balloons()
            #     except Exception as e:
            #         st.error(f"❌ Erro ao enviar o e-mail, entre em contato com o Desenvolvedor. {e}")

            if nome_relatorio in envios:
                data_envio = envios[nome_relatorio]
                st.warning(f"⚠️ O relatório `{nome_relatorio}` já foi enviado em `{data_envio}`. Nenhum e-mail foi enviado novamente.")
                
                if st.button("🔄 Reenviar Relatório"):
                    utils.enviar_email(df_atividade, mes_escolhido, ano_escolhido)
                    data_envio = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    envios[nome_relatorio] = data_envio
                    save_envios_to_drive(envios, file_id)
                    st.success(f"✅ Relatório `{nome_relatorio}` reenviado em `{data_envio}`.")

            else:
                utils.enviar_email(df_atividade, mes_escolhido, ano_escolhido)
                data_envio = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                envios[nome_relatorio] = data_envio
                save_envios_to_drive(envios, file_id)
                st.success(f"✅ Relatório `{nome_relatorio}` enviado com sucesso em `{data_envio}`.")

    utils.atualizar_dados()