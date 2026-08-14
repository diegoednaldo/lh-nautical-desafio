# Dashboard executivo

Painel estático construído com Python e Plotly para comunicar os resultados do desafio e explorações adicionais relevantes para a operação da LH Nautical.

## Conteúdo

- Performance mensal de e-commerce e lojas físicas
- Clientes fiéis e categoria mais comprada da Q4
- Venda média POS por dia da semana da Q5
- Avaliação walk-forward da demanda da Q6
- Recomendações de produtos da Q7
- Impacto financeiro das devoluções concluídas
- Pontualidade dos fornecedores

O painel usa azul-marinho, latão e papel claro como identidade visual. Títulos usam tipografia serifada e números usam tipografia monoespaçada. Não há dependência de fontes, imagens ou scripts externos.

## Gerar localmente

Na raiz do projeto, execute:

```powershell
.\.venv\Scripts\python.exe src\build_dashboard.py
```

Em outro ambiente com as dependências instaladas:

```bash
python src/build_dashboard.py
```

O comando lê `data/raw/`, valida os resultados principais e recria `dashboard/index.html`. A data de corte padrão é `14/08/2026`, alinhada ao `CURRENT_DATE` usado na validação final com PostgreSQL.

Para informar outro corte:

```bash
python src/build_dashboard.py --cutoff-date AAAA-MM-DD
```

Depois, abra `dashboard/index.html` no navegador. O HTML inclui o Plotly internamente e funciona sem servidor local.

## Tratamentos aplicados

- Q4 e Q7 preservam todo o período e todos os status, de acordo com os resultados validados nos notebooks.
- Q5 considera todos os status, somente o canal POS e um calendário completo até a data de corte.
- Q6 preserva todos os status e a avaliação walk-forward de janeiro a março de 2026.
- O comparativo de canais considera pedidos `paid` e `confirmed` até a data de corte.
- Devoluções consideram somente `completed`; variações evidentes de digitação nos motivos são agrupadas sem alterar os CSVs.
- Fornecedores consideram pedidos `received` com data prometida e usam o último recebimento registrado como data de conclusão.

O arquivo publicado contém somente indicadores agregados. CSVs brutos, credenciais e dados pessoais não são copiados para a pasta do dashboard.

## GitHub Pages

O workflow em `.github/workflows/pages.yml` publica somente esta pasta após um push na branch `main`. No repositório do GitHub, configure **Settings > Pages > Build and deployment > Source** como **GitHub Actions**.
