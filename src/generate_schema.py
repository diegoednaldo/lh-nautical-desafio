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

# Acima disso, um número inteiro não cabe nem em BIGINT (limite ~19 dígitos).
# Colunas assim são identificadores longos (ex: chave de acesso de NF-e),
# não quantidades, então tratamos como TEXT.
MAX_INTEGER_DIGITS = 18


def list_csv_files(directory: str) -> list[str]:
    """Retorna a lista de arquivos .csv no diretório informado, ordenada."""
    return sorted(
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.endswith(".csv")
    )


def _is_int(value: str) -> bool:
    stripped = value.strip().lstrip("-")
    if not stripped.isdigit():
        return False
    if len(stripped) > MAX_INTEGER_DIGITS:
        return False
    return True


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
    """Infere o tipo PostgreSQL a partir de uma amostra de valores de uma coluna.

    Estratégia: percorre os candidatos do mais específico para o mais genérico
    (BOOLEAN -> TIMESTAMP -> DATE -> INTEGER -> NUMERIC -> TEXT). Valores vazios
    são ignorados na inferência (tratados como NULL). Se não sobrar nenhum valor
    não-vazio, assume TEXT.
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

    if all(_is_int(v) for v in non_empty):
        return "INTEGER"

    # Sequência de dígitos longa demais para INTEGER/BIGINT (ex: chave de
    # acesso de NF-e): é um identificador, não uma quantidade -> TEXT,
    # mesmo que tecnicamente "parseável" como NUMERIC.
    if all(v.strip().lstrip("-").isdigit() for v in non_empty):
        return "TEXT"

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