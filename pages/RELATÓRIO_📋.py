import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import os
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from googleapiclient.http import MediaIoBaseDownload
import pandas as pd
import os
import io
from google_drive_utils import authenticate_service_account, read_parquet_files_from_drive


st.set_page_config(layout='wide', page_title='Relatório de Atividades', page_icon='📊')

with st.container(): # LOGOTIPO/IMAGENS/TÍTULOS

    # Imagem
    PET = "imagem/PET.png"
    st.sidebar.image(PET)
    st.sidebar.write('---')
    # Título
    with st.container():
        col1, col2 = st.columns([3, 1])
        col1.title('Relatório de Atividades 📋')
        col2.image(PET)

# Configurações do Google Drive
FOLDER_ID = "1d0KqEyocTO1lbnWS1u7hooSVJgv5Fz6Q"  # ID da pasta no Google Drive

# ============================
# Carregar Dados do Google Drive
# ============================
service = authenticate_service_account()  # Agora usa st.secrets dentro do google_drive_utils
df = read_parquet_files_from_drive(service, FOLDER_ID)

if df.empty:
    st.error("Nenhum arquivo .parquet encontrado na pasta do Google Drive.")
    # termina a execução do script
    st.stop()
else:
    st.success("Dados carregados com sucesso!")




with st.container(): # FILTROS ALUNO, DATA

    filtros = {
        'Aluno': ('ALUNO', ['TODOS'] + sorted(df['ALUNO'].unique().tolist())),
        'Ano': ('ANO', ['TODOS'] + sorted(df['ANO'].unique().tolist())),
        'Mês': ('MES', ['TODOS'] + sorted(df['MES'].unique().tolist()))
    }

    for label, (col, options) in filtros.items():
        selecionado = st.sidebar.selectbox(f'Selecione o {label}:', options)
        if selecionado != 'TODOS':
            df = df[df[col] == selecionado]


# Ordenar o DataFrame com base na coluna "HORAS"
df = df.sort_values(by="HORAS", ascending=False)


tabs1, tabs2, tabs3, tabs4 = st.tabs(['DISCENTES', 'ATIVIDADES', 'GERAL', 'CONSOLIDADO'])


with tabs1: # DISCENTES
    df_tabs1 = df.copy()
    df_tabs1 = df_tabs1.groupby(['ALUNO']).agg({'HORAS': 'sum'}).sort_values(by='HORAS', ascending=False).reset_index()

    col1, col2 = st.columns(2)

    with col1:
        st.metric('TOTAL DE HORAS', f'{df_tabs1["HORAS"].sum():.0f}')
    with col2:
        # Total de discentes
        st.metric('TOTAL DE DISCENTES', f'{df_tabs1["ALUNO"].nunique()}')
 
    max_horas = df_tabs1["HORAS"].values[0]

    st.data_editor(
        df_tabs1,
        column_config={
            "HORAS": st.column_config.ProgressColumn(
                "Horas",
                help="Total de horas",
                format="%f",
                min_value=0,
                max_value=max_horas,
            ),
        },
        hide_index=True,
        use_container_width=True,
    )
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_tabs1['ALUNO'], y=df_tabs1['HORAS'], marker=dict(color=df_tabs1['HORAS'], colorscale='Blues')))
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

    max_horas = df_tabs1["HORAS"].values[0]
    st.data_editor(
        df_tabs2,
        column_config={
            "HORAS": st.column_config.ProgressColumn(
                "Horas",
                help="Total de horas",
                format="%f",
                min_value=0,
                max_value=max_horas,
            ),
        },
        hide_index=True,
        use_container_width=True,
    )
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
                # Aplicar os mesmos filtros
                data = df.copy()
                data = data.sort_values(by=["ANO", "MES"], ascending=[False, False])
                data["HORAS"] = data["HORAS"].astype(int)

                try:
                    st.table(data)
                except IndexError as e:
                    st.error(f"Para o filtro aplicado não existe resultado: {e}")
