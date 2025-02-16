# AgroEasy - Gestão de Endividamento

Este projeto é uma dashboard interativa desenvolvida com [Streamlit](https://streamlit.io) para visualizar, filtrar e gerar relatórios dos dados de contratos. A aplicação permite a visualização de métricas, gráficos e tabelas detalhadas sobre o endividamento dos clientes.

## Estrutura do Projeto

**.devcontainer/**  
Contém a configuração para o ambiente de desenvolvimento no Visual Studio Code via Remote Containers.  
Arquivo: [.devcontainer/devcontainer.json](.devcontainer/devcontainer.json)

**.streamlit/**  
Pasta de configuração do Streamlit, onde está definido o tema da aplicação.  
Arquivo: [.streamlit/config.toml](.streamlit/config.toml)

**dados.json**  
Arquivo JSON com os dados dos contratos a serem analisados.

**dashboard.py**  
Código principal da aplicação.  
Arquivo: [dashboard.py](dashboard.py)

## Requisitos

- Python 3.8+
- Bibliotecas:
    - streamlit
    - pandas
    - altair
    - locale (biblioteca padrão)

Para instalar as dependências, execute:

```sh
pip install -r requirements.txt
```

## Como Executar

Na raiz do projeto, execute:

```sh
streamlit run dashboard.py
```

A aplicação será aberta no navegador padrão, exibindo o dashboard com as visualizações dos dados.

## Funcionalidades

### Leitura de Dados
- A função `carregar_dados` lê e carrega os dados do arquivo `dados.json`.

### Preparação dos Dados
- A classe `Dashboard` processa os dados, convertendo colunas de data e normalizando informações através da função `preparar_dados`.

### Filtragem e Visualizações
- Funções específicas para renderizar filtros, gráficos, resumos e tabelas detalhadas.

### Configurações do Tema
- As configurações de tema (cores, fontes e fundos) são definidas no arquivo `config.toml` e acessadas pela função `obter_configuracoes_tema`.

## Contribuição

Contribuições são bem-vindas! Abra issues ou envie pull requests para melhorias e correções no código.