from pathlib import Path

from sqlalchemy import text

from app.db.postgres import get_engine


def main() -> None:
    sql_path = Path(__file__).resolve().parents[1] / "sql" / "init.sql"
    statements = [
        statement.strip()
        for statement in sql_path.read_text(encoding="utf-8").split(";")
        if statement.strip()
    ]
    engine = get_engine()
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
    print("Initialized Supabase Postgres schema.")


if __name__ == "__main__":
    main()
