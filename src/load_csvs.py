"""
Questão 3 - Carregamento dos CSVs no Postgres

Carrega todos os CSVs de data/raw/ nas tabelas criadas
pelo schema.sql (Questão 2), sem nenhum tratamento de dados (sem remoção
de nulos, sem correção de caracteres especiais).

Usa COPY (via psycopg2.copy_expert), que é a forma mais rápida de carga
em massa no Postgres e já trata célula vazia como NULL automaticamente,
sem precisar de nenhuma lógica de limpeza manual.
"""
import csv
import os

if __package__:
    from .db import get_psycopg2_connection
else:
    from db import get_psycopg2_connection

RAW_DATA_DIR = os.path.join("data", "raw")


def list_csv_files(directory: str) -> list[str]:
    """Retorna a lista de arquivos .csv no diretório informado, ordenada."""
    return sorted(f for f in os.listdir(directory) if f.endswith(".csv"))


def get_csv_header(csv_path: str) -> list[str]:
    """Lê apenas o cabeçalho do CSV, para montar a lista de colunas do COPY
    explicitamente (evita depender da ordem das colunas do schema.sql)."""
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        return next(reader)


def find_nonempty_tables(conn, csv_files: list[str]) -> list[str]:
    """Retorna as tabelas de destino que já possuem ao menos uma linha."""
    nonempty_tables = []

    with conn.cursor() as cur:
        for csv_file in csv_files:
            table_name = os.path.splitext(csv_file)[0]
            cur.execute(f'SELECT EXISTS (SELECT 1 FROM "{table_name}" LIMIT 1)')
            if cur.fetchone()[0]:
                nonempty_tables.append(table_name)

    return nonempty_tables


def load_csv_to_table(conn, csv_path: str, table_name: str) -> int:
    """Carrega um CSV em uma tabela via COPY e retorna a quantidade de linhas inseridas."""
    columns = get_csv_header(csv_path)
    columns_sql = ", ".join(f'"{col}"' for col in columns)

    copy_sql = (
        f'COPY "{table_name}" ({columns_sql}) '
        f"FROM STDIN WITH (FORMAT csv, HEADER true, DELIMITER ',')"
    )

    with conn.cursor() as cur:
        with open(csv_path, newline="", encoding="utf-8") as f:
            cur.copy_expert(copy_sql, f)
        cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
        row_count = cur.fetchone()[0]

    conn.commit()
    return row_count


def main():
    conn = get_psycopg2_connection()
    try:
        csv_files = list_csv_files(RAW_DATA_DIR)
        print(f"Encontrados {len(csv_files)} arquivos CSV para carregar.\n")

        nonempty_tables = find_nonempty_tables(conn, csv_files)
        if nonempty_tables:
            print("Carga não executada: o banco já possui dados nas tabelas:")
            print(", ".join(nonempty_tables))
            return

        for csv_file in csv_files:
            table_name = os.path.splitext(csv_file)[0]
            csv_path = os.path.join(RAW_DATA_DIR, csv_file)
            rows_loaded = load_csv_to_table(conn, csv_path, table_name)
            print(f"{table_name}: {rows_loaded} linhas carregadas")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
