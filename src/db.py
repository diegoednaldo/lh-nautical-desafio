"""
Módulo central de conexão com o Postgres.
Usado tanto pelos scripts em src/ quanto pelos notebooks em notebooks/.
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "lh_nautical")
DB_USER = os.getenv("DB_USER", "lh_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "lh_password")


def get_connection_string() -> str:
    return f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def get_engine():
    """Retorna uma SQLAlchemy engine pronta para uso (ex: pd.read_sql)."""
    return create_engine(get_connection_string())


def get_psycopg2_connection():
    """Retorna uma conexão psycopg2 pura, útil para scripts de carga (Questão 3)."""
    import psycopg2

    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )
