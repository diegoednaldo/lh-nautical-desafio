"""Gera o dashboard estático da LH Nautical para publicação no GitHub Pages.

O gerador lê os CSVs locais, aplica apenas os tratamentos documentados e
incorpora dados agregados ao HTML. Nenhum registro detalhado ou dado pessoal é
publicado.
"""

from __future__ import annotations

import argparse
import csv
import html
import unicodedata
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from sklearn.metrics.pairwise import cosine_similarity


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
DEFAULT_OUTPUT = PROJECT_ROOT / "dashboard" / "index.html"
DEFAULT_CUTOFF_DATE = "2026-08-14"

NAVY = "#081C2A"
STRUCTURAL_BLUE = "#21495B"
BRASS = "#B98A37"
LIGHT_BRASS = "#D0AE68"
PAPER = "#FBF7EB"
TEXT = "#16262E"
MUTED = "#58666C"
COPPER = "#8C3F2C"
OPERATIONAL_GREEN = "#1F6460"
GRID = "rgba(19, 47, 63, 0.13)"

TITLE_FONT = "Georgia, Cambria, Times New Roman, serif"
NUMBER_FONT = "Consolas, Liberation Mono, Courier New, monospace"
BODY_FONT = "Segoe UI, Arial, sans-serif"

EXPECTED_TOP10_CUSTOMERS = [
    22,
    1477,
    929,
    1116,
    1691,
    774,
    1470,
    1599,
    965,
    1722,
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera o dashboard estático.")
    parser.add_argument(
        "--cutoff-date",
        default=DEFAULT_CUTOFF_DATE,
        help="Data de corte no formato AAAA-MM-DD.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Arquivo HTML de saída.",
    )
    return parser.parse_args()


def read_csv(name: str, columns: list[str] | None = None, **kwargs) -> pd.DataFrame:
    path = RAW_DATA_DIR / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Arquivo obrigatório não encontrado: {path}")
    return pd.read_csv(path, usecols=columns, **kwargs)


def require_columns(frame: pd.DataFrame, expected: set[str], source: str) -> None:
    missing = expected.difference(frame.columns)
    if missing:
        raise ValueError(f"Colunas ausentes em {source}: {sorted(missing)}")


def format_decimal_pt(value: float | Decimal, decimals: int = 2) -> str:
    formatted = f"{float(value):,.{decimals}f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def format_brl(value: float | Decimal) -> str:
    return f"R$ {format_decimal_pt(value, 2)}"


def format_compact_brl(value: float | Decimal) -> str:
    numeric = float(value)
    if abs(numeric) >= 1_000_000_000:
        return f"R$ {format_decimal_pt(numeric / 1_000_000_000, 2)} bi"
    if abs(numeric) >= 1_000_000:
        return f"R$ {format_decimal_pt(numeric / 1_000_000, 2)} mi"
    if abs(numeric) >= 1_000:
        return f"R$ {format_decimal_pt(numeric / 1_000, 1)} mil"
    return format_brl(numeric)


def format_int(value: int | float) -> str:
    return f"{int(round(value)):,}".replace(",", ".")


def format_percent(value: float, decimals: int = 1) -> str:
    return f"{value * 100:.{decimals}f}%".replace(".", ",")


def format_date_pt(value: pd.Timestamp) -> str:
    return value.strftime("%d/%m/%Y")


def normalize_text(value: object) -> str:
    text = " ".join(str(value).strip().lower().split())
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def count_raw_rows() -> tuple[int, int]:
    files = sorted(RAW_DATA_DIR.glob("*.csv"))
    total_rows = 0
    for path in files:
        with path.open(newline="", encoding="utf-8") as stream:
            total_rows += max(sum(1 for _ in csv.reader(stream)) - 1, 0)
    return len(files), total_rows


def load_sources() -> dict[str, pd.DataFrame]:
    sources = {
        "orders": read_csv(
            "orders",
            ["id", "channel", "customer_id", "status", "total", "created_at"],
            parse_dates=["created_at"],
        ),
        "order_items": read_csv(
            "order_items",
            ["id", "order_id", "product_variant_id", "quantity", "line_total"],
        ),
        "product_variants": read_csv(
            "product_variants", ["id", "product_id"]
        ),
        "products": read_csv("products", ["id", "name", "category_id"]),
        "categories": read_csv("categories", ["id", "name"]),
        "returns": read_csv(
            "returns",
            ["id", "status", "reason", "total_refund_amount", "created_at"],
            parse_dates=["created_at"],
        ),
        "purchase_orders": read_csv(
            "purchase_orders",
            [
                "id",
                "supplier_id",
                "status",
                "placed_at",
                "expected_delivery_at",
            ],
            parse_dates=["placed_at", "expected_delivery_at"],
        ),
        "goods_receipts": read_csv(
            "goods_receipts", ["id", "purchase_order_id", "received_at"],
            parse_dates=["received_at"],
        ),
        "suppliers": read_csv("suppliers", ["id", "trade_name"]),
    }

    require_columns(
        sources["orders"],
        {"id", "channel", "customer_id", "status", "total", "created_at"},
        "orders.csv",
    )
    return sources


def calculate_q4(sources: dict[str, pd.DataFrame]) -> dict[str, object]:
    orders_exact = read_csv(
        "orders", ["id", "customer_id", "total"], dtype={"total": str}
    )
    orders_exact["total_decimal"] = orders_exact["total"].map(Decimal)

    customer_metrics = (
        orders_exact.groupby("customer_id", as_index=False)
        .agg(
            faturamento_total=("total_decimal", "sum"),
            frequencia=("id", "count"),
        )
    )
    customer_metrics["ticket_medio_decimal"] = customer_metrics.apply(
        lambda row: (row["faturamento_total"] / Decimal(int(row["frequencia"]))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ),
        axis=1,
    )

    orders = sources["orders"]
    items = sources["order_items"]
    variants = sources["product_variants"].rename(
        columns={"id": "product_variant_id"}
    )
    products = sources["products"].rename(columns={"id": "product_id"})

    category_events = (
        items[["order_id", "product_variant_id", "quantity"]]
        .merge(
            orders[["id", "customer_id"]].rename(columns={"id": "order_id"}),
            on="order_id",
            how="inner",
        )
        .merge(variants, on="product_variant_id", how="inner")
        .merge(products[["product_id", "category_id"]], on="product_id", how="inner")
    )

    diversity = (
        category_events.groupby("customer_id")["category_id"]
        .nunique()
        .rename("diversidade_categorias")
        .reset_index()
    )
    ranking = customer_metrics.merge(diversity, on="customer_id", how="inner")
    ranking = ranking[ranking["diversidade_categorias"] >= 13].sort_values(
        ["ticket_medio_decimal", "customer_id"], ascending=[False, True]
    )
    top10 = ranking.head(10).copy()
    top10["ticket_medio"] = top10["ticket_medio_decimal"].map(float)
    top10["faturamento_total_num"] = top10["faturamento_total"].map(float)

    top_ids = top10["customer_id"].astype(int).tolist()
    category_sales = category_events[category_events["customer_id"].isin(top_ids)]
    category_sales = category_sales.merge(
        sources["categories"].rename(
            columns={"id": "category_id", "name": "categoria"}
        ),
        on="category_id",
        how="inner",
    )
    category_ranking = (
        category_sales.groupby("categoria", as_index=False)["quantity"]
        .sum()
        .sort_values(["quantity", "categoria"], ascending=[False, True])
    )
    category_leader = category_ranking.iloc[0]

    if top_ids != EXPECTED_TOP10_CUSTOMERS:
        raise AssertionError(f"Top 10 da Q4 divergente: {top_ids}")
    if category_leader["categoria"] != "Hélices" or int(category_leader["quantity"]) != 492:
        raise AssertionError("Categoria principal da Q4 divergente.")

    return {
        "top10": top10,
        "category": str(category_leader["categoria"]),
        "category_quantity": int(category_leader["quantity"]),
    }


def calculate_q5(
    orders: pd.DataFrame, cutoff: pd.Timestamp
) -> dict[str, object]:
    minimum_date = orders["created_at"].min().normalize()
    orders_period = orders[
        orders["created_at"].between(minimum_date, cutoff, inclusive="both")
    ].copy()
    pos = orders_period[orders_period["channel"] == "pos"].copy()
    pos["date"] = pos["created_at"].dt.normalize()

    daily = pos.groupby("date")["total"].sum()
    calendar = pd.DataFrame(
        {"date": pd.date_range(minimum_date, cutoff.normalize(), freq="D")}
    )
    calendar["sales"] = calendar["date"].map(daily).fillna(0.0)
    calendar["weekday_number"] = calendar["date"].dt.dayofweek

    weekday_names = {
        0: "Segunda-feira",
        1: "Terça-feira",
        2: "Quarta-feira",
        3: "Quinta-feira",
        4: "Sexta-feira",
        5: "Sábado",
        6: "Domingo",
    }
    weekday = (
        calendar.groupby("weekday_number", as_index=False)
        .agg(media_venda=("sales", "mean"), dias=("date", "size"))
        .sort_values("weekday_number")
    )
    weekday["dia_semana"] = weekday["weekday_number"].map(weekday_names)
    weekday["media_venda"] = weekday["media_venda"].round(2)
    worst = weekday.sort_values(["media_venda", "weekday_number"]).iloc[0]

    if cutoff.strftime("%Y-%m-%d") == DEFAULT_CUTOFF_DATE:
        if worst["dia_semana"] != "Quinta-feira" or float(worst["media_venda"]) != 151027.72:
            raise AssertionError("Resultado da Q5 divergente do notebook validado.")

    return {
        "weekday": weekday,
        "worst_day": str(worst["dia_semana"]),
        "worst_average": float(worst["media_venda"]),
        "minimum_date": minimum_date,
        "calendar_days": len(calendar),
        "zero_sales_days": int((calendar["sales"] == 0).sum()),
    }


def calculate_q6(sources: dict[str, pd.DataFrame]) -> dict[str, object]:
    products = sources["products"]
    target_products = products[products["name"] == "Bússola de Bordo 702"]
    product_ids = target_products["id"].astype(int).tolist()
    variant_ids = sources["product_variants"].loc[
        sources["product_variants"]["product_id"].isin(product_ids), "id"
    ]

    sales = (
        sources["order_items"].loc[
            sources["order_items"]["product_variant_id"].isin(variant_ids),
            ["order_id", "quantity"],
        ]
        .merge(
            sources["orders"][["id", "created_at"]].rename(
                columns={"id": "order_id"}
            ),
            on="order_id",
            how="inner",
        )
    )
    sales = sales[sales["created_at"] < pd.Timestamp("2026-04-01")].copy()
    sales["month"] = sales["created_at"].dt.to_period("M")
    monthly = sales.groupby("month")["quantity"].sum().sort_index()
    complete_index = pd.period_range(monthly.index.min(), "2026-03", freq="M")
    monthly = monthly.reindex(complete_index, fill_value=0)

    history = monthly.loc[: pd.Period("2025-12", freq="M")].copy()
    rows = []
    for month in pd.period_range("2026-01", "2026-03", freq="M"):
        forecast = float(history.iloc[-3:].mean())
        actual = float(monthly.loc[month])
        rows.append({"month": month, "real": actual, "forecast": forecast})
        history.loc[month] = actual

    result = pd.DataFrame(rows)
    result["forecast_rounded"] = result["forecast"].round().astype(int)
    result["absolute_error"] = (result["real"] - result["forecast"]).abs()
    forecast_total = int(result["forecast_rounded"].sum())
    actual_total = int(result["real"].sum())
    mae = float(result["absolute_error"].mean())

    if forecast_total != 149 or actual_total != 207 or round(mae, 2) != 19.44:
        raise AssertionError("Resultado da Q6 divergente do notebook validado.")

    return {
        "monthly": result,
        "forecast_total": forecast_total,
        "actual_total": actual_total,
        "mae": mae,
        "product_ids": product_ids,
    }


def calculate_q7(sources: dict[str, pd.DataFrame]) -> dict[str, object]:
    interactions = (
        sources["order_items"][["order_id", "product_variant_id"]]
        .merge(
            sources["orders"][["id", "customer_id"]].rename(
                columns={"id": "order_id"}
            ),
            on="order_id",
            how="inner",
        )
        .merge(
            sources["product_variants"].rename(
                columns={"id": "product_variant_id"}
            ),
            on="product_variant_id",
            how="inner",
        )[["customer_id", "product_id"]]
        .drop_duplicates()
    )
    interactions["value"] = 1
    matrix = interactions.pivot(
        index="customer_id", columns="product_id", values="value"
    ).fillna(0)

    reference = sources["products"].loc[
        sources["products"]["name"] == "Motor de Popa 1949", "id"
    ]
    if reference.empty:
        raise ValueError("Produto de referência da Q7 não encontrado.")
    reference_id = int(reference.iloc[0])

    similarity = cosine_similarity(matrix.T)
    scores = pd.Series(
        similarity[matrix.columns.get_loc(reference_id)],
        index=matrix.columns,
        name="similaridade",
    )
    ranking = (
        scores.drop(reference_id)
        .sort_values(ascending=False)
        .head(5)
        .rename_axis("product_id")
        .reset_index()
        .merge(
            sources["products"][["id", "name"]],
            left_on="product_id",
            right_on="id",
            how="left",
        )[["product_id", "name", "similaridade"]]
    )

    first = ranking.iloc[0]
    if first["name"] != "Motor de Popa 5331" or round(float(first["similaridade"]), 6) != 0.256553:
        raise AssertionError("Resultado da Q7 divergente do notebook validado.")

    return {
        "ranking": ranking,
        "reference_id": reference_id,
        "matrix_shape": matrix.shape,
    }


def calculate_channels(
    orders: pd.DataFrame, cutoff: pd.Timestamp
) -> dict[str, object]:
    business = orders[
        orders["status"].isin(["paid", "confirmed"])
        & (orders["created_at"] <= cutoff)
    ].copy()
    business["month"] = business["created_at"].dt.to_period("M").dt.to_timestamp()
    monthly = (
        business.groupby(["month", "channel"], as_index=False)
        .agg(faturamento=("total", "sum"), pedidos=("id", "size"))
        .sort_values(["month", "channel"])
    )
    summary = (
        business.groupby("channel", as_index=False)
        .agg(
            faturamento=("total", "sum"),
            pedidos=("id", "size"),
            ticket_medio=("total", "mean"),
        )
        .sort_values("channel")
    )
    ecommerce_revenue = float(
        summary.loc[summary["channel"] == "ecommerce", "faturamento"].iloc[0]
    )
    total_revenue = float(summary["faturamento"].sum())
    ecommerce_share = ecommerce_revenue / total_revenue

    monthly["year"] = monthly["month"].dt.year
    yearly = (
        monthly.groupby(["year", "channel"], as_index=False)["faturamento"]
        .sum()
        .pivot(index="year", columns="channel", values="faturamento")
        .fillna(0)
        .reset_index()
    )

    return {
        "monthly": monthly,
        "summary": summary,
        "yearly": yearly,
        "ecommerce_share": ecommerce_share,
        "business_orders": len(business),
        "total_revenue": total_revenue,
    }


def clean_return_reason(value: object) -> str:
    if pd.isna(value):
        return "Não informado"

    key = normalize_text(value)
    mapping = {
        "cliente desistiu da compra": "Cliente desistiu da compra",
        "cliente desistui da compra": "Cliente desistiu da compra",
        "compra duplicada": "Compra duplicada",
        "produto avariado no transporte": "Produto avariado no transporte",
        "produt oavariado no transporte": "Produto avariado no transporte",
        "produto variado no transporte": "Produto avariado no transporte",
        "tamanho/cor incorretos": "Tamanho/cor incorretos",
        "tamanho/cor incorretoos": "Tamanho/cor incorretos",
        "tamanho/cor iincorretos": "Tamanho/cor incorretos",
        "tamanho/coor incorretos": "Tamanho/cor incorretos",
        "produto com defeito de fabrica": "Produto com defeito de fábrica",
        "produto ccom defeito de fabrica": "Produto com defeito de fábrica",
        "produto com defeitoo de fabrica": "Produto com defeito de fábrica",
        "item nao corresponde a descricao": "Item não corresponde à descrição",
        "item nao corresponde a descricaoo": "Item não corresponde à descrição",
        "item nao corressponde a descricao": "Item não corresponde à descrição",
        "outros": "Outros",
    }
    if not key or not any(character.isalnum() for character in key):
        return "Não informado"
    if key not in mapping:
        raise ValueError(f"Motivo de devolução sem regra explícita: {value!r}")
    return mapping[key]


def calculate_returns(
    returns: pd.DataFrame, cutoff: pd.Timestamp
) -> dict[str, object]:
    completed = returns[
        (returns["status"] == "completed") & (returns["created_at"] <= cutoff)
    ].copy()
    completed["motivo"] = completed["reason"].map(clean_return_reason)
    ranking = (
        completed.groupby("motivo", as_index=False)
        .agg(
            devolucoes=("id", "size"),
            reembolso=("total_refund_amount", "sum"),
        )
        .sort_values(["reembolso", "motivo"], ascending=[False, True])
    )
    return {
        "ranking": ranking,
        "refund_total": float(ranking["reembolso"].sum()),
        "completed_returns": int(ranking["devolucoes"].sum()),
    }


def calculate_suppliers(
    sources: dict[str, pd.DataFrame], cutoff: pd.Timestamp
) -> dict[str, object]:
    purchase_orders = sources["purchase_orders"]
    purchase_orders = purchase_orders[
        (purchase_orders["status"] == "received")
        & (purchase_orders["placed_at"] <= cutoff)
        & purchase_orders["expected_delivery_at"].notna()
    ].copy()

    goods_receipts = sources["goods_receipts"]
    goods_receipts = goods_receipts[
        (goods_receipts["received_at"] <= cutoff)
        & goods_receipts["purchase_order_id"].isin(purchase_orders["id"])
    ].copy()
    completed_at = goods_receipts.groupby("purchase_order_id")["received_at"].max()

    completed = purchase_orders.merge(
        completed_at.rename("completed_at"),
        left_on="id",
        right_index=True,
        how="inner",
    )
    completed["delay_days"] = (
        completed["completed_at"].dt.normalize()
        - completed["expected_delivery_at"].dt.normalize()
    ).dt.days
    completed["on_time"] = completed["delay_days"] <= 0

    overall_on_time = float(completed["on_time"].mean())
    late_orders = int((~completed["on_time"]).sum())

    def mean_late_days(values: pd.Series) -> float:
        late = values[values > 0]
        return float(late.mean()) if not late.empty else 0.0

    supplier_summary = (
        completed.groupby("supplier_id", as_index=False)
        .agg(
            pedidos_concluidos=("id", "size"),
            pontualidade=("on_time", "mean"),
            atraso_medio_dias=("delay_days", mean_late_days),
        )
        .merge(
            sources["suppliers"].rename(
                columns={"id": "supplier_id", "trade_name": "fornecedor"}
            ),
            on="supplier_id",
            how="left",
        )
    )
    supplier_summary["rotulo"] = supplier_summary.apply(
        lambda row: f"F{int(row['supplier_id']):02d} · {row['fornecedor']}", axis=1
    )
    worst = supplier_summary.sort_values(
        ["pontualidade", "pedidos_concluidos", "supplier_id"],
        ascending=[True, False, True],
    ).head(8)

    return {
        "ranking": worst,
        "overall_on_time": overall_on_time,
        "completed_orders": len(completed),
        "late_orders": late_orders,
        "average_late_days": mean_late_days(completed["delay_days"]),
    }


def build_data(cutoff_date: str) -> dict[str, object]:
    cutoff_day = pd.Timestamp(cutoff_date).normalize()
    cutoff = cutoff_day + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
    sources = load_sources()
    raw_table_count, raw_row_count = count_raw_rows()

    q4 = calculate_q4(sources)
    q5 = calculate_q5(sources["orders"], cutoff)
    q6 = calculate_q6(sources)
    q7 = calculate_q7(sources)
    channels = calculate_channels(sources["orders"], cutoff)
    returns = calculate_returns(sources["returns"], cutoff)
    suppliers = calculate_suppliers(sources, cutoff)

    future_orders = int((sources["orders"]["created_at"] > cutoff).sum())

    data = {
        "cutoff_day": cutoff_day,
        "raw_table_count": raw_table_count,
        "raw_row_count": raw_row_count,
        "raw_order_count": len(sources["orders"]),
        "future_orders": future_orders,
        "q4": q4,
        "q5": q5,
        "q6": q6,
        "q7": q7,
        "channels": channels,
        "returns": returns,
        "suppliers": suppliers,
    }

    if cutoff_day.strftime("%Y-%m-%d") == DEFAULT_CUTOFF_DATE:
        validate_default_snapshot(data)
    return data


def validate_default_snapshot(data: dict[str, object]) -> None:
    checks = [
        (data["raw_table_count"] == 24, "quantidade de arquivos CSV"),
        (data["raw_row_count"] == 433_424, "quantidade bruta de registros"),
        (data["raw_order_count"] == 48_998, "quantidade bruta de pedidos"),
        (data["future_orders"] == 4_271, "pedidos após a data de corte"),
        (data["q5"]["calendar_days"] == 2_418, "dias do calendário da Q5"),
        (data["q5"]["zero_sales_days"] == 76, "dias sem venda da Q5"),
        (data["channels"]["business_orders"] == 38_097, "pedidos dos canais"),
        (
            round(data["channels"]["total_revenue"], 2) == 1_096_687_344.91,
            "faturamento dos canais",
        ),
        (data["returns"]["completed_returns"] == 717, "devoluções concluídas"),
        (
            round(data["returns"]["refund_total"], 2) == 4_276_548.78,
            "valor total reembolsado",
        ),
        (data["suppliers"]["completed_orders"] == 879, "pedidos recebidos"),
        (data["suppliers"]["late_orders"] == 160, "pedidos recebidos com atraso"),
        (
            round(data["suppliers"]["overall_on_time"] * 100, 2) == 81.80,
            "pontualidade geral",
        ),
    ]
    failed = [label for valid, label in checks if not valid]
    if failed:
        raise AssertionError(
            "Snapshot padrão divergente em: " + ", ".join(failed)
        )


def style_figure(fig: go.Figure, height: int = 410) -> go.Figure:
    fig.update_layout(
        autosize=True,
        height=height,
        margin=dict(l=62, r=24, t=28, b=58),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=PAPER,
        font=dict(family=BODY_FONT, size=13, color=TEXT),
        hoverlabel=dict(
            bgcolor=NAVY,
            bordercolor=LIGHT_BRASS,
            font=dict(family=BODY_FONT, size=13, color=PAPER),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=12),
        ),
        modebar=dict(bgcolor="rgba(251,247,235,0.9)", color=STRUCTURAL_BLUE),
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor=GRID,
        zeroline=False,
        linecolor="rgba(19,47,63,0.35)",
        tickfont=dict(family=NUMBER_FONT, size=11, color=MUTED),
        title_font=dict(family=BODY_FONT, size=12, color=MUTED),
        automargin=True,
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor=GRID,
        zeroline=False,
        linecolor="rgba(19,47,63,0.35)",
        tickfont=dict(family=NUMBER_FONT, size=11, color=MUTED),
        title_font=dict(family=BODY_FONT, size=12, color=MUTED),
        automargin=True,
    )
    return fig


def build_figures(data: dict[str, object]) -> dict[str, go.Figure]:
    figures: dict[str, go.Figure] = {}

    channel_fig = go.Figure()
    channel_styles = {
        "ecommerce": ("E-commerce", NAVY, "solid", "circle"),
        "pos": ("Lojas físicas", BRASS, "dash", "square"),
    }
    for channel, (label, color, dash, symbol) in channel_styles.items():
        subset = data["channels"]["monthly"]
        subset = subset[subset["channel"] == channel]
        hover = [
            f"<b>{label}</b><br>{row.month.strftime('%m/%Y')}<br>"
            f"Faturamento: {format_brl(row.faturamento)}<br>"
            f"Pedidos: {format_int(row.pedidos)}"
            for row in subset.itertuples()
        ]
        channel_fig.add_trace(
            go.Scatter(
                x=subset["month"],
                y=subset["faturamento"],
                name=label,
                mode="lines+markers",
                line=dict(color=color, width=2.4, dash=dash),
                marker=dict(color=color, size=6, symbol=symbol),
                text=hover,
                hovertemplate="%{text}<extra></extra>",
            )
        )
    style_figure(channel_fig, height=430)
    channel_fig.update_xaxes(dtick="M12", tickformat="%Y", title="Mês da venda")
    channel_fig.update_yaxes(title="Faturamento (R$)", tickformat=".2s")
    figures["channels"] = channel_fig

    customers = data["q4"]["top10"].sort_values("ticket_medio")
    customer_labels = customers["customer_id"].map(lambda value: f"Cliente {int(value)}")
    customer_colors = [STRUCTURAL_BLUE] * len(customers)
    customer_colors[-1] = BRASS
    customer_hover = [
        f"<b>Cliente {int(row.customer_id)}</b><br>"
        f"Ticket médio: {format_brl(row.ticket_medio)}<br>"
        f"Faturamento: {format_brl(row.faturamento_total_num)}<br>"
        f"Pedidos: {format_int(row.frequencia)}<br>"
        f"Categorias: {format_int(row.diversidade_categorias)}"
        for row in customers.itertuples()
    ]
    customer_fig = go.Figure(
        go.Bar(
            x=customers["ticket_medio"],
            y=customer_labels,
            orientation="h",
            marker=dict(color=customer_colors, line=dict(color=NAVY, width=0.5)),
            text=customers["ticket_medio"].map(format_compact_brl),
            textposition="outside",
            hovertext=customer_hover,
            hovertemplate="%{hovertext}<extra></extra>",
            cliponaxis=False,
        )
    )
    style_figure(customer_fig, height=470)
    customer_fig.update_xaxes(title="Ticket médio (R$)", tickformat=".3s")
    customer_fig.update_yaxes(showgrid=False)
    figures["customers"] = customer_fig

    weekday = data["q5"]["weekday"]
    weekday_colors = [
        COPPER if name == data["q5"]["worst_day"] else STRUCTURAL_BLUE
        for name in weekday["dia_semana"]
    ]
    weekday_hover = [
        f"<b>{row.dia_semana}</b><br>Média: {format_brl(row.media_venda)}<br>"
        f"Dias no calendário: {format_int(row.dias)}"
        for row in weekday.itertuples()
    ]
    weekday_fig = go.Figure(
        go.Bar(
            x=weekday["dia_semana"],
            y=weekday["media_venda"],
            marker=dict(color=weekday_colors),
            text=weekday["media_venda"].map(format_compact_brl),
            textposition="outside",
            hovertext=weekday_hover,
            hovertemplate="%{hovertext}<extra></extra>",
            cliponaxis=False,
        )
    )
    style_figure(weekday_fig, height=410)
    weekday_fig.update_xaxes(title=None, tickangle=-24, showgrid=False)
    weekday_fig.update_yaxes(title="Venda média (R$)", rangemode="tozero")
    figures["weekday"] = weekday_fig

    forecast = data["q6"]["monthly"]
    month_labels = forecast["month"].map(
        {pd.Period("2026-01", freq="M"): "Jan/2026", pd.Period("2026-02", freq="M"): "Fev/2026", pd.Period("2026-03", freq="M"): "Mar/2026"}
    )
    forecast_fig = go.Figure()
    forecast_fig.add_trace(
        go.Bar(
            x=month_labels,
            y=forecast["real"],
            name="Real",
            marker=dict(color=NAVY),
            text=forecast["real"].map(lambda value: format_int(value)),
            textposition="outside",
            hovertemplate="<b>Real</b><br>%{x}: %{y:.0f} unidades<extra></extra>",
        )
    )
    forecast_fig.add_trace(
        go.Bar(
            x=month_labels,
            y=forecast["forecast_rounded"],
            name="Previsto",
            marker=dict(color=BRASS, pattern=dict(shape="/")),
            text=forecast["forecast_rounded"].map(lambda value: format_int(value)),
            textposition="outside",
            customdata=forecast["forecast"],
            hovertemplate=(
                "<b>Previsto</b><br>%{x}: %{y:.0f} unidades arredondadas"
                "<br>Valor antes do arredondamento: %{customdata:.2f}<extra></extra>"
            ),
        )
    )
    style_figure(forecast_fig, height=410)
    forecast_fig.update_layout(barmode="group", bargap=0.28, bargroupgap=0.08)
    forecast_fig.update_xaxes(showgrid=False)
    forecast_fig.update_yaxes(title="Unidades", rangemode="tozero")
    figures["forecast"] = forecast_fig

    returns = data["returns"]["ranking"].sort_values("reembolso")
    return_colors = [STRUCTURAL_BLUE] * len(returns)
    return_colors[-1] = COPPER
    return_hover = [
        f"<b>{row.motivo}</b><br>Reembolsado: {format_brl(row.reembolso)}<br>"
        f"Devoluções: {format_int(row.devolucoes)}"
        for row in returns.itertuples()
    ]
    returns_fig = go.Figure(
        go.Bar(
            x=returns["reembolso"],
            y=returns["motivo"],
            orientation="h",
            marker=dict(color=return_colors),
            text=returns["reembolso"].map(format_compact_brl),
            textposition="outside",
            hovertext=return_hover,
            hovertemplate="%{hovertext}<extra></extra>",
            cliponaxis=False,
        )
    )
    style_figure(returns_fig, height=450)
    returns_fig.update_xaxes(title="Valor reembolsado (R$)", tickformat=".2s")
    returns_fig.update_yaxes(showgrid=False)
    figures["returns"] = returns_fig

    suppliers = data["suppliers"]["ranking"].sort_values("pontualidade", ascending=False)
    supplier_hover = [
        f"<b>{row.rotulo}</b><br>Pontualidade: {format_percent(row.pontualidade)}<br>"
        f"Pedidos concluídos: {format_int(row.pedidos_concluidos)}<br>"
        f"Atraso médio quando houve atraso: {format_decimal_pt(row.atraso_medio_dias, 1)} dias"
        for row in suppliers.itertuples()
    ]
    suppliers_fig = go.Figure(
        go.Bar(
            x=suppliers["pontualidade"] * 100,
            y=suppliers["rotulo"],
            orientation="h",
            marker=dict(color=STRUCTURAL_BLUE),
            text=suppliers["pontualidade"].map(format_percent),
            textposition="outside",
            hovertext=supplier_hover,
            hovertemplate="%{hovertext}<extra></extra>",
            cliponaxis=False,
        )
    )
    style_figure(suppliers_fig, height=470)
    suppliers_fig.add_vline(
        x=data["suppliers"]["overall_on_time"] * 100,
        line_color=BRASS,
        line_dash="dash",
        line_width=2,
        annotation_text=f"Média geral {format_percent(data['suppliers']['overall_on_time'])}",
        annotation_position="top left",
        annotation_font=dict(color=NAVY, family=NUMBER_FONT, size=11),
    )
    suppliers_fig.update_xaxes(title="Pedidos concluídos no prazo", range=[0, 105], ticksuffix="%")
    suppliers_fig.update_yaxes(showgrid=False)
    figures["suppliers"] = suppliers_fig

    recommendations = data["q7"]["ranking"].sort_values("similaridade")
    recommendation_colors = [STRUCTURAL_BLUE] * len(recommendations)
    recommendation_colors[-1] = BRASS
    recommendations_fig = go.Figure(
        go.Bar(
            x=recommendations["similaridade"],
            y=recommendations["name"],
            orientation="h",
            marker=dict(color=recommendation_colors),
            text=recommendations["similaridade"].map(lambda value: f"{value:.4f}"),
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Similaridade: %{x:.6f}<extra></extra>",
            cliponaxis=False,
        )
    )
    style_figure(recommendations_fig, height=390)
    recommendations_fig.update_xaxes(
        title="Similaridade de cosseno",
        range=[0, float(recommendations["similaridade"].max()) * 1.18],
        tickformat=".2f",
    )
    recommendations_fig.update_yaxes(showgrid=False)
    figures["recommendations"] = recommendations_fig

    return figures


PLOT_CONFIG = {
    "responsive": True,
    "displaylogo": False,
    "scrollZoom": False,
    "modeBarButtonsToRemove": [
        "lasso2d",
        "select2d",
        "autoScale2d",
        "toggleSpikelines",
    ],
    "toImageButtonOptions": {"format": "png", "scale": 2},
}


def figure_html(fig: go.Figure, div_id: str, include_plotly: bool) -> str:
    return pio.to_html(
        fig,
        config=PLOT_CONFIG,
        include_plotlyjs="inline" if include_plotly else False,
        full_html=False,
        div_id=div_id,
        validate=True,
    )


def render_table(
    caption: str, headers: list[str], rows: list[list[str]]
) -> str:
    header_html = "".join(f"<th scope=\"col\">{html.escape(value)}</th>" for value in headers)
    row_html = "".join(
        "<tr>"
        + "".join(f"<td>{html.escape(str(value))}</td>" for value in row)
        + "</tr>"
        for row in rows
    )
    return (
        "<div class=\"table-wrap\"><table>"
        f"<caption>{html.escape(caption)}</caption>"
        f"<thead><tr>{header_html}</tr></thead><tbody>{row_html}</tbody>"
        "</table></div>"
    )


def build_tables(data: dict[str, object]) -> dict[str, str]:
    yearly = data["channels"]["yearly"]
    channel_rows = [
        [
            str(int(row.year)),
            format_brl(getattr(row, "ecommerce", 0)),
            format_brl(getattr(row, "pos", 0)),
        ]
        for row in yearly.itertuples()
    ]

    customer_rows = [
        [
            str(int(row.customer_id)),
            format_brl(row.ticket_medio),
            format_int(row.frequencia),
            format_int(row.diversidade_categorias),
        ]
        for row in data["q4"]["top10"].itertuples()
    ]

    weekday_rows = [
        [row.dia_semana, format_brl(row.media_venda), format_int(row.dias)]
        for row in data["q5"]["weekday"].itertuples()
    ]

    forecast_rows = [
        [
            str(row.month),
            format_int(row.real),
            format_decimal_pt(row.forecast, 2),
            format_int(row.forecast_rounded),
            format_decimal_pt(row.absolute_error, 2),
        ]
        for row in data["q6"]["monthly"].itertuples()
    ]

    return_rows = [
        [row.motivo, format_int(row.devolucoes), format_brl(row.reembolso)]
        for row in data["returns"]["ranking"].itertuples()
    ]

    supplier_rows = [
        [
            row.rotulo,
            format_percent(row.pontualidade),
            format_int(row.pedidos_concluidos),
            f"{format_decimal_pt(row.atraso_medio_dias, 1)} dias",
        ]
        for row in data["suppliers"]["ranking"].itertuples()
    ]

    recommendation_rows = [
        [
            str(position),
            row.name,
            f"{row.similaridade:.6f}".replace(".", ","),
        ]
        for position, row in enumerate(data["q7"]["ranking"].itertuples(), start=1)
    ]

    return {
        "channels": render_table(
            "Faturamento anual por canal. O ano de 2026 está parcial até a data de corte.",
            ["Ano", "E-commerce", "Lojas físicas"],
            channel_rows,
        ),
        "customers": render_table(
            "Top 10 clientes fiéis da Q4.",
            ["Customer ID", "Ticket médio", "Pedidos", "Categorias"],
            customer_rows,
        ),
        "weekday": render_table(
            "Venda média POS por dia da semana com calendário completo.",
            ["Dia", "Venda média", "Dias no calendário"],
            weekday_rows,
        ),
        "forecast": render_table(
            "Avaliação walk-forward da Q6.",
            ["Mês", "Real", "Previsto", "Arredondado", "Erro absoluto"],
            forecast_rows,
        ),
        "returns": render_table(
            "Devoluções concluídas por motivo normalizado.",
            ["Motivo", "Devoluções", "Valor reembolsado"],
            return_rows,
        ),
        "suppliers": render_table(
            "Fornecedores com menor pontualidade entre pedidos concluídos.",
            ["Fornecedor", "Pontualidade", "Pedidos", "Atraso médio"],
            supplier_rows,
        ),
        "recommendations": render_table(
            "Top 5 produtos similares ao Motor de Popa 1949.",
            ["Posição", "Produto", "Similaridade"],
            recommendation_rows,
        ),
    }


def build_html(data: dict[str, object]) -> str:
    figures = build_figures(data)
    plots = {
        "channels": figure_html(figures["channels"], "plot-channels", True),
        "customers": figure_html(figures["customers"], "plot-customers", False),
        "weekday": figure_html(figures["weekday"], "plot-weekday", False),
        "forecast": figure_html(figures["forecast"], "plot-forecast", False),
        "returns": figure_html(figures["returns"], "plot-returns", False),
        "suppliers": figure_html(figures["suppliers"], "plot-suppliers", False),
        "recommendations": figure_html(
            figures["recommendations"], "plot-recommendations", False
        ),
    }
    tables = build_tables(data)

    channel_summary = data["channels"]["summary"].set_index("channel")
    ecommerce_ticket = float(channel_summary.loc["ecommerce", "ticket_medio"])
    pos_ticket = float(channel_summary.loc["pos", "ticket_medio"])
    ticket_gap = abs(ecommerce_ticket - pos_ticket)
    forecast_gap = data["q6"]["actual_total"] - data["q6"]["forecast_total"]
    return_leader = data["returns"]["ranking"].iloc[0]
    recommendation_leader = data["q7"]["ranking"].iloc[0]
    best_customer = data["q4"]["top10"].iloc[0]

    page = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Painel executivo do desafio de dados da LH Nautical.">
  <meta name="theme-color" content="{NAVY}">
  <title>Painel Executivo | LH Nautical</title>
  <link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="assets/styles.css">
</head>
<body>
  <a class="skip-link" href="#conteudo">Ir para o conteúdo</a>
  <header class="site-header">
    <nav class="site-nav" aria-label="Navegação principal">
      <a class="brand" href="#topo" aria-label="LH Nautical, voltar ao início">
        <span class="brand-mark" aria-hidden="true">LH</span>
        <span>LH Nautical <small>Painel executivo</small></span>
      </a>
      <div class="nav-links">
        <a href="#visao">Visão</a>
        <a href="#comercial">Comercial</a>
        <a href="#operacao">Operação</a>
        <a href="#oportunidades">Oportunidades</a>
        <a href="#metodologia">Método</a>
      </div>
    </nav>
  </header>

  <main id="conteudo">
    <section class="hero" id="topo" aria-labelledby="hero-title">
      <div class="hero-grid">
        <div class="hero-copy">
          <p class="eyebrow">CARTA ANALÍTICA / EDIÇÃO 01</p>
          <h1 id="hero-title">Dados sólidos para decisões em mar aberto.</h1>
          <p class="hero-lead">Performance comercial, cadência de vendas, demanda, devoluções e fornecedores reunidos em uma leitura executiva da operação LH Nautical.</p>
          <div class="hero-meta">
            <span>Data de corte <strong>{format_date_pt(data['cutoff_day'])}</strong></span>
            <span>Fonte <strong>{format_int(data['raw_table_count'])} tabelas CSV</strong></span>
            <span>Escopo bruto <strong>{format_int(data['raw_row_count'])} registros</strong></span>
          </div>
        </div>
        <div class="instrument-panel" aria-label="Identificação técnica do painel">
          <div class="instrument-ring" aria-hidden="true"><span>N</span><b>03°</b><small>LH / DATA</small></div>
          <p>Leitura estática e auditável. Dados pessoais e arquivos brutos não fazem parte do material publicado.</p>
        </div>
      </div>
    </section>

    <section class="section" id="visao" aria-labelledby="visao-title">
      <div class="section-heading">
        <p class="eyebrow">POSIÇÃO / 00</p>
        <h2 id="visao-title">Visão executiva</h2>
        <p>Os indicadores abaixo conectam performance comercial, ritmo de vendas, suprimentos e experiência do cliente.</p>
      </div>
      <div class="kpi-grid">
        <article class="kpi-card">
          <span class="kpi-code">COM / 01</span>
          <strong>{format_percent(data['channels']['ecommerce_share'])}</strong>
          <h3>Participação do e-commerce</h3>
          <p>No faturamento de pedidos pagos ou confirmados até a data de corte.</p>
        </article>
        <article class="kpi-card kpi-alert">
          <span class="kpi-code">POS / 02</span>
          <strong>{format_compact_brl(data['q5']['worst_average'])}</strong>
          <h3>{data['q5']['worst_day']}</h3>
          <p>Pior média diária nas lojas físicas, incluindo dias sem venda.</p>
        </article>
        <article class="kpi-card">
          <span class="kpi-code">DEM / 03</span>
          <strong>{format_int(data['q6']['forecast_total'])}</strong>
          <h3>Unidades previstas</h3>
          <p>Bússola de Bordo 702 no primeiro trimestre de 2026.</p>
        </article>
        <article class="kpi-card">
          <span class="kpi-code">SUP / 04</span>
          <strong>{format_percent(data['suppliers']['overall_on_time'])}</strong>
          <h3>Entregas no prazo</h3>
          <p>Entre pedidos de compra recebidos até a data de corte.</p>
        </article>
        <article class="kpi-card">
          <span class="kpi-code">RET / 05</span>
          <strong>{format_compact_brl(data['returns']['refund_total'])}</strong>
          <h3>Valor reembolsado</h3>
          <p>Em {format_int(data['returns']['completed_returns'])} devoluções concluídas.</p>
        </article>
      </div>
      <aside class="executive-note">
        <span>LEITURA CENTRAL</span>
        <p>O e-commerce amplia a escala sem elevar significativamente o ticket: a diferença média entre os canais é de apenas {format_brl(ticket_gap)}. Em suprimentos, {format_int(data['suppliers']['late_orders'])} de {format_int(data['suppliers']['completed_orders'])} pedidos recebidos chegaram após a data prometida, com atraso médio de {format_decimal_pt(data['suppliers']['average_late_days'], 1)} dias entre os atrasados.</p>
      </aside>
    </section>

    <section class="section section-tinted" id="comercial" aria-labelledby="comercial-title">
      <div class="section-heading">
        <p class="eyebrow">ROTA / 01</p>
        <h2 id="comercial-title">Performance comercial</h2>
        <p>Volume por canal e comportamento dos clientes fiéis mostram onde a receita ganha escala.</p>
      </div>
      <article class="chart-card chart-wide" aria-labelledby="channels-title">
        <header class="chart-header">
          <span class="reading-code">LEITURA 01</span>
          <h3 id="channels-title">Faturamento mensal por canal</h3>
          <p>O e-commerce concentra {format_percent(data['channels']['ecommerce_share'])} do faturamento operacional. A vantagem vem do volume de pedidos, pois os tickets médios são próximos. Agosto de 2026 é parcial.</p>
        </header>
        <div class="plot-shell">{plots['channels']}</div>
        <details><summary>Ver dados anuais</summary>{tables['channels']}</details>
      </article>

      <div class="chart-grid">
        <article class="chart-card" aria-labelledby="customers-title">
          <header class="chart-header">
            <span class="reading-code">LEITURA 02 / Q4</span>
            <h3 id="customers-title">Clientes fiéis por ticket médio</h3>
            <p>O cliente {int(best_customer['customer_id'])} lidera com ticket médio de {format_brl(best_customer['ticket_medio'])}. O ranking considera apenas clientes com pelo menos 13 categorias.</p>
          </header>
          <div class="plot-shell">{plots['customers']}</div>
          <details><summary>Ver dados do top 10</summary>{tables['customers']}</details>
        </article>
        <aside class="insight-card brass-card">
          <span class="reading-code">CONCENTRAÇÃO / Q4</span>
          <h3>{data['q4']['category']}</h3>
          <strong>{format_int(data['q4']['category_quantity'])} itens</strong>
          <p>É a categoria com maior quantidade comprada pelo grupo específico dos dez clientes fiéis.</p>
          <div class="scale-rule" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></div>
        </aside>
      </div>
    </section>

    <section class="section" id="operacao" aria-labelledby="operacao-title">
      <div class="section-heading">
        <p class="eyebrow">ROTA / 02</p>
        <h2 id="operacao-title">Cadência e risco operacional</h2>
        <p>O calendário completo corrige a leitura das lojas físicas. Previsão e fornecedores revelam onde a operação precisa de margem de segurança.</p>
      </div>
      <div class="chart-grid">
        <article class="chart-card" aria-labelledby="weekday-title">
          <header class="chart-header">
            <span class="reading-code">LEITURA 03 / Q5</span>
            <h3 id="weekday-title">Venda média POS por dia da semana</h3>
            <p>{data['q5']['worst_day']} tem a menor média, {format_brl(data['q5']['worst_average'])}. Todos os dias do calendário entram no denominador, inclusive os zerados.</p>
          </header>
          <div class="plot-shell">{plots['weekday']}</div>
          <details><summary>Ver dados do calendário</summary>{tables['weekday']}</details>
        </article>

        <article class="chart-card" aria-labelledby="forecast-title">
          <header class="chart-header">
            <span class="reading-code">LEITURA 04 / Q6</span>
            <h3 id="forecast-title">Demanda real contra baseline</h3>
            <p>O baseline previu {format_int(data['q6']['forecast_total'])} unidades contra {format_int(data['q6']['actual_total'])} reais, uma diferença de {format_int(forecast_gap)} unidades. MAE: {format_decimal_pt(data['q6']['mae'], 2)}.</p>
          </header>
          <div class="plot-shell">{plots['forecast']}</div>
          <details><summary>Ver previsão mensal</summary>{tables['forecast']}</details>
        </article>
      </div>

      <div class="chart-grid risk-grid">
        <article class="chart-card" aria-labelledby="returns-title">
          <header class="chart-header">
            <span class="reading-code">LEITURA 05 / EXPERIÊNCIA</span>
            <h3 id="returns-title">Reembolsos concluídos por motivo</h3>
            <p>{return_leader['motivo']} é o maior impacto financeiro, com {format_brl(return_leader['reembolso'])}. O valor reembolsado não representa prejuízo líquido.</p>
          </header>
          <div class="plot-shell">{plots['returns']}</div>
          <details><summary>Ver motivos normalizados</summary>{tables['returns']}</details>
        </article>

        <article class="chart-card" aria-labelledby="suppliers-title">
          <header class="chart-header">
            <span class="reading-code">LEITURA 06 / SUPRIMENTOS</span>
            <h3 id="suppliers-title">Fornecedores com menor pontualidade</h3>
            <p>A taxa geral é {format_percent(data['suppliers']['overall_on_time'])}. Atrasos podem contribuir para rupturas, mas este gráfico não prova causalidade.</p>
          </header>
          <div class="plot-shell">{plots['suppliers']}</div>
          <details><summary>Ver ranking de fornecedores</summary>{tables['suppliers']}</details>
        </article>
      </div>
    </section>

    <section class="section section-dark" id="oportunidades" aria-labelledby="oportunidades-title">
      <div class="section-heading light-heading">
        <p class="eyebrow">ROTA / 03</p>
        <h2 id="oportunidades-title">Oportunidades de crescimento</h2>
        <p>A recomendação transforma co-compra em uma vitrine objetiva, preservando as limitações do método.</p>
      </div>
      <div class="opportunity-grid">
        <article class="chart-card dark-chart" aria-labelledby="recommendations-title">
          <header class="chart-header">
            <span class="reading-code">LEITURA 07 / Q7</span>
            <h3 id="recommendations-title">Produtos similares ao Motor de Popa 1949</h3>
            <p>{recommendation_leader['name']} ocupa a primeira posição, com similaridade {float(recommendation_leader['similaridade']):.6f}. A proximidade mede sobreposição de clientes, não afinidade física entre produtos.</p>
          </header>
          <div class="plot-shell">{plots['recommendations']}</div>
          <details><summary>Ver top 5</summary>{tables['recommendations']}</details>
        </article>
        <aside class="recommendation-callout">
          <span class="reading-code">RECOMENDAÇÃO PRINCIPAL</span>
          <strong>01</strong>
          <h3>{recommendation_leader['name']}</h3>
          <p>Similaridade de cosseno</p>
          <b>{float(recommendation_leader['similaridade']):.6f}</b>
          <small>A estabilidade do ranking não foi avaliada.</small>
        </aside>
      </div>
    </section>

    <section class="section methodology" id="metodologia" aria-labelledby="metodologia-title">
      <div class="section-heading">
        <p class="eyebrow">CADERNO DE BORDO</p>
        <h2 id="metodologia-title">Como calculamos</h2>
        <p>Regras explícitas evitam que indicadores com nomes semelhantes representem universos diferentes.</p>
      </div>
      <div class="method-grid">
        <article><span>01</span><h3>Questões do desafio</h3><p>Q4, Q6 e Q7 preservam todos os status, conforme as soluções validadas. Q5 usa somente POS, calendário completo e todos os status.</p></article>
        <article><span>02</span><h3>Explorações comerciais</h3><p>Canais consideram pedidos paid e confirmed até {format_date_pt(data['cutoff_day'])}. Os {format_int(data['future_orders'])} pedidos posteriores ao corte não entram nessa leitura.</p></article>
        <article><span>03</span><h3>Devoluções</h3><p>Somente status completed. Variações de caixa, espaços e erros evidentes de digitação foram agrupadas em motivos canônicos, sem alterar os CSVs.</p></article>
        <article><span>04</span><h3>Fornecedores</h3><p>Somente pedidos com status received e data prometida. A última data de recebimento registrada é comparada à data esperada, ignorando o horário.</p></article>
        <article><span>05</span><h3>Previsão</h3><p>IDs 74 e 240 são agregados pelo nome Bússola de Bordo 702. A avaliação walk-forward usa apenas os três meses anteriores a cada previsão.</p></article>
        <article><span>06</span><h3>Privacidade</h3><p>O HTML contém apenas agregações. CPF, tax ID, e-mail, telefone, endereço, notas fiscais e registros detalhados não são publicados.</p></article>
      </div>
      <p class="source-note">Fonte: 24 arquivos CSV do desafio LH Nautical. Snapshot analítico em {format_date_pt(data['cutoff_day'])}. O período bruto de pedidos contém {format_int(data['raw_order_count'])} registros.</p>
    </section>
  </main>

  <footer>
    <div><span class="brand-mark small" aria-hidden="true">LH</span><p>LH Nautical / Desafio de Dados</p></div>
    <p>Dashboard estático gerado com Python e Plotly.</p>
  </footer>
  <script>
    if (window.location.hash) {{
      window.addEventListener("load", () => {{
        const target = document.getElementById(window.location.hash.slice(1));
        if (target) {{
          window.requestAnimationFrame(() => target.scrollIntoView());
        }}
      }});
    }}
  </script>
</body>
</html>
"""
    return page.replace("\u2014", "-")


def build_dashboard(cutoff_date: str, output: Path) -> dict[str, object]:
    data = build_data(cutoff_date)
    dashboard_html = build_html(data)
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(dashboard_html, encoding="utf-8", newline="\n")
    return data


def main() -> None:
    args = parse_args()
    data = build_dashboard(args.cutoff_date, args.output)
    print(f"Dashboard gerado em: {args.output.resolve()}")
    print(f"Data de corte: {format_date_pt(data['cutoff_day'])}")
    print(
        "Métricas validadas: "
        f"Q4 {data['q4']['category']}={data['q4']['category_quantity']}; "
        f"Q5 {data['q5']['worst_day']}={data['q5']['worst_average']:.2f}; "
        f"Q6 previsão={data['q6']['forecast_total']}, MAE={data['q6']['mae']:.2f}; "
        f"Q7 {data['q7']['ranking'].iloc[0]['name']}"
    )


if __name__ == "__main__":
    main()
