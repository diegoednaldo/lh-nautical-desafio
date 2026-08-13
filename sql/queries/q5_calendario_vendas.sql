-- Questão 5.1 - Dimensão de calendário + vendas por dia da semana (lojas físicas)

WITH calendario AS (
    SELECT generate_series(
        (SELECT MIN(created_at)::date FROM orders),
        CURRENT_DATE,
        '1 day'::interval
    )::date AS data
),

vendas_pos AS (
    SELECT
        created_at::date AS data,
        SUM(total)        AS venda_dia
    FROM orders
    WHERE channel = 'pos'
    GROUP BY created_at::date
),

calendario_vendas AS (
    SELECT
        c.data,
        COALESCE(v.venda_dia, 0) AS venda_dia,
        CASE EXTRACT(DOW FROM c.data)
            WHEN 0 THEN 'Domingo'
            WHEN 1 THEN 'Segunda-feira'
            WHEN 2 THEN 'Terça-feira'
            WHEN 3 THEN 'Quarta-feira'
            WHEN 4 THEN 'Quinta-feira'
            WHEN 5 THEN 'Sexta-feira'
            WHEN 6 THEN 'Sábado'
        END AS dia_semana
    FROM calendario c
    LEFT JOIN vendas_pos v ON v.data = c.data
)

SELECT
    dia_semana,
    ROUND(AVG(venda_dia), 2) AS media_venda,
    COUNT(*)                 AS qtd_dias_no_calendario
FROM calendario_vendas
GROUP BY dia_semana
ORDER BY media_venda ASC;
