"""
Questão 3 - Carregamento dos CSVs no Postgres

Carrega todos os CSVs de data/raw/lh_nautical_csv/ nas tabelas criadas
pelo schema.sql (Questão 2), sem nenhum tratamento de dados (sem remoção
de nulos, sem correção de caracteres especiais).

Restrições obrigatórias (ver documentação do desafio):
- Executar após o schema.sql ter sido aplicado no banco
- Qualquer biblioteca pode ser usada para a carga (nativa ou externa)
- Não tratar/limpar os dados nesta etapa

TODO: implementar a lógica de:
  1. Conectar ao Postgres (usar src/db.py)
  2. Para cada CSV, carregar os dados na tabela correspondente
     (ex: via psycopg2 COPY, que é o método mais rápido para cargas grandes)
  3. Validar a quantidade de linhas carregadas por tabela
"""
import os

from src.db import get_psycopg2_connection

RAW_DATA_DIR = os.path.join("data", "raw", "lh_nautical_csv")


def load_csv_to_table(conn, csv_path: str, table_name: str) -> int:
    """Carrega um CSV em uma tabela via COPY e retorna a quantidade de linhas inseridas."""
    raise NotImplementedError


def main():
    conn = get_psycopg2_connection()

    csv_files = [f for f in os.listdir(RAW_DATA_DIR) if f.endswith(".csv")]

    for csv_file in csv_files:
        table_name = os.path.splitext(csv_file)[0]
        csv_path = os.path.join(RAW_DATA_DIR, csv_file)
        rows_loaded = load_csv_to_table(conn, csv_path, table_name)
        print(f"{table_name}: {rows_loaded} linhas carregadas")

    conn.close()


if __name__ == "__main__":
    main()
