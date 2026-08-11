-- Questão 1.1 - EDA da tabela orders (SQL)
-- Sem tratamento: apenas observação e agregação

SELECT
    COUNT(*)                       AS total_linhas,
    MIN(created_at)                AS data_minima,
    MAX(created_at)                AS data_maxima,
    MIN(total)                     AS valor_minimo,
    MAX(total)                     AS valor_maximo,
    ROUND(AVG(total), 2)           AS valor_medio
FROM orders;