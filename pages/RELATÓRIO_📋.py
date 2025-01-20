import os
import io
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from googleapiclient.http import MediaIoBaseDownload
from google_drive_utils import authenticate_service_account, read_parquet_files_from_drive
from datetime import datetime

st.set_page_config(layout='wide', page_title='Relatório de Atividades', page_icon='📊')

with st.container(): # LOGOTIPO/IMAGENS/TÍTULOS

    PET = "imagem/PET.png"
    st.sidebar.image(PET)
    st.sidebar.write('---')

    with st.container():
        col1, col2 = st.columns([3, 1])
        col1.title('Relatório de Atividades 📋')
        col2.image(PET)

with st.container(): # API GOOGLE DRIVE
    FOLDER_ID = "1d0KqEyocTO1lbnWS1u7hooSVJgv5Fz6Q"  # ID da pasta no Google Drive
    service = authenticate_service_account() 
    df = read_parquet_files_from_drive(service, FOLDER_ID)

    if df.empty:
        st.error("Nenhum arquivo .parquet encontrado na pasta do Google Drive.")
        st.stop()
    else:
        st.success("Dados carregados com sucesso!")

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
    for label, (col, options) in filtros.items():

        default_value = 'TODOS'
        if label == 'Ano':
            default_value = ano_atual if ano_atual in options else 'TODOS'
        elif label == 'Mês':
            default_value = mes_atual if mes_atual in options else 'TODOS'

        selecionado = st.sidebar.selectbox(
            f'Selecione o {label}:', 
            options, 
            index=options.index(default_value) if default_value in options else 0,  
            key=f"filtro_{label}" 
        )
        selecoes[label] = selecionado 
        if selecionado != 'TODOS':
            df = df[df[col] == selecionado]

df = df.sort_values(by="HORAS", ascending=False)

tabs1, tabs2, tabs3, tabs4 = st.tabs(['DISCENTES', 'ATIVIDADES', 'GERAL', 'CONSOLIDADO'])

with tabs1: # DISCENTES
    df_tabs1 = df.copy()
    df_tabs1 = df_tabs1.groupby(['ALUNO']).agg({'HORAS': 'sum'}).sort_values(by='HORAS', ascending=False).reset_index()

    col1, col2 = st.columns(2)

    with col1:
        st.metric('TOTAL DE HORAS', f'{df_tabs1["HORAS"].sum():.0f}')
    with col2:
        st.metric('TOTAL DE DISCENTES', f'{df_tabs1["ALUNO"].nunique()}')
 
    fig = go.Figure()
    fig.add_trace(go.Pie(labels=df_tabs1['ALUNO'], values=df_tabs1['HORAS'], hole=.3))
    fig.update_layout(title=f'Total de horas por discente')
    st.plotly_chart(fig, use_container_width=True, key='tab1_chart')

with tabs2: # DISCENTES
    df_tabs2 = df.copy()
    df_tabs2 = df_tabs2.groupby(['ATIVIDADE']).agg({'HORAS': 'sum'}).sort_values(by='HORAS', ascending=False).reset_index()

    col1, col2 = st.columns(2)

    with col1:
        st.metric('TOTAL DE HORAS', f'{df_tabs2["HORAS"].sum():.0f}')

    with col2: 
        st.metric('TOTAL DE ATIVIDADES', f'{df_tabs2["ATIVIDADE"].nunique()}')

    fig = go.Figure()
    fig.add_trace(go.Pie(labels=df_tabs2['ATIVIDADE'], values=df_tabs2['HORAS'], hole=.3))
    fig.update_layout(title=f'Total de horas por Atividade')
    st.plotly_chart(fig, use_container_width=True)

with tabs3: # GERAL
    df_tabs3 = df.copy()
    df_tabs3 = df_tabs3.groupby(['ALUNO', 'ATIVIDADE']).agg({'HORAS': 'sum'}).reset_index()

    col1, col2 = st.columns(2)

    with col1:
        df_tabs3_sum = df_tabs3.groupby('ALUNO').agg({'HORAS': 'sum'}).reset_index()
        df_tabs3_sum = df_tabs3_sum.sort_values(by='HORAS', ascending=False)
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(x=df_tabs3_sum['ALUNO'], y=df_tabs3_sum['HORAS'], marker=dict(color=df_tabs3_sum['HORAS'], colorscale='Blues')))
        fig_bar.update_layout(title='Total de horas por discente')
        st.plotly_chart(fig_bar, use_container_width=True, key='tab3_bar_chart')

    with col2:
        fig_pie = go.Figure()
        fig_pie.add_trace(go.Pie(labels=df_tabs3['ATIVIDADE'], values=df_tabs3['HORAS'], hole=.3))
        fig_pie.update_layout(title='Total de horas por Atividade')
        st.plotly_chart(fig_pie, use_container_width=True, key='tab3_pie_chart')

with tabs4: # CONSOLIDADO
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

    st.subheader(f"Périodo selecionado para o relatório consolidado: {mes_escolhido}/{ano_escolhido}")
    st.caption("Modifique o período selecionando nos filtros a esquerda.")

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
