import streamlit as st
import pandas as pd
import numpy as np
import Scripts.utils as utils
import streamlit as st
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

    with st.container(): # Filtro de Aluno

        filtro_aluno = st.selectbox("Aluno", df["ALUNO"].unique())
        df_filtrado = df[(df["ALUNO"] == filtro_aluno)]


        # grafico das horas
        # criar coluna DATA a partir de ANO e MES
        df_filtrado["DATA"] = pd.to_datetime(df_filtrado["ANO"].astype(str) + "-" + df_filtrado["MES"].astype(str) + "-01")
        df_filtrado = df_filtrado.sort_values("DATA")
    
        st.data_editor(df_filtrado)

        # agrupar por DATA
        df_filtrado_data = df_filtrado.groupby("DATA").sum().reset_index()
    with st.container(): # Grafico de horas
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_filtrado_data["DATA"], y=df_filtrado_data["HORAS"], name="Horas", marker=dict(color="blue")))
        st.plotly_chart(fig)

    utils.atualizar_dados()