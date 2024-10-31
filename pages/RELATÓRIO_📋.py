import pandas as pd
import streamlit as st
import os

@st.cache_data(ttl=84600)
def data_load():
    pasta = 'relatorio/'
    df = pd.concat([pd.read_parquet(pasta + f) for f in os.listdir(pasta) if f.endswith('.parquet')])
    df['DATA'] = pd.to_datetime(df['DATA']) 
    df.to_csv('data/relatorio.csv', index=False)
    return df

df = data_load()


st.write(df.dtypes)
# Selecionar aluno
aluno = st.selectbox('Selecione o Aluno:', df['ALUNO'])
aluno_df = df[df['ALUNO'] == aluno].copy()
st.table(aluno_df)

# Ordenar o DataFrame com base na coluna "HORAS"
df = df.sort_values(by="HORAS", ascending=False)

# Adicionar uma coluna de ranking
df["Ranking"] = range(1, len(df) + 1)


# Definir o valor máximo de horas
max_horas = df["HORAS"].max()



# Exibir o DataFrame com a barra de progresso
st.data_editor(
    df,
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
)
