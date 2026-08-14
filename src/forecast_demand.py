"""Questão 6 - Previsão de demanda da Bússola de Bordo 702.

Regras analíticas adotadas:

- todos os pedidos são considerados, sem filtro de status, conforme o
  enunciado;
- todos os IDs cujo nome seja exatamente ``Bússola de Bordo 702`` são
  agregados porque o enunciado define o alvo pelo nome. O conjunto atual
  possui os IDs 74 e 240; eles têm nome e descrição iguais, mas marca e
  categoria diferentes. Portanto, essa agregação é uma hipótese operacional,
  não uma afirmação de que os cadastros representam comprovadamente o mesmo
  item físico;
- o histórico até dezembro de 2025 forma o treino inicial;
- janeiro a março de 2026 é avaliado em walk-forward mensal: a previsão de
  cada mês usa somente as três observações mensais anteriores. Depois de
  avaliar um mês, seu valor real passa a integrar o histórico do mês seguinte.
"""
import pandas as pd

if __package__:
    from .db import get_engine
else:
    from db import get_engine


PRODUCT_NAME = "Bússola de Bordo 702"
TRAIN_END = pd.Period("2025-12", freq="M")
TEST_PERIOD = pd.period_range("2026-01", "2026-03", freq="M")
TEST_END_EXCLUSIVE = "2026-04-01"
MOVING_AVERAGE_WINDOW = 3


def build_monthly_sales_series(engine) -> pd.Series:
    """Constrói a série mensal, unificando todos os IDs com nome exato."""
    products = pd.read_sql(
        f"SELECT id FROM products WHERE name = '{PRODUCT_NAME}'", engine
    )
    if products.empty:
        raise ValueError(f"Produto com nome exato '{PRODUCT_NAME}' não encontrado.")

    product_ids = products["id"].tolist()

    variants = pd.read_sql(
        f"SELECT id FROM product_variants WHERE product_id IN "
        f"({','.join(map(str, product_ids))})",
        engine,
    )
    if variants.empty:
        raise ValueError(f"Nenhuma variante encontrada para '{PRODUCT_NAME}'.")

    variant_ids = variants["id"].tolist()

    query = f"""
        SELECT oi.quantity, o.created_at
        FROM order_items oi
        JOIN orders o ON o.id = oi.order_id
        -- Regra do enunciado: não filtrar o status dos pedidos.
        WHERE oi.product_variant_id IN ({','.join(map(str, variant_ids))})
          AND o.created_at < '{TEST_END_EXCLUSIVE}'
    """
    vendas = pd.read_sql(query, engine)
    vendas["created_at"] = pd.to_datetime(vendas["created_at"])
    vendas["mes"] = vendas["created_at"].dt.to_period("M")

    vendas_mensais = vendas.groupby("mes")["quantity"].sum().sort_index()

    # Série contínua somente até o fim do período necessário para a avaliação.
    idx_completo = pd.period_range(
        vendas_mensais.index.min(), TEST_PERIOD[-1], freq="M"
    )
    return vendas_mensais.reindex(idx_completo, fill_value=0)


def walk_forward_forecast(
    vendas_mensais: pd.Series,
    train_end: pd.Period,
    test_period: pd.PeriodIndex,
    window: int = 3,
) -> pd.DataFrame:
    """Avalia a média móvel mensal em walk-forward, sem vazamento temporal."""
    history = vendas_mensais.loc[:train_end].copy()

    rows = []
    for month in test_period:
        prediction = history.iloc[-window:].mean()
        actual = vendas_mensais.loc[month]
        rows.append({"mes": month, "real": actual, "previsto": prediction})

        # Atualiza o histórico somente depois de prever e avaliar o mês atual.
        history.loc[month] = actual

    resultado = pd.DataFrame(rows).set_index("mes")
    resultado["previsto_arredondado"] = resultado["previsto"].round().astype(int)
    resultado["erro_absoluto"] = (resultado["real"] - resultado["previsto"]).abs()
    return resultado


def main():
    engine = get_engine()

    vendas_mensais = build_monthly_sales_series(engine)
    resultado = walk_forward_forecast(
        vendas_mensais,
        train_end=TRAIN_END,
        test_period=TEST_PERIOD,
        window=MOVING_AVERAGE_WINDOW,
    )

    mae = resultado["erro_absoluto"].mean()
    soma_previsao = resultado["previsto_arredondado"].sum()

    print(f"Produto (nome exato): {PRODUCT_NAME}")
    print("Status considerados: todos (sem filtro)")
    print(f"Treino inicial: histórico até {TRAIN_END}")
    print(f"Teste walk-forward: {TEST_PERIOD[0]} a {TEST_PERIOD[-1]}")
    print("\nResultado mensal:")
    print(resultado.to_string())
    print(f"\nMAE (previsão não arredondada): {mae:.2f}")
    print(f"Total real no 1º trimestre de 2026: {resultado['real'].sum():.0f}")
    print(
        "Total previsto no 1º trimestre de 2026 "
        f"(previsões mensais arredondadas): {soma_previsao}"
    )


if __name__ == "__main__":
    main()
