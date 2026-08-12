-- Questão 4.1 - Análise de clientes fiéis

-- CTE 1: Faturamento total, frequência e ticket médio por cliente (nível orders)
WITH customer_metrics AS (
    SELECT
        customer_id,
        SUM(total)                              AS faturamento_total,
        COUNT(id)                               AS frequencia,
        ROUND(SUM(total) / COUNT(id), 2)        AS ticket_medio
    FROM orders
    GROUP BY customer_id
),

-- CTE 2: Diversidade de categorias distintas compradas por cliente
customer_categories AS (
    SELECT
        o.customer_id,
        COUNT(DISTINCT p.category_id) AS diversidade_categorias
    FROM orders o
    JOIN order_items oi      ON oi.order_id = o.id
    JOIN product_variants pv ON pv.id = oi.product_variant_id
    JOIN products p          ON p.id = pv.product_id
    GROUP BY o.customer_id
),

-- CTE 3: Top 10 clientes fiéis (>= 13 categorias, maior ticket médio,
-- desempate por customer_id crescente)
top10_clientes_fieis AS (
    SELECT
        cm.customer_id,
        cm.faturamento_total,
        cm.frequencia,
        cm.ticket_medio,
        cc.diversidade_categorias
    FROM customer_metrics cm
    JOIN customer_categories cc ON cc.customer_id = cm.customer_id
    WHERE cc.diversidade_categorias >= 13
    ORDER BY cm.ticket_medio DESC, cm.customer_id ASC
    LIMIT 10
)

SELECT * FROM top10_clientes_fieis;


-- Questão 4 (parte 3) - Categoria com maior soma de itens (quantity)
-- entre os 10 clientes fiéis identificados acima
WITH customer_metrics AS (
    SELECT
        customer_id,
        SUM(total)                        AS faturamento_total,
        COUNT(id)                         AS frequencia,
        ROUND(SUM(total) / COUNT(id), 2)  AS ticket_medio
    FROM orders
    GROUP BY customer_id
),
customer_categories AS (
    SELECT
        o.customer_id,
        COUNT(DISTINCT p.category_id) AS diversidade_categorias
    FROM orders o
    JOIN order_items oi      ON oi.order_id = o.id
    JOIN product_variants pv ON pv.id = oi.product_variant_id
    JOIN products p          ON p.id = pv.product_id
    GROUP BY o.customer_id
),
top10_clientes_fieis AS (
    SELECT cm.customer_id, cm.ticket_medio, cc.diversidade_categorias
    FROM customer_metrics cm
    JOIN customer_categories cc ON cc.customer_id = cm.customer_id
    WHERE cc.diversidade_categorias >= 13
    ORDER BY cm.ticket_medio DESC, cm.customer_id ASC
    LIMIT 10
)
SELECT
    cat.name              AS categoria,
    SUM(oi.quantity)       AS total_itens_comprados
FROM top10_clientes_fieis t
JOIN orders o             ON o.customer_id = t.customer_id
JOIN order_items oi       ON oi.order_id = o.id
JOIN product_variants pv  ON pv.id = oi.product_variant_id
JOIN products p           ON p.id = pv.product_id
JOIN categories cat       ON cat.id = p.category_id
GROUP BY cat.name
ORDER BY total_itens_comprados DESC
LIMIT 1;