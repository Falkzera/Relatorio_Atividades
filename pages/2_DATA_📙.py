import time 
import pandas as pd
import streamlit as st
import sidrapy # type: ignore
import plotly.graph_objects as go
from datetime import datetime
from Scripts.scripts import download_excel_button
from Models.marca import display_sidebar, display_header 

ano_atual = datetime.now().year

display_sidebar()

display_header("Base de Dados - PETECO 📊")

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("Você precisa fazer login para acessar esta página 🔐.")
    st.stop()

else:

    def formatar_valor(valor):
                    if valor >= 1_000_000_000:
                        valor_formatado = f"{valor / 1_000_000_000:.3f}".replace('.', ',')
                        return f"{valor_formatado} bilhões"
                    elif valor >= 1_000_000:
                        valor_formatado = f"{valor / 1_000_000:.3f}".replace('.', ',')
                        return f"{valor_formatado} milhões"
                    else:
                        valor_formatado = f"{valor / 1_000:.3f}".replace('.', ',')
                        return f"{valor_formatado} mil"
                    
    with st.container():
            # Estados
            estados = st.multiselect('Selecione os estados', 
                                    ['Rondônia', 'Acre', 'Amazonas', 'Roraima', 'Pará', 'Amapá', 'Tocantins', 
                                    'Maranhão', 'Piauí', 'Ceará', 'Rio Grande do Norte', 'Paraíba', 'Pernambuco', 
                                    'Alagoas', 'Sergipe', 'Bahia', 'Minas Gerais', 'Espírito Santo', 'Rio de Janeiro', 
                                    'São Paulo', 'Paraná', 'Santa Catarina', 'Rio Grande do Sul', 'Mato Grosso do Sul', 
                                    'Mato Grosso', 'Goiás', 'Distrito Federal'], 
                                    ['Alagoas', ])
            # Códigos IBGE
            ibge_codes = {
                        'Rondônia': '11', 'Acre': '12', 'Amazonas': '13', 'Roraima': '14', 'Pará': '15', 'Amapá': '16', 
                        'Tocantins': '17', 'Maranhão': '21', 'Piauí': '22', 'Ceará': '23', 'Rio Grande do Norte': '24', 
                        'Paraíba': '25', 'Pernambuco': '26', 'Alagoas': '27', 'Sergipe': '28', 'Bahia': '29', 
                        'Minas Gerais': '31', 'Espírito Santo': '32', 'Rio de Janeiro': '33', 'São Paulo': '35', 
                        'Paraná': '41', 'Santa Catarina': '42', 'Rio Grande do Sul': '43', 'Mato Grosso do Sul': '50', 
                        'Mato Grosso': '51', 'Goiás': '52', 'Distrito Federal': '53'
                    }
            selected_codes = [ibge_codes[estado] for estado in estados]

    with st.container(): # Seleção Período
        def boxes():
            anos_disponiveis = [str(ano) for ano in range(ano_atual, ano_atual - 15, -1)]
            col1, col2 = st.columns(2)
            periodo_ano = col1.multiselect('Selecione o ano de consulta', anos_disponiveis)
            periodo_tri = col2.multiselect('Selecione o trimestre de consulta', ['1° Trimestre', '2° Trimestre', '3° Trimestre', '4° Trimestre'])
            periodo_combinado  = [ano + '0' +tri for ano in periodo_ano for tri in [item.split('°')[0] for item in periodo_tri]]
            # como sortear os periodos?
            periodo_combinado_ordenado = sorted(periodo_combinado, reverse=True)
            periodo = ','.join(periodo_combinado_ordenado)
            return periodo

    selecione_tabela = st.selectbox('Selecione a tabela de consulta:', 
                        ('Pesquisa Trimestral do Abate de Animais (1092)', 'Pesquisa Trimestral do Leite (1093)'))


    if selecione_tabela == 'Pesquisa Trimestral do Abate de Animais (1092)':
            
            st.header(':blue[Pesquisa Trimestral do Abate de Animais]')
            table_code = '1092'
            variable = '284'
            nome_variavel = 'abates'
            tipo_variavel = 'cabeças'

    elif selecione_tabela == 'Pesquisa Trimestral do Leite (1093)':
            
            st.header(':blue[Pesquisa Trimestral do Leite - Mil Litros]')
            table_code = '1086'
            variable = '283'
            nome_variavel = 'leite cru adquirido'
            tipo_variavel = 'litros'
            
    periodo = boxes()

    ibge_territorial_code = ','.join(selected_codes)
    periodos_selecionados = ','.join(periodo)
    data = sidrapy.get_table(table_code=table_code, # Pesquisa trimestral do abate de animais
                                territorial_level='3', # Selecionado por unidade de federação
                                ibge_territorial_code=ibge_territorial_code, # Unidades do nordeste
                                variable=variable, # Animais abatidos (cabeças)
                                period=periodo, # Todos os períodos        
                            )

    data.columns = data.iloc[0]
    df = data.iloc[1:, [6, 8, 4, 10]].copy()
    df['DATA'] = pd.to_datetime(df['Trimestre'].str.extract(r'(\d{4})')[0] + '-' + df['Trimestre'].str.extract(r'(\d{1})')[0])
    df['Valor'] = df['Valor'].replace(['X', '...'], pd.NA)
    df = df.dropna(subset=['Valor'])
    df['Valor'] = df['Valor'].astype(float)
    df = df.rename(columns={'Unidade da Federação': 'UF', 'Valor': 'VALOR'})[['DATA', 'UF', 'VALOR']]

    tamanho_df = len(df)

    df['ANO'] = df['DATA'].dt.year
    df['MES'] = df['DATA'].dt.month

    anos = sorted(df['ANO'].unique())
    anos_continuos = all(anos[i] + 1 == anos[i + 1] for i in range(len(anos) - 1))
    meses_validos = True
    for i, ano in enumerate(anos):
        meses = sorted(df[df['ANO'] == ano]['MES'].unique())
        if i < len(anos) - 1: 
            if meses != [1, 2, 3, 4]:
                meses_validos = False
                break
        else:  
            if meses != list(range(1, max(meses) + 1)):  
                meses_validos = False
                break
    if anos_continuos and meses_validos:
        continuidade = 'contínuo'
    else:
        continuidade = 'não contínuo'

    with st.expander(f"Base de Dados: {selecione_tabela}", expanded=False):
                    st.table(df)
                    download_excel_button(df, filename="Download_Serie.xlsx", sheet_name="UF_Dados")

    st.header(':orange[Sugestão de Texto]')

    with st.container(): # Botão para gerar Dados
        if st.button('Gerar Dados'):

            with st.spinner('Processando...'):  
                progress_bar = st.progress(0)  
                
                for percent_complete in range(1, 101):  
                    time.sleep(0.02)  
                    progress_bar.progress(percent_complete)

            with st.container(): # 1 - DADOS PARA ALL PERIODO!	

                st.markdown(f"<span style='font-size: 22px;'> \
                            Segundo o IBGE, de acordo com o período analisado, que de modo **{continuidade}**, se inicia no **{df[df['DATA'].dt.year == df['DATA'].dt.year.min()]['DATA'].dt.month.min():01d}° trimestre de {df['DATA'].dt.year.min():04d}** \
                            e finaliza no **{df[df['DATA'].dt.year == df['DATA'].dt.year.max()]['DATA'].dt.month.max():01d}° trimestre de {df['DATA'].dt.year.max():04d}**, revela que a quantidade de **{nome_variavel}** \
                            para {'os Estados: ' if df['UF'].nunique() != 1 else 'o Estado'} {', '.join(df['UF'].unique()[:-1]) + ' e ' + df['UF'].unique()[-1] if len(df['UF'].unique()) > 1 else df['UF'].unique()[0]} foi de **{formatar_valor(df['VALOR'].sum())}** de **{tipo_variavel}** \
                            {', representando para os trimestres disponíveis uma média de ' + str(formatar_valor(df['VALOR'].mean())) +' '+ f'{tipo_variavel}.' if tamanho_df >= 2 else '.'} \
                            {'Ao analisar a produção de cada Estado e a sua participação percentual no valor geral, podemos visualizar que: ' if df['UF'].nunique() != 1 else ''} \
                            </span>", unsafe_allow_html=True)

                df_uf_sorted = (df.groupby('UF', as_index=False)['VALOR'].sum().sort_values(by='VALOR', ascending=False).assign(PERCENTUAL=lambda x: x['VALOR'] / x['VALOR'].sum() * 100).reset_index(drop=True).pipe(lambda df: df.set_index(pd.RangeIndex(1, len(df) + 1))).assign(VALOR=lambda x: x['VALOR'].map(lambda v: f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")), PERCENTUAL=lambda x: x['PERCENTUAL'].map(lambda p: f"{p:.2f}%")))
                texto_continuo = ", ".join([f"**{uf}**: {valor} ({percentual})" for uf, valor, percentual in zip(df_uf_sorted['UF'], df_uf_sorted['VALOR'], df_uf_sorted['PERCENTUAL'])])
                if df['UF'].nunique() != 1:
                    st.markdown(f"<span style='font-size: 22px;'> A participação de cada Estado tem a seguinte composição: {texto_continuo}, \
                    criando-se um ranking de produção, o qual pode ser observado na tabela abaixo. </span>", unsafe_allow_html=True)

                    with st.expander("Ranking de produção por UF - Todo Período", expanded=False):
        
                        df_uf_sorted['PERCENTUAL'] =df_uf_sorted['PERCENTUAL'].replace('\.', ',', regex=True)
                        st.table(df_uf_sorted)

                        download_excel_button(df_uf_sorted, filename="Download.xlsx", sheet_name="UF_Dados")

            with st.container(): # 2 - DADOS PARA ULTIMO TRIMESTRE!

                if df['DATA'].nunique() != 1:
                
                    st.markdown(f"<span style='font-size: 22px;'> \
                                Com base nos dados mais recentes, **referente apenas ao {df[df['DATA'].dt.year == df['DATA'].dt.year.max()]['DATA'].dt.month.max():01d}° trimestre de {df['DATA'].dt.year.max():04d}** \
                                revela que a quantidade de **{nome_variavel}** \
                                para {'os Estados: ' if df['UF'].nunique() != 1 else 'o Estado'} {', '.join(df['UF'].unique()[:-1]) + ' e ' + df['UF'].unique()[-1] if len(df['UF'].unique()) > 1 else df['UF'].unique()[0]} \
                                foi de **{formatar_valor(df.loc[(df['DATA'].dt.year == df['DATA'].dt.year.max()) & (df['DATA'].dt.month == df.loc[df['DATA'].dt.year == df['DATA'].dt.year.max(), 'DATA'].dt.month.max()), 'VALOR'].sum())}**. \
                                </span>", unsafe_allow_html=True)

                    if len(df['UF'].unique()) != 1:
                        df_maxima_data = df.loc[
                            (df['DATA'].dt.year == df['DATA'].dt.year.max()) & 
                            (df['DATA'].dt.month == df.loc[df['DATA'].dt.year == df['DATA'].dt.year.max(), 'DATA'].dt.month.max())
                        ]

                        df_uf_sorted = (df_maxima_data.groupby('UF', as_index=False)['VALOR'].sum().sort_values(by='VALOR', ascending=False).assign(PERCENTUAL=lambda x: x['VALOR'] / x['VALOR'].sum() * 100).reset_index(drop=True).pipe(lambda df: df.set_index(pd.RangeIndex(1, len(df) + 1))).assign(VALOR=lambda x: x['VALOR'].map(lambda v: f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")), PERCENTUAL=lambda x: x['PERCENTUAL'].map(lambda p: f"{p:.2f}%")))
                        texto_continuo = ", ".join([f"**{uf}**: {valor} ({percentual})" for uf, valor, percentual in zip(df_uf_sorted['UF'], df_uf_sorted['VALOR'], df_uf_sorted['PERCENTUAL'])])

                        st.markdown(f"<span style='font-size: 22px;'> A participação no volume de cada Estado tem a seguinte composição: {texto_continuo}, \
                        criando-se um ranking de produção, o qual pode ser observado na tabela abaixo. </span>", unsafe_allow_html=True)

                        with st.container(): # Tabela de ranking de produção por UF no trimestre mais recente
                            
                            with st.expander("Ranking de produção por UF - Dados mais recentes", expanded=False):
                    
                                df_uf_sorted['PERCENTUAL'] =df_uf_sorted['PERCENTUAL'].replace('\.', ',', regex=True)
                                st.table(df_uf_sorted)
                                download_excel_button(df_uf_sorted, filename="Downloads_Ultimo_TRI.xlsx", sheet_name="UF_Ultimo_TRI")

                    with st.container(): # 3 - VARIAÇÃO DOS DADOS!!:
                    
                        ufs = df['UF'].unique()
                        df_variacao_final = pd.DataFrame(index=ufs)

                        for uf in ufs:
                            df_uf = df[df['UF'] == uf].copy() 
                            df_uf = df_uf.sort_values(by='DATA')  
                            
                            df_uf['ANO_MES'] = df_uf['DATA'].dt.strftime('%Y-%m')
                            variacoes = {}
                            for i in range(1, len(df_uf)):
                                col_name = f"{df_uf.iloc[i-1]['ANO_MES']} -> {df_uf.iloc[i]['ANO_MES']}"
                                variacoes[col_name] = ((df_uf.iloc[i]['VALOR'] / df_uf.iloc[i-1]['VALOR']) - 1) * 100

                            df_variacao_final.loc[uf, variacoes.keys()] = variacoes.values()

                        df_variacao_final = df_variacao_final.applymap(lambda x: f"{x:.2f}%" if pd.notnull(x) else "-")

                        st.markdown(f"<span style='font-size: 22px;'>  \
                                    Abaixo é possível a visualização referente a variação trimestral dos dados observados a partir do périodo selecionado, pelo Estado selecionado. \
                                    </span>", unsafe_allow_html=True)

                        with st.expander("📊 Tabela de Variação Mensal por Estado"):
                            col1, col2 = st.columns(2)
                            df_variacao_final = df_variacao_final.replace('\.', ',', regex=True)
                            st.table(df_variacao_final)

                            df_variacao_final = df_variacao_final.rename(columns={'index': 'UF'})
                            df_variacao_final_graph = df_variacao_final.copy()
                            df_variacao_final.reset_index(inplace=True)
                            download_excel_button(df_variacao_final, filename="Downloads_Variacao.xlsx", sheet_name="UF_Variacao")


                            with st.container(): # 4 - GRÁFICO DE VARIAÇÃO DOS DADOS!!:
                                df_variacao_final_graph = df_variacao_final_graph.replace('\,', '.', regex=True)
                                fig = go.Figure()    
                                for uf in ufs:
                                    fig.add_trace(go.Scatter(x=df_variacao_final_graph.columns, y=df_variacao_final_graph.loc[uf].tolist(), mode='lines+markers', name=uf))
                                st.plotly_chart(fig)
                    
