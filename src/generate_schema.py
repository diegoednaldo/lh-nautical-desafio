"""
Questão 2 - Geração do schema.sql

Lê todos os CSVs de um diretório e gera um único arquivo schema.sql com
instruções CREATE TABLE para um banco PostgreSQL de destino.

Restrições obrigatórias:
- Apenas bibliotecas padrão do Python 3 (csv, os, datetime, etc.)
- Proibido usar pandas, dask, polars ou similares
- Banco de destino: PostgreSQL
"""
import csv
import os
from datetime import datetime

RAW_DATA_DIR = os.path.join("data", "raw")
OUTPUT_SCHEMA_PATH = os.path.join("sql", "schema.sql")

INTEGER_MAX = 2_147_483_647
BIGINT_MAX = 9_223_372_036_854_775_807


def list_csv_files(directory: str) -> list[str]:
    """Retorna a lista de arquivos .csv no diretório informado, ordenada."""
    return sorted(
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.endswith(".csv")
    )


def _is_plain_integer_string(value: str) -> bool:
    """True se o valor é uma sequência de dígitos (com sinal opcional),
    sem separadores nem ponto decimal."""
    v = value.strip()
    if v and v[0] in "+-":
        v = v[1:]
    return v.isdigit()


def _has_leading_zero(value: str) -> bool:
    """True se o valor tem zero à esquerda (ex: '0812356442423', '06100715800').
    Nesse caso o campo é um identificador/código, não uma quantidade numérica,
    e convertê-lo para INTEGER/BIGINT perderia esse zero, corrompendo o dado.
    """
    v = value.strip().lstrip("+-")
    return len(v) > 1 and v[0] == "0"


def _is_float(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def _is_bool(value: str) -> bool:
    return value.strip().upper() in ("TRUE", "FALSE")


def _is_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _is_timestamp(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        return True
    except ValueError:
        return False


def infer_column_type(sample_values: list[str]) -> str:
    """Infere o tipo PostgreSQL a partir dos valores de uma coluna.

    Estratégia: percorre os candidatos do mais específico para o mais genérico
    (BOOLEAN -> TIMESTAMP -> DATE -> INTEGER/BIGINT -> NUMERIC -> TEXT).
    Valores vazios são ignorados (tratados como NULL). Números com zero à
    esquerda são tratados como TEXT (identificadores como telefone/EAN, não
    quantidades) para não perder informação na conversão.
    """
    non_empty = [v for v in sample_values if v is not None and v.strip() != ""]

    if not non_empty:
        return "TEXT"

    if all(_is_bool(v) for v in non_empty):
        return "BOOLEAN"

    if all(_is_timestamp(v) for v in non_empty):
        return "TIMESTAMP"

    if all(_is_date(v) for v in non_empty):
        return "DATE"

    if all(_is_plain_integer_string(v) for v in non_empty):
        if any(_has_leading_zero(v) for v in non_empty):
            return "TEXT"

        max_abs = max(abs(int(v)) for v in non_empty)
        if max_abs <= INTEGER_MAX:
            return "INTEGER"
        if max_abs <= BIGINT_MAX:
            return "BIGINT"
        return "TEXT"  # grande demais até para BIGINT (ex: chave de NF-e)

    if all(_is_float(v) for v in non_empty):
        return "NUMERIC"

    return "TEXT"


def build_create_table_statement(table_name: str, csv_path: str) -> str:
    """Monta a instrução CREATE TABLE para um CSV específico."""
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)

        # Percorre o arquivo inteiro (não só uma amostra) para que colunas
        # majoritariamente vazias no início não sejam mal classificadas.
        samples = {col: [] for col in header}
        for row in reader:
            for col, value in zip(header, row):
                samples[col].append(value)

    columns_sql = []
    for col in header:
        col_type = infer_column_type(samples[col])
        # heurística simples: coluna "id" isolada vira PK
        if col == "id":
            columns_sql.append(f'    "{col}" {col_type} PRIMARY KEY')
        else:
            columns_sql.append(f'    "{col}" {col_type}')

    columns_block = ",\n".join(columns_sql)
    return f'CREATE TABLE IF NOT EXISTS "{table_name}" (\n{columns_block}\n);'


def main():
    csv_files = list_csv_files(RAW_DATA_DIR)
    statements = []

    for csv_path in csv_files:
        table_name = os.path.splitext(os.path.basename(csv_path))[0]
        statements.append(build_create_table_statement(table_name, csv_path))
        print(f"Processado: {table_name}")

    os.makedirs(os.path.dirname(OUTPUT_SCHEMA_PATH), exist_ok=True)
    with open(OUTPUT_SCHEMA_PATH, "w", encoding="utf-8") as f:
        header = (
            "-- Gerado automaticamente por src/generate_schema.py (Questão 2)\n"
            "-- Não editar manualmente: rode o script novamente para regenerar.\n\n"
        )
        f.write(header + "\n\n".join(statements) + "\n")

    print(f"\nSchema gerado em: {OUTPUT_SCHEMA_PATH}")


if __name__ == "__main__":
    main()