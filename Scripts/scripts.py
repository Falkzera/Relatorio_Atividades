import pandas as pd
import streamlit as st
import io

def download_excel_button(df, filename="dados.xlsx", sheet_name="Sheet1", button_label="Baixar tabela em Excel"):
    """
    Função para criar um botão de download para um DataFrame Pandas no formato Excel.

    Parâmetros:
    - df (pd.DataFrame): DataFrame a ser salvo no Excel.
    - filename (str): Nome do arquivo para download (padrão: "dados.xlsx").
    - sheet_name (str): Nome da aba no Excel (padrão: "Sheet1").
    - button_label (str): Texto exibido no botão de download (padrão: "Baixar tabela em Excel").
    """

    # Criar um buffer de memória para salvar o arquivo temporário
    output = io.BytesIO()

    # Criar o arquivo Excel
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)

    # Retornar ao início do arquivo para permitir a leitura
    output.seek(0)

    # Criar botão de download no Streamlit
    st.download_button(
        label=button_label,
        data=output,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
