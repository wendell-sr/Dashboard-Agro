import streamlit as st
import pandas as pd
import json
import altair as alt
import os
import locale

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

    def prepare_data(self):
        """Normaliza os dados e converte colunas de data."""
        if self.data and "contratos" in self.data:
            self.contracts = pd.json_normalize(self.data["contratos"])
            if "dataContratacao" in self.contracts.columns:
                self.contracts["dataContratacao"] = pd.to_datetime(self.contracts["dataContratacao"], errors='coerce')
            if "vencimentoContrato" in self.contracts.columns:
                self.contracts["vencimentoContrato"] = pd.to_datetime(self.contracts["vencimentoContrato"], errors='coerce')

    def render_filters(self):
        """Renderiza os filtros na barra lateral e atualiza o DataFrame filtrado."""
        st.sidebar.header("Filtros")

        # Filtro Cliente: origem dos dados do JSON (normalmente único)
        cliente = self.data.get("cliente", {}).get("nomeEmpresa", "Cliente não definido")
        filtro_cliente = st.sidebar.selectbox("Cliente", options=[cliente])

        # Filtro Sócio: com base na coluna "socioResponsavel"
        socios = sorted(self.contracts["socioResponsavel"].unique())
        filtro_socio = st.sidebar.multiselect("Sócio", options=socios, default=socios)

        # Filtro Banco: caso exista a coluna "banco" nos dados
        if "banco" in self.contracts.columns:
            bancos = sorted(self.contracts["banco"].unique())
            filtro_banco = st.sidebar.multiselect("Banco", options=bancos, default=bancos)
        else:
            filtro_banco = None

        # Filtro Contrato: com base na coluna "tipoContrato"
        contratos = sorted(self.contracts["tipoContrato"].unique())
        filtro_contrato = st.sidebar.multiselect("Contrato", options=contratos, default=contratos)

        # Filtro Ano: com base na coluna "dataContratacao"
        if "dataContratacao" in self.contracts.columns:
            anos = sorted(self.contracts["dataContratacao"].dropna().dt.year.unique())
            filtro_ano = st.sidebar.multiselect("Ano", options=anos, default=anos)
        else:
            filtro_ano = None

        # Montando as condições de filtro
        cond = (self.contracts["socioResponsavel"].isin(filtro_socio)) & \
               (self.contracts["tipoContrato"].isin(filtro_contrato))
        if filtro_banco is not None:
            cond &= self.contracts["banco"].isin(filtro_banco)
        if filtro_ano is not None:
            cond &= self.contracts["dataContratacao"].dt.year.isin(filtro_ano)

        self.df_filtrado = self.contracts[cond]

    def render_consolidated_table(self):
        """Exibe a tabela consolidada (sócio, quantidade de contratos e valor total da dívida)."""
        consolidado = self.df_filtrado.groupby("socioResponsavel", as_index=False).agg(
            Quantidade_Contratos=('valorTotal', 'count'),
            Total_Divida=('valorTotal', 'sum')
        )
        consolidado.rename(columns={
            'socioResponsavel': 'Nome do Sócio',
            'Quantidade_Contratos': 'Quantidade de Contratos',
            'Total_Divida': 'Valor Total da Dívida'
        }, inplace=True)
        consolidado["Valor Total da Dívida"] = consolidado["Valor Total da Dívida"].apply(format_currency)
        st.subheader("Consolidado de Contratos")
        st.dataframe(consolidado)

    def render_detail_table(self):
        """Exibe a tabela detalhada dos contratos filtrados."""
        st.subheader("Tabela de Contratos Detalhada")
        st.dataframe(self.df_filtrado)

    def render_summary(self):
        """Exibe as métricas resumidas do dashboard."""
        total_divida = self.df_filtrado["valorTotal"].sum()
        st.subheader("Resumo")
        st.metric(label="Total da Dívida (R$)", value=format_currency(total_divida))

    def render_charts(self):
        """Exibe os gráficos baseados nos dados filtrados."""
        # Gráfico: Dívida Total por Banco
        divida_por_banco = self.df_filtrado.groupby("banco", as_index=False)["valorTotal"].sum()
        graf_banco = alt.Chart(divida_por_banco).mark_bar().encode(
            x=alt.X('banco:N', title='Banco'),
            y=alt.Y('valorTotal:Q', title='Dívida Total (R$)'),
            tooltip=['banco', 'valorTotal']
        ).properties(title="Total de Dívida por Banco", width=600)
        st.altair_chart(graf_banco, use_container_width=True)

        # Gráfico: Número de Contratos por Ano de Contratação
        if "dataContratacao" in self.df_filtrado.columns:
            df_temp = self.df_filtrado.copy()
            df_temp["AnoContratacao"] = df_temp["dataContratacao"].dt.year
            contagem_ano = df_temp.groupby("AnoContratacao").size().reset_index(name="Quantidade")
            graf_ano = alt.Chart(contagem_ano).mark_line(point=True).encode(
                x=alt.X('AnoContratacao:Q', title='Ano de Contratação'),
                y=alt.Y('Quantidade:Q', title='Número de Contratos'),
                tooltip=['AnoContratacao', 'Quantidade']
            ).properties(title="Contratos por Ano de Contratação", width=600)
            st.altair_chart(graf_ano, use_container_width=True)
        else:
            st.info("Coluna 'dataContratacao' não encontrada para gerar o gráfico de contratos por ano.")

    def render_dashboard(self):
        """Renderiza o dashboard completo."""
        st.title("Dashboard de Gestão de Endividamento")
        st.markdown("Visualize e filtre os contratos de endividamento do setor agro.")
        self.render_filters()

        if self.df_filtrado.empty:
            st.warning("Nenhum dado encontrado com os filtros selecionados.")
            return

        self.render_consolidated_table()
        self.render_detail_table()
        self.render_summary()
        self.render_charts()

if __name__ == "__main__":
    configure_locale()
    data = load_data()
    if data and "contratos" in data:
        dashboard = Dashboard(data)
        dashboard.prepare_data()
        dashboard.render_dashboard()
    else:
        st.error("Não foi possível carregar os dados dos contratos.")
