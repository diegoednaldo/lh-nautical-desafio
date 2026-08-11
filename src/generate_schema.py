"""
Questão 2 - Geração do schema.sql

Lê todos os CSVs de um diretório e gera um único arquivo schema.sql com
instruções CREATE TABLE para um banco PostgreSQL de destino.

Restrições obrigatórias (ver documentação do desafio):
- Apenas bibliotecas padrão do Python 3 (csv, os, datetime, etc.)
- Proibido usar pandas, dask, polars ou similares
- Banco de destino: PostgreSQL

TODO: implementar a lógica de:
  1. Varrer o diretório de CSVs (data/raw/lh_nautical_csv/)
  2. Para cada CSV, ler o cabeçalho e uma amostra de linhas
  3. Inferir o tipo de dado de cada coluna (texto, inteiro, decimal, data, etc.)
  4. Montar o CREATE TABLE correspondente
  5. Escrever tudo em sql/schema.sql
"""
import csv
import os

RAW_DATA_DIR = os.path.join("data", "raw", "lh_nautical_csv")
OUTPUT_SCHEMA_PATH = os.path.join("sql", "schema.sql")


def list_csv_files(directory: str) -> list[str]:
    """Retorna a lista de arquivos .csv no diretório informado."""
    raise NotImplementedError


def infer_column_type(sample_values: list[str]) -> str:
    """Infere o tipo PostgreSQL (INTEGER, NUMERIC, TEXT, TIMESTAMP, etc.)
    a partir de uma amostra de valores de uma coluna."""
    raise NotImplementedError


def build_create_table_statement(table_name: str, csv_path: str) -> str:
    """Monta a instrução CREATE TABLE para um CSV específico."""
    raise NotImplementedError


def main():
    csv_files = list_csv_files(RAW_DATA_DIR)
    statements = []

    for csv_path in csv_files:
        table_name = os.path.splitext(os.path.basename(csv_path))[0]
        statements.append(build_create_table_statement(table_name, csv_path))

    os.makedirs(os.path.dirname(OUTPUT_SCHEMA_PATH), exist_ok=True)
    with open(OUTPUT_SCHEMA_PATH, "w", encoding="utf-8") as f:
        f.write("\n\n".join(statements))

    print(f"Schema gerado em: {OUTPUT_SCHEMA_PATH}")


if __name__ == "__main__":
    main()
