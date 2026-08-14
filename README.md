<p align="center">
  <img src="dashboard/assets/favicon.svg" width="88" alt="Símbolo da LH Nautical">
</p>

<h1 align="center">LH Nautical | Desafio Técnico de Dados</h1>

<p align="center">
  Solução em Python e PostgreSQL com análises em Jupyter Notebooks e dashboard executivo publicado no GitHub Pages.
</p>

<p align="center">
  <a href="https://diegoednaldo.github.io/lh-nautical-desafio/"><strong>Acessar o dashboard</strong></a>
  &nbsp;|&nbsp;
  <a href="notebooks/">Ver notebooks</a>
  &nbsp;|&nbsp;
  <a href="docs/documentacao_desafio.pdf">Documentação</a>
</p>

---

## Contexto do problema

O desafio propõe transformar os dados operacionais da LH Nautical em uma base estruturada e em informações úteis para decisões de negócio.

O projeto parte de 24 arquivos CSV e percorre o fluxo completo entre o dado bruto e a apresentação dos resultados:

- análise exploratória sem modificar os dados;
- geração automática de um schema PostgreSQL;
- carga integral dos CSVs no banco;
- análises de clientes e vendas;
- previsão de demanda;
- recomendação de produtos;
- dashboard executivo com explorações adicionais.

<p align="center">
  <strong>24 CSVs</strong> &nbsp;|&nbsp;
  <strong>433.424 registros</strong> &nbsp;|&nbsp;
  <strong>7 questões</strong> &nbsp;|&nbsp;
  <strong>6 notebooks</strong>
</p>

---

## Notebooks do projeto

As respostas, premissas, validações e conclusões estão organizadas nos notebooks abaixo.

### Exploração e banco de dados

- [01 | Análise exploratória de pedidos](notebooks/01_eda_orders.ipynb)
- [02 | Geração do schema e carga dos CSVs](notebooks/02_schema_e_carga.ipynb)

### Análises de negócio

- [03 | Identificação de clientes fiéis](notebooks/03_analise_clientes.ipynb)
- [04 | Calendário e vendas por dia da semana](notebooks/04_calendario_vendas.ipynb)

### Modelos analíticos

- [05 | Previsão de demanda](notebooks/05_previsao_demanda.ipynb)
- [06 | Recomendação de produtos](notebooks/06_recomendacao.ipynb)

---

## Etapas do projeto

### 1. Análise exploratória

- observação exclusiva da tabela `orders`;
- análise de período, valores e distribuição;
- identificação de outliers sem limpeza ou exclusão;
- consulta complementar em [`q1_eda_orders.sql`](sql/queries/q1_eda_orders.sql).

### 2. Geração automática do schema

- leitura dos 24 CSVs;
- inferência dos tipos PostgreSQL;
- uso exclusivo de bibliotecas padrão do Python;
- geração de [`schema.sql`](sql/schema.sql) por [`generate_schema.py`](src/generate_schema.py).

### 3. Carga no PostgreSQL

- uso de `COPY` para carga em massa;
- preservação de nulos e caracteres especiais;
- validação das contagens carregadas;
- proteção contra uma nova carga em tabelas que já possuem dados.

Script: [`load_csvs.py`](src/load_csvs.py).

### 4. Análise de clientes fiéis

- faturamento total, frequência e ticket médio;
- diversidade de categorias compradas;
- seleção dos clientes com pelo menos 13 categorias;
- identificação da categoria mais comprada pelo top 10.

Consulta: [`q4_clientes_fieis.sql`](sql/queries/q4_clientes_fieis.sql).

### 5. Análise temporal de vendas

- seleção do canal `pos`;
- calendário contínuo desde a primeira venda;
- inclusão dos dias sem vendas com valor zero;
- comparação das médias por dia da semana.

Consulta: [`q5_calendario_vendas.sql`](sql/queries/q5_calendario_vendas.sql).

### 6. Previsão de demanda

- produto analisado: `Bússola de Bordo 702`;
- baseline de média móvel dos três meses anteriores;
- avaliação walk-forward de janeiro a março de 2026;
- cálculo do erro absoluto médio.

Script: [`forecast_demand.py`](src/forecast_demand.py).

### 7. Sistema de recomendação

- matriz binária entre clientes e produtos;
- quantidade comprada ignorada;
- similaridade de cosseno entre produtos;
- ranking dos itens mais próximos ao `Motor de Popa 1949`.

Script: [`recommend_products.py`](src/recommend_products.py).

---

## Dashboard executivo

### [Acessar o dashboard publicado](https://diegoednaldo.github.io/lh-nautical-desafio/)

O painel foi desenvolvido com Python e Plotly e publicado como site estático no GitHub Pages. A versão atual utiliza a data de corte analítica de **14/08/2026**.

O dashboard apresenta:

- indicadores executivos da operação;
- faturamento mensal de e-commerce e lojas físicas;
- ranking dos clientes fiéis;
- vendas médias POS por dia da semana;
- demanda real comparada ao baseline;
- reembolsos por motivo de devolução;
- pontualidade dos fornecedores;
- recomendações de produtos.

O arquivo publicado contém somente métricas agregadas e não depende de servidor, banco de dados ou credenciais para funcionar.

Gerador: [`build_dashboard.py`](src/build_dashboard.py)<br>
Metodologia: [`dashboard/README.md`](dashboard/README.md)

---

## Tecnologias utilizadas

- Python, pandas e NumPy;
- PostgreSQL 16 e SQL;
- psycopg2 e SQLAlchemy;
- Docker e Docker Compose;
- Jupyter Notebook;
- scikit-learn;
- Plotly, Matplotlib e Seaborn;
- GitHub Actions e GitHub Pages.

---

## Principais insights

- **Canais:** o e-commerce se destaca pelo volume, não pelo ticket médio.
- **Clientes:** o grupo fiel oferece oportunidades de retenção e cross-sell.
- **Vendas POS:** incluir dias sem venda evita médias superestimadas.
- **Operação:** devoluções e atrasos indicam pontos de melhoria no checkout e em compras.
- **Modelos:** previsão e recomendação funcionam como referências exploratórias.

Os valores detalhados estão disponíveis nos notebooks e no dashboard.

---

## Limitações

- A previsão utiliza um baseline simples e não representa um modelo pronto para produção.
- A recomendação considera apenas a sobreposição de clientes e não utiliza atributos dos produtos.
- A estabilidade do ranking de recomendações não foi avaliada.
- A Q6 agrega dois cadastros com o nome `Bússola de Bordo 702`, conforme hipótese documentada no projeto.
- O conjunto possui pedidos posteriores à data de corte. Cada análise temporal explicita o período utilizado.
- A base não oferece custos históricos suficientes para calcular lucro ou prejuízo líquido com segurança.
- A relação entre atrasos de fornecedores e falta de estoque é uma hipótese, não uma conclusão causal.

---

## Próximos passos possíveis

As entregas exigidas pelo desafio estão concluídas. Em uma evolução para uso contínuo, seria possível:

- formalizar uma regra de negócio única para os status que representam venda;
- ampliar os testes de qualidade e integridade dos dados;
- avaliar a previsão em múltiplas janelas temporais;
- medir a estabilidade do sistema de recomendação;
- automatizar a atualização do dashboard em um ambiente seguro.

---

## Como executar o projeto

### 1. Clonar e preparar o ambiente

```bash
git clone https://github.com/diegoednaldo/lh-nautical-desafio.git
cd lh-nautical-desafio

python -m venv .venv
```

No Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

No Linux ou macOS:

```bash
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Adicionar os dados

Os CSVs brutos não são versionados. Coloque os 24 arquivos originais diretamente em `data/raw/`, sem alterar nomes, colunas ou valores.

### 3. Iniciar o PostgreSQL

```bash
docker compose up -d
```

### 4. Gerar o schema e carregar o banco

O fluxo completo da Q2 e da Q3 está no notebook [`02_schema_e_carga.ipynb`](notebooks/02_schema_e_carga.ipynb).

Os scripts também podem ser executados separadamente:

```bash
python src/generate_schema.py
python src/load_csvs.py
```

O arquivo `sql/schema.sql` precisa ser aplicado ao PostgreSQL antes da execução do carregador.

### 5. Executar os notebooks

```bash
jupyter lab
```

Abra o Jupyter na raiz do projeto e execute os notebooks em ordem numérica.

### 6. Executar scripts, dashboard e testes

```bash
python src/forecast_demand.py
python src/recommend_products.py
python src/build_dashboard.py
python -m unittest tests.test_dashboard -v
```

O dashboard local será salvo em `dashboard/index.html`.

---

## Segurança dos dados

- os CSVs originais não são modificados nem versionados;
- o arquivo `.env` não é adicionado ao Git;
- credenciais locais permanecem fora do código;
- dados pessoais, fiscais e endereços não são publicados no dashboard.

---

## Autor

Desenvolvido por [diegoednaldo](https://github.com/diegoednaldo).
