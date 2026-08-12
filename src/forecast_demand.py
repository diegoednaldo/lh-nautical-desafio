"""
Questão 6 - Previsão de Demanda: Bússola de Bordo 702

Constrói um baseline de previsão mensal de vendas usando média móvel dos
últimos 3 meses (rolling one-step-ahead), treina com dados até 31/12/2025
e avalia contra o 1º trimestre de 2026 usando MAE.

Nota de qualidade de dado: existem dois cadastros de produto com o nome
exatamente igual "Bússola de Bordo 702" (IDs 74 e 240). Como ambos têm
histórico de vendas real e não há como desambiguá-los com segurança
(a data de criação do cadastro não é confiável), as vendas de ambos são
somadas e tratadas como um único produto.
"""
import pandas as pd

from src.db import get_engine


def build_monthly_sales_series(engine) -> pd.Series:
    """Constrói a série mensal de vendas (soma de quantity) do produto
    'Bússola de Bordo 702', unificando os dois cadastros duplicados."""
    products = pd.read_sql(
        "SELECT id FROM products WHERE name = 'Bússola de Bordo 702'", engine
    )
    product_ids = products["id"].tolist()

    variants = pd.read_sql(
        f"SELECT id FROM product_variants WHERE product_id IN "
        f"({','.join(map(str, product_ids))})",
        engine,
    )
    variant_ids = variants["id"].tolist()

    query = f"""
        SELECT oi.quantity, o.created_at
        FROM order_items oi
        JOIN orders o ON o.id = oi.order_id
        WHERE oi.product_variant_id IN ({','.join(map(str, variant_ids))})
    """
    vendas = pd.read_sql(query, engine)
    vendas["created_at"] = pd.to_datetime(vendas["created_at"])
    vendas["mes"] = vendas["created_at"].dt.to_period("M")

    vendas_mensais = vendas.groupby("mes")["quantity"].sum().sort_index()

    # Preenche meses sem venda com 0, garantindo série contínua
    idx_completo = pd.period_range(
        vendas_mensais.index.min(), vendas_mensais.index.max(), freq="M"
    )
    return vendas_mensais.reindex(idx_completo, fill_value=0)


def moving_average_baseline(vendas_mensais: pd.Series, window: int = 3) -> pd.Series:
    """Previsão de cada mês = média móvel dos `window` meses anteriores
    (rolling one-step-ahead). O shift(1) garante que o mês M nunca usa a
    própria venda de M, só dados estritamente anteriores a M."""
    return vendas_mensais.rolling(window=window).mean().shift(1)


def evaluate_forecast(vendas_mensais: pd.Series, forecast: pd.Series,
                       periodo_teste: pd.PeriodIndex) -> pd.DataFrame:
    """Monta a tabela de comparação real vs. previsto e calcula o erro absoluto."""
    resultado = pd.DataFrame({
        "real": vendas_mensais.reindex(periodo_teste),
        "previsto": forecast.reindex(periodo_teste),
    })
    resultado["previsto_arredondado"] = resultado["previsto"].round().astype(int)
    resultado["erro_absoluto"] = (resultado["real"] - resultado["previsto"]).abs()
    return resultado


def main():
    engine = get_engine()

    vendas_mensais = build_monthly_sales_series(engine)
    forecast = moving_average_baseline(vendas_mensais, window=3)

    periodo_teste = pd.period_range("2026-01", "2026-03", freq="M")
    resultado = evaluate_forecast(vendas_mensais, forecast, periodo_teste)

    mae = resultado["erro_absoluto"].mean()
    soma_previsao = resultado["previsto_arredondado"].sum()

    print(resultado)
    print(f"\nMAE: {mae:.2f}")
    print(f"Soma real Q1 2026: {resultado['real'].sum()}")
    print(f"Soma da previsão (arredondada) Q1 2026: {soma_previsao}")


if __name__ == "__main__":
    main()