"""Questão 7: recomendação por similaridade de comportamento de compra.

O script considera todos os pedidos, sem filtro de status. A quantidade
comprada é ignorada: cada combinação cliente e produto recebe valor 1 quando
houve ao menos uma compra e 0 caso contrário.
"""

import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

if __package__:
    from .db import get_engine
else:
    from db import get_engine


REFERENCE_PRODUCT = "Motor de Popa 1949"
TOP_N = 5


def load_data(engine) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Carrega o catálogo de produtos e as interações cliente por produto."""
    products = pd.read_sql("SELECT id, name FROM products", engine)
    interactions = pd.read_sql(
        """
        SELECT o.customer_id, pv.product_id
        FROM order_items oi
        JOIN orders o ON o.id = oi.order_id
        JOIN product_variants pv ON pv.id = oi.product_variant_id
        """,
        engine,
    )
    return products, interactions


def build_binary_matrix(interactions: pd.DataFrame) -> pd.DataFrame:
    """Constrói a matriz binária com clientes nas linhas e produtos nas colunas."""
    interaction_counts = interactions.groupby(
        ["customer_id", "product_id"]
    ).size()
    return interaction_counts.unstack(fill_value=0).gt(0).astype(int)


def rank_similar_products(
    binary_matrix: pd.DataFrame,
    products: pd.DataFrame,
    reference_product: str = REFERENCE_PRODUCT,
    top_n: int = TOP_N,
) -> pd.DataFrame:
    """Retorna os produtos mais similares ao item de referência."""
    reference_rows = products.loc[products["name"] == reference_product, "id"]
    if reference_rows.empty:
        raise ValueError(f"Produto '{reference_product}' não encontrado.")

    reference_id = reference_rows.iloc[0]
    if reference_id not in binary_matrix.columns:
        raise ValueError(f"Produto '{reference_product}' não possui interações.")

    similarity_matrix = cosine_similarity(binary_matrix.T)
    similarities = pd.Series(
        similarity_matrix[binary_matrix.columns.get_loc(reference_id)],
        index=binary_matrix.columns,
        name="similaridade",
    )

    ranking = (
        similarities.drop(reference_id)
        .sort_values(ascending=False)
        .head(top_n)
        .rename_axis("product_id")
        .reset_index()
        .merge(products, left_on="product_id", right_on="id", how="left")
    )
    return ranking[["product_id", "name", "similaridade"]]


def main() -> None:
    engine = get_engine()
    products, interactions = load_data(engine)
    binary_matrix = build_binary_matrix(interactions)
    ranking = rank_similar_products(binary_matrix, products)

    print(f"Produto de referência: {REFERENCE_PRODUCT}")
    print("Status considerados: todos (sem filtro)")
    print(f"Matriz cliente x produto: {binary_matrix.shape}")
    print("\nTop 5 produtos mais similares:")
    print(ranking.to_string(index=False, formatters={"similaridade": "{:.6f}".format}))


if __name__ == "__main__":
    main()
