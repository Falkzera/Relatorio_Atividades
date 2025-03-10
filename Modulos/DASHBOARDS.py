import streamlit as st
import pandas as pd
import numpy as np
import Scripts.utils as utils
import streamlit as st
# importar make_subplots para criar subplots
from plotly.subplots import make_subplots
import plotly.express as px
import plotly.graph_objects as go
from Scripts.google_drive_utils import (authenticate_service_account, read_parquet_files_from_drive)

def DASHBOARDS():

    with st.container(): # API GOOGLE DRIVE
        FOLDER_ID = "1d0KqEyocTO1lbnWS1u7hooSVJgv5Fz6Q"  # ID da pasta no Google Drive
        service = authenticate_service_account() 
        df = read_parquet_files_from_drive(service, FOLDER_ID)

        if df.empty:
            st.error("Nenhum arquivo .parquet encontrado na pasta do Google Drive.")
            st.stop()
        else:
            pass

    with st.container(): # Filtro de Aluno, Mês e Ano
        col1, col2, col3 = st.columns(3)

        with col1:
            filtro_aluno = st.selectbox("Aluno", ["TODOS"] + sorted(df["ALUNO"].unique()), index=0)
        with col2:
            anos_disponiveis = df[df["ALUNO"] == filtro_aluno]["ANO"].unique() if filtro_aluno != "TODOS" else df["ANO"].unique()
            filtro_ano = st.selectbox("Ano", ["TODOS"] + sorted(anos_disponiveis), index=0)
        with col3:
            if filtro_ano != "TODOS" and filtro_aluno != "TODOS":
                meses_disponiveis = df[(df["ANO"] == filtro_ano) & (df["ALUNO"] == filtro_aluno)]["MES"].unique()
            elif filtro_ano != "TODOS":
                meses_disponiveis = df[df["ANO"] == filtro_ano]["MES"].unique()
            elif filtro_aluno != "TODOS":
                meses_disponiveis = df[df["ALUNO"] == filtro_aluno]["MES"].unique()
            else:
                meses_disponiveis = df["MES"].unique()
            filtro_mes = st.selectbox("Mês", ["TODOS"] + sorted(meses_disponiveis), index=0)

        df_filtrado = df.copy()

        if filtro_aluno != "TODOS":
            df_filtrado = df_filtrado[df_filtrado["ALUNO"] == filtro_aluno]
        if filtro_mes != "TODOS":
            df_filtrado = df_filtrado[df_filtrado["MES"] == filtro_mes]
        if filtro_ano != "TODOS":
            df_filtrado = df_filtrado[df_filtrado["ANO"] == filtro_ano]

        df_filtrado["DATA"] = pd.to_datetime(df_filtrado["ANO"].astype(str) + "-" + df_filtrado["MES"].astype(str) + "-01")
        df_filtrado = df_filtrado.sort_values("DATA")

        # Agrupar por DATA
        df_filtrado_data = df_filtrado.groupby("DATA").sum().reset_index()


    with st.container(): # metrics
        st.write('---')

        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="Total de atividades realizadas", value=len(df_filtrado), border=True)
        with col2:
            st.metric(label="Total de horas realizadas", value=df_filtrado['HORAS'].sum(), border=True)
        
    # Lógica para as três atividades com maior total de horas:
    # Agrupa por ATIVIDADE e soma as HORAS
    top_atividades = (
        df_filtrado.groupby("ATIVIDADE")["HORAS"]
        .sum()
        .reset_index()
        .sort_values("HORAS", ascending=False)
        .head(3)
    )

    st.subheader("Top 3 atividades com maior número de horas")
    cols = st.columns(3)  # Cria três colunas para exibir os metrics dos top 3

    # Itera pelas atividades e coloca cada uma em uma coluna
    for i, row in enumerate(top_atividades.itertuples()):
        with cols[i]:
            st.metric(label=row.ATIVIDADE, value=row.HORAS, border=True)

    with st.container(): # Gráfico de horas
        st.write("---")
        st.subheader(f"*- Detalhamento por atividades*")
        tab1, tab2 = st.tabs(["Horas Totais", "Horas por Atividade"])

        with tab1: # HORAS TOTAIS
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df_filtrado_data["DATA"], y=df_filtrado_data["HORAS"], marker_color ='#0b4757', text=df_filtrado_data["HORAS"], textposition='inside', name=f'Horas'))
            fig.add_trace(go.Scatter(x=df_filtrado_data["DATA"], y=df_filtrado_data["HORAS"], name=''))
            total_hours = df_filtrado_data["HORAS"].sum()
            fig.update_layout(title=f' Quantidade de horas ao longo do tempo - (acumulado por atividades) - {total_hours} horas', title_font=dict(size=20), legend=dict(font=dict(size=15), orientation='h', x=0.5, xanchor='center', y=-0.3), xaxis=dict(tickfont=dict(size=15)), yaxis=dict(tickfont=dict(size=15)))
            fig.update_xaxes(dtick='M1', tickformat='%b %Y')
            fig.update_layout(autosize=False, width=1000, height=500)
            st.plotly_chart(fig, use_container_width=True)


        with tab2: # HORAS POR ATIVIDADES

            atividade_selecionada = st.selectbox("Selecione a atividade", ["TODOS"] + list(df_filtrado["ATIVIDADE"].unique()))

            if atividade_selecionada == "TODOS": # PARA TODAS AS ATIVIDADES

                tabs1, tabs2 = st.tabs(["Gráfico de Barras", "Heatmap"]) # DOIS GRÁFICOS

                with tabs1: # GRÁFICO DE LINHAS

                    df_filtrado['DATA_MES'] = df_filtrado['DATA'].dt.to_period('M')
                    atividades_comissao_interna = df_filtrado['ATIVIDADE'].value_counts()
                    atividades_comissao_interna = atividades_comissao_interna[atividades_comissao_interna > 5].index.tolist()
                    atividades_comissao_interna = [atividade for atividade in atividades_comissao_interna if atividade.startswith("Atividades Comissão")]
                    atividades_selecionadas = st.multiselect("Selecione as atividades", options=sorted(df_filtrado['ATIVIDADE'].unique()), default=atividades_comissao_interna)
                    df_filtrado_selecionadas = df_filtrado[df_filtrado['ATIVIDADE'].isin(atividades_selecionadas)]
                    line_data_selecionadas = df_filtrado_selecionadas.pivot_table(index='DATA_MES', columns='ATIVIDADE', values='HORAS', aggfunc='sum', fill_value=0)
                    line_data_selecionadas = line_data_selecionadas.sort_index()
                    line_data_selecionadas.index = line_data_selecionadas.index.astype(str)
                    
                    fig_selecionadas = go.Figure()
                    stackgroup = 'one' if st.radio("Ativar Stackgroup", ("Sim", "Não"), index=0, horizontal=True) == "Sim" else None
                    for atividade in line_data_selecionadas.columns:
                        y_values = line_data_selecionadas[atividade].replace(0, np.nan)  # Substitui 0 por NaN para interromper a linha
                        fig_selecionadas.add_trace(go.Scatter(x=line_data_selecionadas.index, y=y_values, mode='lines', name=atividade, stackgroup=stackgroup))
                    
                    # Define o layout
                    fig_selecionadas.update_layout(
                        title=f'Quantidade de horas ao longo do tempo por atividades selecionadas - {total_hours} horas',
                        title_font=dict(size=20),
                        xaxis=dict(title=None, tickfont=dict(size=15)),
                        yaxis=dict(title=None, tickfont=dict(size=15)),
                        legend=dict(font=dict(size=15), orientation='h', x=0.5, xanchor='center', y=-0.3),
                        autosize=False,
                        width=1000,
                        height=500
                    )
                    
                    # Ajusta o formato do eixo x para exibir mês e ano
                    fig_selecionadas.update_xaxes(dtick='M1', tickformat='%b %Y', tickangle=90)
                    
                    # Renderiza o gráfico no Streamlit
                    st.plotly_chart(fig_selecionadas, use_container_width=True)











                with tabs2: # GRÁFICO DE HEATMAP
                    radio_value = st.radio("Alternar eixo Y e X", ("Sim", "Não"), index=0, horizontal=True)
                    df_filtrado['DATA_MES'] = df_filtrado['DATA'].dt.to_period('M')

                    if radio_value == "Sim": # INVERTER EIXO
                        heatmap_data = df_filtrado.pivot_table(index='DATA_MES', columns="ATIVIDADE", values="HORAS", aggfunc="sum", fill_value=0)
                        x_axis, y_axis = heatmap_data.columns, heatmap_data.index.astype(str)
                    else: # NÃO INVERTER EIXO	
                        heatmap_data = df_filtrado.pivot_table(index='ATIVIDADE', columns="DATA_MES", values="HORAS", aggfunc="sum", fill_value=0)
                        x_axis, y_axis = heatmap_data.columns.astype(str), heatmap_data.index

                    fig = go.Figure(data=go.Heatmap(z=heatmap_data.values, x=x_axis, y=y_axis, colorscale='Blues'))
                    fig.update_layout(title=f'Quantidade de horas ao longo do tempo por atividades - {total_hours} horas', title_font=dict(size=20), xaxis=dict(title=None, tickfont=dict(size=15)), yaxis=dict(title=None, tickfont=dict(size=15)), legend=dict(font=dict(size=15), orientation='h', x=0.5, xanchor='center', y=-0.3))
                    fig.update_xaxes(dtick='M1', tickformat='%b %Y', tickangle=90)
                    fig.update_yaxes(dtick='M1', tickformat='%b %Y')
                    fig.update_layout(autosize=False, width=1000, height=1000)
                    st.plotly_chart(fig, use_container_width=True)

            else: # PARA UMA ATIVIDADE ESPECÍFICA
                df_atividade = df_filtrado[df_filtrado["ATIVIDADE"] == atividade_selecionada]
                total_horas_atividade = df_atividade["HORAS"].sum()
                st.markdown(f"<h2 style='text-align: center; font-size: 28px;'>Quantidade de horas ao longo do tempo - {atividade_selecionada.title()} - {total_horas_atividade} horas totais</h2>", unsafe_allow_html=True)
                tabs1, tabs2 = st.columns(2)

                if len(df_atividade) >= 1: # SE A ATIVIDADE TIVER REGISTROS

                    with tabs1:
                        # df_atividade tem que agrupar por aluno

                        df_atividade_agg = df_atividade.groupby("DATA").sum().reset_index()

                        fig = go.Figure()
                        fig.add_trace(go.Bar(x=df_atividade_agg["DATA"], y=df_atividade_agg["HORAS"], marker_color='#0b4757', text=df_atividade_agg["HORAS"], textposition='inside', name='Horas'))
                        fig.add_trace(go.Scatter(x=df_atividade_agg["DATA"], y=df_atividade_agg["HORAS"], mode='lines+markers', name=''))
                        fig.update_layout(title=f'', title_font=dict(size=20), legend=dict(font=dict(size=15), orientation='h', x=0.5, xanchor='center', y=-0.3), xaxis=dict(tickfont=dict(size=15)), yaxis=dict(tickfont=dict(size=15)))
                        fig.update_xaxes(dtick='M1', tickformat='%b %Y')
                        st.plotly_chart(fig, use_container_width=True)

                    with tabs2:
                        df_atividade_agg = df_atividade.groupby("DATA").sum().reset_index()

                        fig = go.Figure()
                        fig.add_trace(go.Scatterpolar(r=df_atividade_agg["HORAS"], theta=df_atividade_agg["DATA"].dt.strftime('%b %Y'), fill='toself', name=atividade_selecionada))
                        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, df_filtrado["HORAS"].max()])), title=f'', title_font=dict(size=20), legend=dict(font=dict(size=15), orientation='h', x=0.5, xanchor='center', y=-0.3))
                        st.plotly_chart(fig, use_container_width=True)

                else: # SE A ATIVIDADE NÃO TIVER REGISTROS
                    st.error(f"Não há registros para a atividade {atividade_selecionada}.")

    with st.container(): # Dataframe
        st.write("---")

        df_filtrado = df_filtrado.sort_values(by=["ATIVIDADE", "DATA"]); df_grouped = df_filtrado.groupby("ATIVIDADE").agg(TOTAL_HORAS=("HORAS", "sum"), FREQUENCIA=("HORAS", "count"), HORAS_LIST=("HORAS", lambda x: list(x))).reset_index()

        total_horas_geral = df_grouped["TOTAL_HORAS"].sum()
        df_grouped["PERCENTUAL"] = df_grouped["TOTAL_HORAS"].apply(lambda x: f"{(x / total_horas_geral * 100):.2f}".replace('.', ',') + "%")
        df_grouped = df_grouped.sort_values(by="TOTAL_HORAS", ascending=False)
        df_grouped = df_grouped[["ATIVIDADE", "TOTAL_HORAS", "PERCENTUAL", "FREQUENCIA", "HORAS_LIST"]]
        st.subheader("*- Horas detalhadas por atividade (Rankeadas por horas)*")

        col_width_total = len("TOTAL HORAS") * -26
        col_width_percent = len("PERCENTUAL") * -29
        col_width_freq = len("FREQUENCIA") * -30

        st.data_editor(df_grouped, hide_index=True, column_config={"ATIVIDADE": st.column_config.TextColumn("ATIVIDADE", width=len("ATIVIDADE") * 8), "TOTAL_HORAS": st.column_config.NumberColumn("TOTAL HORAS", width=col_width_total), "PERCENTUAL": st.column_config.TextColumn("PERCENTUAL", width=col_width_percent), "FREQUENCIA": st.column_config.NumberColumn("FREQUENCIA", width=col_width_freq), "HORAS_LIST": st.column_config.LineChartColumn("GRÁFICO", help="Mini-gráfico com as horas registradas por data para cada atividade", width="small", y_min=0)})
















        # if filtro_aluno == "TODOS":

        st.write("---")
        st.subheader(f"*- Detalhamento por alunos*")
        tab1, tab2 = st.tabs(["Alunos", "Atividades"])

        with tab1: # HORAS TOTAIS

            df_aluno_agg = df_filtrado.groupby("ALUNO")["HORAS"].sum().reset_index()
            df_aluno_agg = df_aluno_agg.sort_values(by="HORAS", ascending=False)  # Ordenar em ordem crescente
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df_aluno_agg["ALUNO"], y=df_aluno_agg["HORAS"], marker_color='#0b4757', text=df_aluno_agg["HORAS"], textposition='inside', name='Horas'))
            fig.add_trace(go.Scatter(x=df_aluno_agg["ALUNO"], y=df_aluno_agg["HORAS"], name=''))
            total_hours = df_aluno_agg["HORAS"].sum()
            fig.update_layout(title=f'Quantidade de horas por aluno', title_font=dict(size=20), xaxis=dict(title=None, tickfont=dict(size=15)), yaxis=dict(title=None, tickfont=dict(size=15)))
            fig.update_layout(autosize=False, width=1000, height=500)
            # fig.update_xaxes(dtick='M1', tickformat='%b %Y', tickangle=90)
            st.plotly_chart(fig, use_container_width=True)

        with tab2:

            df_atividade_agg = df_filtrado.groupby("ATIVIDADE")["HORAS"].sum().reset_index()
            df_atividade_agg = df_atividade_agg.sort_values(by="HORAS", ascending=False)  # Ordenar em ordem crescente
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df_atividade_agg["ATIVIDADE"], y=df_atividade_agg["HORAS"], marker_color='#0b4757', text=df_atividade_agg["HORAS"], textposition='inside', name='Horas'))
            fig.add_trace(go.Scatter(x=df_atividade_agg["ATIVIDADE"], y=df_atividade_agg["HORAS"], name=''))
            total_hours = df_atividade_agg["HORAS"].sum()
            fig.update_layout(title=f'Quantidade de horas por atividade', title_font=dict(size=20), xaxis=dict(title=None, tickfont=dict(size=15)), yaxis=dict(title=None, tickfont=dict(size=15)))
            fig.update_layout(autosize=False, width=1000, height=800)
            fig.update_xaxes(dtick='M1', tickformat='%b %Y', tickangle=90)
            st.plotly_chart(fig, use_container_width=True)












    utils.atualizar_dados()