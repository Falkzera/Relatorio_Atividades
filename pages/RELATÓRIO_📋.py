import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import os

st.set_page_config(layout='wide', page_title='Relatório de Atividades', page_icon='📊')

with st.container(): # DATA_BASE    
    def data_load():
        pasta = 'relatorio/'
        df = pd.concat([pd.read_parquet(os.path.join(root, f)) for root, _, files in os.walk(pasta) for f in files if f.endswith('.parquet')])
        # df['DATA'] = pd.to_datetime(df['ANO'].astype(str) + '-' + df['MÊS'].astype(str))
        df.to_csv('data/relatorio.csv', index=False)
        return df

    df = data_load()
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


tabs1, tabs2, tabs3 = st.tabs(['DISCENTES', 'ATIVIDADES', 'GERAL'])


with tabs1: # DISCENTES
    df_tabs1 = df.copy()
    df_tabs1 = df_tabs1.groupby(['ALUNO']).agg({'HORAS': 'sum'}).sort_values(by='HORAS', ascending=False).reset_index()

    col1, col2 = st.columns(2)

    with col1:
        st.metric('TOTAL DE HORAS', f'{df_tabs1["HORAS"].sum():.0f}')
    with col2:
        # Total de discentes
        st.metric('TOTAL DE DISCENTES', f'{df_tabs1["ALUNO"].nunique()}')
 

    # Definir o valor máximo de horas
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
    st.plotly_chart(fig, use_container_width=True)



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
    fig.add_trace(go.Bar(x=df_tabs2['ATIVIDADE'], y=df_tabs2['HORAS'], marker=dict(color=df_tabs2['HORAS'], colorscale='Blues')))
    fig.update_layout(title=f'Total de horas por Atividade')
    st.plotly_chart(fig, use_container_width=True)
