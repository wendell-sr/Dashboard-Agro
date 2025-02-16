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

def configure_locale():
    """Configura o locale para pt_BR ou exibe aviso se não for possível."""
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except:
        try:
            locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
        except Exception:
            st.warning("Configuração de localidade pt_BR não encontrada. Valores serão exibidos sem formatação regional.")

def format_currency(value):
    """Formata o valor numérico para o padrão monetário brasileiro."""
    try:
        return locale.currency(value, grouping=True)
    except Exception:
        valor_formatado = f'{value:,.2f}'  # ex: 1,234.56
        valor_formatado = valor_formatado.replace(',', 'v').replace('.', ',').replace('v', '.')
        return f'R$ {valor_formatado}'

def get_theme_settings():
    """Retorna as configurações do tema a partir do config.toml."""
    return {
        "primary_color": st.get_option('theme.primaryColor'),
        "background_color": st.get_option('theme.backgroundColor'),
        "secondary_background_color": st.get_option('theme.secondaryBackgroundColor'),
        "text_color": st.get_option('theme.textColor'),
        "font": st.get_option('theme.font')
    }

@st.cache_data
def load_data(data_path="dados.json"):
    """Carrega e retorna os dados do arquivo JSON."""
    if not os.path.exists(data_path):
        st.error(f"Arquivo {data_path} não encontrado.")
        return {}
    with open(data_path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            st.error("Erro ao decodificar o arquivo JSON.")
            return {}

class Dashboard:
    def __init__(self, data):
        self.data = data
        self.contracts = pd.DataFrame()
        self.df_filtrado = pd.DataFrame()
        # Para armazenar os anos selecionados e adaptarmos o gráfico
        self.selected_ano = None

    def prepare_data(self):
        """Normaliza os dados e converte colunas de data para formato datetime e string legível."""
        if self.data and "contratos" in self.data:
            self.contracts = pd.json_normalize(self.data["contratos"])
            # Converter para datetime e criar colunas formatadas no padrão DD-MM-YYYY
            if "dataContratacao" in self.contracts.columns:
                self.contracts["dataContratacao"] = pd.to_datetime(
                    self.contracts["dataContratacao"], errors='coerce'
                )
                self.contracts["dataContratacaoFormatada"] = self.contracts["dataContratacao"].dt.strftime("%d-%m-%Y")
            if "vencimentoContrato" in self.contracts.columns:
                self.contracts["vencimentoContrato"] = pd.to_datetime(
                    self.contracts["vencimentoContrato"], errors='coerce'
                )
                self.contracts["vencimentoContratoFormatado"] = self.contracts["vencimentoContrato"].dt.strftime("%d-%m-%Y")

    def render_filters(self):
        """Renderiza os filtros na barra lateral utilizando o tema."""
        theme = get_theme_settings()
        st.sidebar.header("Filtros", help="Configurações de filtros", )
        
        # Filtro Cliente (geralmente único)
        cliente = self.data.get("cliente", {}).get("nomeEmpresa", "Cliente não definido")
        _ = st.sidebar.selectbox("Cliente", options=[cliente])
        
        # Filtro Sócio
        socios = sorted(self.contracts["socioResponsavel"].unique())
        filtro_socio = st.sidebar.multiselect("Sócio", options=socios, default=socios)
        
        # Filtro Banco (se existir)
        if "banco" in self.contracts.columns:
            bancos = sorted(self.contracts["banco"].unique())
            filtro_banco = st.sidebar.multiselect("Banco", options=bancos, default=bancos)
        else:
            filtro_banco = None
        
        # Filtro Contrato
        contratos = sorted(self.contracts["tipoContrato"].unique())
        filtro_contrato = st.sidebar.multiselect("Contrato", options=contratos, default=contratos)
        
        # Filtro Ano
        if "dataContratacao" in self.contracts.columns:
            anos = sorted(self.contracts["dataContratacao"].dropna().dt.year.unique())
            filtro_ano = st.sidebar.multiselect("Ano", options=anos, default=anos)
        else:
            filtro_ano = None
        
        # Armazenar o filtro de ano para uso no gráfico
        self.selected_ano = filtro_ano
        
        # Condições para filtragem dos contratos
        cond = (self.contracts["socioResponsavel"].isin(filtro_socio)) & \
               (self.contracts["tipoContrato"].isin(filtro_contrato))
        if filtro_banco is not None:
            cond &= self.contracts["banco"].isin(filtro_banco)
        if filtro_ano is not None:
            cond &= self.contracts["dataContratacao"].dt.year.isin(filtro_ano)
            
        self.df_filtrado = self.contracts[cond]

    def render_consolidated_table(self):
        """Exibe a tabela consolidada com as configurações do tema."""
        theme = get_theme_settings()
        consolidado = self.df_filtrado.groupby("socioResponsavel", as_index=False).agg(
            Quantidade_Contratos=('valorTotal', 'count'),
            Total_Divida=('valorTotal', 'sum')
        )
        consolidado.rename(columns={
            'socioResponsavel': 'Nome do Sócio',
            'Quantidade_Contratos': 'Qtd. Contratos',
            'Total_Divida': 'Valor Total da Dívida'
        }, inplace=True)
        consolidado["Valor Total da Dívida"] = consolidado["Valor Total da Dívida"].apply(format_currency)
        st.subheader("Dívida Total - Cliente")
        st.dataframe(consolidado)

    def render_summary(self):
        """Exibe as métricas resumidas utilizando o tema."""
        total_divida = self.df_filtrado["valorTotal"].sum()
        st.subheader("Resumo")
        st.metric(label="Total da Dívida (R$)", value=format_currency(total_divida))

    def render_charts(self):
        """Exibe os gráficos com valores como rótulos e com cores/fonte definidas no tema."""
        theme = get_theme_settings()
        # Gráfico 1: Dívida Total por Banco
        divida_por_banco = self.df_filtrado.groupby("banco", as_index=False)["valorTotal"].sum()
        graf_banco = alt.Chart(divida_por_banco).mark_bar(color=theme["primary_color"]).encode(
            x=alt.X('banco:N', title='Banco',
                    axis=alt.Axis(labelColor=theme["text_color"], titleColor=theme["text_color"],
                                  labelFont=theme["font"], titleFont=theme["font"])),
            y=alt.Y('valorTotal:Q',
                    axis=alt.Axis(labels=False, ticks=False, title='Dívida Total (R$)',
                                  titleColor=theme["text_color"], titleFont=theme["font"]))
        )
        texto_banco = alt.Chart(divida_por_banco).mark_text(
            align='center',
            baseline='middle',
            dy=-10,
            color=theme["text_color"],
            font=theme["font"]
        ).encode(
            x=alt.X('banco:N'),
            y=alt.Y('valorTotal:Q'),
            text=alt.Text('valorTotal:Q', format=',.2f')
        )
        graf_banco_layer = alt.layer(graf_banco, texto_banco).properties(
            title=alt.TitleParams(text="Total de Dívida por Banco", color=theme["text_color"], font=theme["font"]),
            width=600
        )
        st.altair_chart(graf_banco_layer, use_container_width=True)

        # Gráfico 2: Valor Total de Parcelas
        if "dataContratacao" in self.df_filtrado.columns:
            df_temp = self.df_filtrado.copy()
            if self.selected_ano is not None and len(self.selected_ano) == 1:
                df_temp["Mes"] = df_temp["dataContratacao"].dt.month
                agrupado = df_temp.groupby("Mes", as_index=False)["valorTotal"].sum()
                months_pt = {
                    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
                    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
                    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
                }
                agrupado["MesNome"] = agrupado["Mes"].map(months_pt)
                agrupado.sort_values("Mes", inplace=True)
                graf_parcelas_line = alt.Chart(agrupado).mark_line(point=True, color=theme["primary_color"]).encode(
                    x=alt.X('MesNome:N', title='Mês', sort=list(months_pt.values()),
                            axis=alt.Axis(labelColor=theme["text_color"], titleColor=theme["text_color"],
                                          labelFont=theme["font"], titleFont=theme["font"])),
                    y=alt.Y('valorTotal:Q',
                            axis=alt.Axis(labels=False, ticks=False, title='Valor Total (R$)',
                                          titleColor=theme["text_color"], titleFont=theme["font"]))
                )
                texto_parcelas = alt.Chart(agrupado).mark_text(
                    align='center',
                    baseline='bottom',
                    dy=-10,
                    color=theme["text_color"],
                    font=theme["font"]
                ).encode(
                    x=alt.X('MesNome:N'),
                    y=alt.Y('valorTotal:Q'),
                    text=alt.Text('valorTotal:Q', format=',.2f')
                )
                graf_parcelas_layer = alt.layer(graf_parcelas_line, texto_parcelas).properties(
                    title=alt.TitleParams(text="Valor Total de Parcelas por Mês", color=theme["text_color"], font=theme["font"]),
                    width=600
                )
            else:
                df_temp["Ano"] = df_temp["dataContratacao"].dt.year.astype(int)
                agrupado = df_temp.groupby("Ano", as_index=False)["valorTotal"].sum()
                graf_parcelas_line = alt.Chart(agrupado).mark_line(point=True, color=theme["primary_color"]).encode(
                    x=alt.X('Ano:O', title='Ano',
                            axis=alt.Axis(labelColor=theme["text_color"], titleColor=theme["text_color"],
                                          labelFont=theme["font"], titleFont=theme["font"])),
                    y=alt.Y('valorTotal:Q',
                            axis=alt.Axis(labels=False, ticks=False, title='Valor Total (R$)',
                                          titleColor=theme["text_color"], titleFont=theme["font"]))
                )
                texto_parcelas = alt.Chart(agrupado).mark_text(
                    align='center',
                    baseline='bottom',
                    dy=-10,
                    color=theme["text_color"],
                    font=theme["font"]
                ).encode(
                    x=alt.X('Ano:O'),
                    y=alt.Y('valorTotal:Q'),
                    text=alt.Text('valorTotal:Q', format=',.2f')
                )
                graf_parcelas_layer = alt.layer(graf_parcelas_line, texto_parcelas).properties(
                    title=alt.TitleParams(text="Valor Total de Parcelas por Ano", color=theme["text_color"], font=theme["font"]),
                    width=600
                )
            st.altair_chart(graf_parcelas_layer, use_container_width=True)
        else:
            st.info("Coluna 'dataContratacao' não disponível para gerar o gráfico de parcelas.")

    def render_detail_table(self):
        """Exibe a tabela detalhada dos contratos filtrados."""
        st.subheader("Tabela de Contratos Detalhada")
        st.dataframe(self.df_filtrado)

    def render_dashboard(self):
        """Renderiza o dashboard completo."""
        st.title("Gestão de Endividamento")
        self.render_filters()

        if self.df_filtrado.empty:
            st.warning("Nenhum dado encontrado com os filtros selecionados.")
            return

        # Primeira linha: Resumo e Consolidado lado a lado
        col1, col2 = st.columns(2)
        with col1:
            self.render_summary()
        with col2:
            self.render_consolidated_table()

        # Em seguida, gráficos
        self.render_charts()

        # Por fim, a tabela detalhada
        self.render_detail_table()

if __name__ == "__main__":
    configure_locale()
    data = load_data()
    if data and "contratos" in data:
        dashboard = Dashboard(data)
        dashboard.prepare_data()
        dashboard.render_dashboard()
    else:
        st.error("Não foi possível carregar os dados dos contratos.")
