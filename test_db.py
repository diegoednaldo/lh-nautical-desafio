from sqlalchemy import text
from src.db import get_engine

engine = get_engine()

with engine.connect() as connection:
    result = connection.execute(text("SELECT 1"))
    print(result.fetchone())