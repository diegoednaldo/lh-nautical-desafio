# Desafio de Dados: LH Nautical

Projeto desenvolvido para o desafio técnico da LH Nautical, cobrindo o pipeline completo:
EDA → modelagem de schema → carregamento em Postgres → análises de negócio → previsão de
demanda → sistema de recomendação.

## Stack

- **Python 3** (VSCode como ambiente principal)
- **PostgreSQL** rodando via Docker Compose
- **Jupyter Notebooks** para as entregas exploratórias/analíticas
- **Plotly e GitHub Pages** para o dashboard estático
- Bibliotecas: ver `requirements.txt`

## Estrutura do projeto

```
lh-nautical-desafio/
├── data/
│   └── raw/                # CSVs originais, sem nenhum tratamento (não editar)
├── sql/
│   ├── schema.sql          # gerado pela Questão 2 (src/generate_schema.py)
│   └── queries/            # queries .sql isoladas por questão
├── src/                    # código python reutilizável (scripts "de produção")
├── notebooks/              # notebooks de análise, um por frente/questão
├── dashboard/              # entregável final (painel/dashboard)
├── tests/                  # validações automatizadas do dashboard
├── .github/workflows/      # publicação no GitHub Pages
└── docs/                   # documentação original do desafio
```

## Como rodar

### 1. Configurar ambiente Python

```bash
python -m venv .venv
source .venv/bin/activate  # no Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurar variáveis de ambiente

```bash
cp .env.example .env
# edite o .env se necessário (usuário/senha/porta do Postgres)
```

### 3. Subir o banco Postgres local

```bash
docker compose up -d
```

Isso sobe um Postgres em `localhost:5432` com os dados definidos no `.env`.

### 4. Rodar os notebooks em ordem

| Notebook | Questão(ões) | Descrição |
|---|---|---|
| `01_eda_orders.ipynb` | Q1 | EDA bruta da tabela `orders`, sem tratamento |
| `02_schema_e_carga.ipynb` | Q2, Q3 | Geração do `schema.sql` e carga dos 24 CSVs no Postgres |
| `03_analise_clientes.ipynb` | Q4 | Identificação de clientes fiéis |
| `04_calendario_vendas.ipynb` | Q5 | Dimensão de datas e vendas médias por dia da semana |
| `05_previsao_demanda.ipynb` | Q6 | Baseline de previsão (média móvel) para Bússola de Bordo 702 |
| `06_recomendacao.ipynb` | Q7 | Sistema de recomendação por similaridade de cosseno |

### 5. Dashboard final

Gere o painel com os dados locais:

```bash
python src/build_dashboard.py
```

O arquivo final fica em `dashboard/index.html` e pode ser aberto diretamente no navegador. A pasta contém somente o HTML e os recursos estáticos necessários para publicação no GitHub Pages. Instruções e regras de cálculo estão em `dashboard/README.md`.

Para validar as métricas e a geração determinística:

```bash
python -m unittest tests.test_dashboard -v
```

## Status das entregas

- [x] Q1: EDA
- [x] Q2: Schema
- [x] Q3: Carregamento
- [x] Q4: Análise de clientes
- [x] Q5: Dimensão de calendário
- [x] Q6: Previsão de demanda
- [x] Q7: Sistema de recomendação
- [x] Dashboard final
