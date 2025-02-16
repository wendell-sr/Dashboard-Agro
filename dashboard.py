import streamlit as st
import pandas as pd
import json
import altair as alt
import os
import locale

st.set_page_config(
    page_title="Título do Dashboard",
    page_icon=":chart_with_upwards_trend:",
    layout="wide"
)
def formatar_moeda(valor):
    """Formata o valor numérico para o padrão monetário brasileiro."""
    try:
        return locale.currency(valor, grouping=True)
    except Exception:
        valor_formatado = f'{valor:,.2f}'  # ex: 1,234.56
        valor_formatado = valor_formatado.replace(',', 'v').replace('.', ',').replace('v', '.')
        return f'R$ {valor_formatado}'

def obter_configuracoes_tema():
    """Retorna as configurações do tema a partir do config.toml."""
    return {
        "primary_color": st.get_option('theme.primaryColor'),
        "background_color": st.get_option('theme.backgroundColor'),
        "secondary_background_color": st.get_option('theme.secondaryBackgroundColor'),
        "text_color": st.get_option('theme.textColor'),
        "font": st.get_option('theme.font')
    }

@st.cache_data
def carregar_dados(caminho_dados="dados.json"):
    """Carrega e retorna os dados do arquivo JSON."""
    if not os.path.exists(caminho_dados):
        st.error(f"Arquivo {caminho_dados} não encontrado.")
        return {}
    with open(caminho_dados, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            st.error("Erro ao decodificar o arquivo JSON.")
            return {}

class Dashboard:
    def __init__(self, dados):
        self.dados = dados
        self.contratos = pd.DataFrame()
        self.df_filtrado = pd.DataFrame()
        # Para armazenar os anos selecionados e adaptarmos o gráfico
        self.ano_selecionado = None

    def preparar_dados(self):
        """Normaliza os dados e converte colunas de data para formato datetime e string legível."""
        if self.dados and "contratos" in self.dados:
            self.contratos = pd.json_normalize(self.dados["contratos"])
            # Converter para datetime e criar colunas formatadas no padrão DD-MM-YYYY
            if "dataContratacao" in self.contratos.columns:
                self.contratos["dataContratacao"] = pd.to_datetime(
                    self.contratos["dataContratacao"], errors='coerce'
                )
                self.contratos["dataContratacaoFormatada"] = self.contratos["dataContratacao"].dt.strftime("%d-%m-%Y")
            if "vencimentoContrato" in self.contratos.columns:
                self.contratos["vencimentoContrato"] = pd.to_datetime(
                    self.contratos["vencimentoContrato"], errors='coerce'
                )
                self.contratos["vencimentoContratoFormatada"] = self.contratos["vencimentoContrato"].dt.strftime("%d-%m-%Y")

    def renderizar_filtros(self):
        """Renderiza os filtros na barra lateral utilizando o tema."""
        tema = obter_configuracoes_tema()
        st.sidebar.header("Filtros", help="Configurações de filtros")
        
        # Filtro Cliente (geralmente único)
        cliente = self.dados.get("cliente", {}).get("nomeEmpresa", "Cliente não definido")
        _ = st.sidebar.selectbox("Cliente", options=[cliente])
        
        # Filtro Sócio
        socios = sorted(self.contratos["socioResponsavel"].unique())
        filtro_socio = st.sidebar.multiselect("Sócio", options=socios, default=socios)
        
        # Filtro Banco (se existir)
        if "banco" in self.contratos.columns:
            bancos = sorted(self.contratos["banco"].unique())
            filtro_banco = st.sidebar.multiselect("Banco", options=bancos, default=bancos)
        else:
            filtro_banco = None
        
        # Filtro Contrato
        contratos = sorted(self.contratos["tipoContrato"].unique())
        filtro_contrato = st.sidebar.multiselect("Contrato", options=contratos, default=contratos)
        
        # Filtro Ano
        if "dataContratacao" in self.contratos.columns:
            anos = sorted(self.contratos["dataContratacao"].dropna().dt.year.unique())
            filtro_ano = st.sidebar.multiselect("Ano", options=anos, default=anos)
        else:
            filtro_ano = None
        
        # Armazenar o filtro de ano para uso no gráfico
        self.ano_selecionado = filtro_ano
        
        # Condições para filtragem dos contratos
        cond = (self.contratos["socioResponsavel"].isin(filtro_socio)) & \
               (self.contratos["tipoContrato"].isin(filtro_contrato))
        if filtro_banco is not None:
            cond &= self.contratos["banco"].isin(filtro_banco)
        if filtro_ano is not None:
            cond &= self.contratos["dataContratacao"].dt.year.isin(filtro_ano)
            
        self.df_filtrado = self.contratos[cond]

    def renderizar_tabela_consolidada(self):
        """Exibe a tabela consolidada com as configurações do tema."""
        tema = obter_configuracoes_tema()
        consolidado = self.df_filtrado.groupby("socioResponsavel", as_index=False).agg(
            Quantidade_Contratos=('valorTotal', 'count'),
            Total_Divida=('valorTotal', 'sum')
        )
        consolidado.rename(columns={
            'socioResponsavel': 'Nome do Sócio',
            'Quantidade_Contratos': 'Qtd. Contratos',
            'Total_Divida': 'Valor Total da Dívida'
        }, inplace=True)
        consolidado["Valor Total da Dívida"] = consolidado["Valor Total da Dívida"].apply(formatar_moeda)
        st.subheader("Dívida Total - Cliente")
        st.dataframe(consolidado)

    def renderizar_resumo(self):
        """Exibe as métricas resumidas utilizando o tema."""
        total_divida = self.df_filtrado["valorTotal"].sum()
        st.subheader("Resumo")
        st.metric(label="Total da Dívida (R$)", value=formatar_moeda(total_divida))

    def renderizar_graficos(self):
        """Exibe os gráficos com valores como rótulos e com cores/fonte definidas no tema."""
        tema = obter_configuracoes_tema()
        # Gráfico 1: Dívida Total por Banco
        divida_por_banco = self.df_filtrado.groupby("banco", as_index=False)["valorTotal"].sum()
        graf_banco = alt.Chart(divida_por_banco).mark_bar(color=tema["primary_color"]).encode(
            x=alt.X('banco:N', title='Banco',
                    axis=alt.Axis(labelAngle=0,labelColor=tema["text_color"], titleColor=tema["text_color"],
                                  labelFont=tema["font"], titleFont=tema["font"])),
            y=alt.Y('valorTotal:Q',
                    axis=alt.Axis(grid=False, labels=False, ticks=False, title='Dívida Total (R$)',
                                  titleColor=tema["text_color"], titleFont=tema["font"]))
        )
        texto_banco = alt.Chart(divida_por_banco).mark_text(
            align='center',
            baseline='middle',
            dy=-10,
            color=tema["text_color"],
            font=tema["font"]
        ).encode(
            x=alt.X('banco:N'),
            y=alt.Y('valorTotal:Q'),
            text=alt.Text('valorTotal:Q', format=',.2f')
        )
        graf_banco_layer = alt.layer(graf_banco, texto_banco).properties(
            title=alt.TitleParams(text="Total de Dívida por Banco", color=tema["text_color"], font=tema["font"]),
            width=600
        )
        st.altair_chart(graf_banco_layer, use_container_width=True)

        # Gráfico 2: Valor Total de Parcelas
        if "dataContratacao" in self.df_filtrado.columns:
            df_temp = self.df_filtrado.copy()
            if self.ano_selecionado is not None and len(self.ano_selecionado) == 1:
                df_temp["Mes"] = df_temp["dataContratacao"].dt.month
                agrupado = df_temp.groupby("Mes", as_index=False)["valorTotal"].sum()
                meses_pt = {
                    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
                    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
                    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
                }
                agrupado["NomeMes"] = agrupado["Mes"].map(meses_pt)
                agrupado.sort_values("Mes", inplace=True)
                graf_parcelas_line = alt.Chart(agrupado).mark_line(point=True, color=tema["primary_color"]).encode(
                    x=alt.X('NomeMes:N', title='Mês', sort=list(meses_pt.values()),
                            axis=alt.Axis(labelColor=tema["text_color"], titleColor=tema["text_color"],
                                          labelFont=tema["font"], titleFont=tema["font"])),
                    y=alt.Y('valorTotal:Q',
                            axis=alt.Axis(labels=False, ticks=False, title='Valor Total (R$)',
                                          titleColor=tema["text_color"], titleFont=tema["font"]))
                )
                texto_parcelas = alt.Chart(agrupado).mark_text(
                    align='center',
                    baseline='bottom',
                    dy=-10,
                    color=tema["text_color"],
                    font=tema["font"]
                ).encode(
                    x=alt.X('NomeMes:N'),
                    y=alt.Y('valorTotal:Q'),
                    text=alt.Text('valorTotal:Q', format=',.2f')
                )
                graf_parcelas_layer = alt.layer(graf_parcelas_line, texto_parcelas).properties(
                    title=alt.TitleParams(text="Valor Total de Parcelas por Mês", color=tema["text_color"], font=tema["font"]),
                    width=600
                )
            else:
                df_temp["Ano"] = df_temp["dataContratacao"].dt.year.astype(int)
                agrupado = df_temp.groupby("Ano", as_index=False)["valorTotal"].sum()
                graf_parcelas_line = alt.Chart(agrupado).mark_line(point=True, color=tema["primary_color"]).encode(
                    x=alt.X(
                        'Ano:O', 
                        title='Ano',
                        axis=alt.Axis(
                            labelColor=tema["text_color"],
                            titleColor=tema["text_color"],
                            labelFont=tema["font"],
                            titleFont=tema["font"],
                            labelAngle=0,
                            grid=False
                        )
                    ),
                    y=alt.Y(
                        'valorTotal:Q',
                        axis=alt.Axis(
                            labels=False,
                            ticks=False,
                            title='Valor Total (R$)',
                            titleColor=tema["text_color"],
                            titleFont=tema["font"],
                            grid=False
                        )
                    )
                )
                texto_parcelas = alt.Chart(agrupado).mark_text(
                    align='center',
                    baseline='bottom',
                    dy=-10,
                    color=tema["text_color"],
                    font=tema["font"]
                ).encode(
                    x=alt.X('Ano:O'),
                    y=alt.Y('valorTotal:Q'),
                    text=alt.Text('valorTotal:Q', format=',.2f')
                )
                graf_parcelas_layer = alt.layer(graf_parcelas_line, texto_parcelas).properties(
                    title=alt.TitleParams(
                        text="Valor Total de Parcelas por Ano",
                        color=tema["text_color"],
                        font=tema["font"]
                    ),
                    width=600
                )
            st.altair_chart(graf_parcelas_layer, use_container_width=True)
        else:
            st.info("Coluna 'dataContratacao' não disponível para gerar o gráfico de parcelas.")

    def renderizar_tabela_detalhada(self):
        """Exibe a tabela detalhada dos contratos filtrados com as colunas reordenadas."""
        st.subheader("Tabela de Contratos Detalhada")
        df_detalhada = self.df_filtrado.copy()
        
        # Calcular a duração em anos, se as datas estiverem disponíveis
        if "dataContratacao" in df_detalhada.columns and "vencimentoContrato" in df_detalhada.columns:
            df_detalhada["Duração em Anos"] = (
                (df_detalhada["vencimentoContrato"] - df_detalhada["dataContratacao"]).dt.days / 365
            ).round(1)
        
        # Garantir que a coluna de número do contrato exista; caso não, criar com valor padrão
        if "numeroContrato" not in df_detalhada.columns:
            df_detalhada["numeroContrato"] = "Não definido"
        
        # Formatar o valor total para o padrão de moeda real
        if "valorTotal" in df_detalhada.columns:
            df_detalhada["valorTotal"] = df_detalhada["valorTotal"].apply(formatar_moeda)
        
        # Reordenar e renomear as colunas conforme desejado
        colunas_desejadas = [
            "socioResponsavel", 
            "banco", 
            "numeroContrato", 
            "dataContratacaoFormatada", 
            "vencimentoContratoFormatada",  # nome correto
            "valorTotal", 
            "Duração em Anos"
        ]
        df_detalhada = df_detalhada[colunas_desejadas]
        df_detalhada = df_detalhada.rename(columns={
            "socioResponsavel": "Sócio",
            "banco": "Banco",
            "numeroContrato": "Número do Contrato",
            "dataContratacaoFormatada": "Data de Contratação",
            "vencimentoContratoFormatada": "Vencimento do Contrato",
            "valorTotal": "Valor Total"
        })
        
        st.dataframe(df_detalhada)

    def renderizar_dashboard(self):
        """Renderiza o dashboard completo."""
        st.markdown(
            "<h1 style='text-align: center;'>Gestão de Endividamento</h1>",
            unsafe_allow_html=True
        )
        self.renderizar_filtros()

        if self.df_filtrado.empty:
            st.warning("Nenhum dado encontrado com os filtros selecionados.")
            return

        # Primeira linha: Resumo e Consolidado lado a lado
        col1, col2 = st.columns(2)
        with col1:
            self.renderizar_resumo()
        with col2:
            self.renderizar_tabela_consolidada()

        # Em seguida, gráficos
        self.renderizar_graficos()

        # Por fim, a tabela detalhada
        self.renderizar_tabela_detalhada()

if __name__ == "__main__":
    dados = carregar_dados()
    if dados and "contratos" in dados:
        dashboard = Dashboard(dados)
        dashboard.preparar_dados()
        dashboard.renderizar_dashboard()
    else:
        st.error("Não foi possível carregar os dados dos contratos.")
