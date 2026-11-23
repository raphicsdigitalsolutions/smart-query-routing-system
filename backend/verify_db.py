from sqlalchemy import create_engine, text
import os

engine = create_engine(os.environ["DATABASE_URL"])

with engine.connect() as conn:
    print("DATABASE TABLES:")

    result = conn.execute(text(
        "SELECT tablename FROM pg_catalog.pg_tables "
        "WHERE schemaname = 'public' ORDER BY tablename"
    ))

    for row in result:
        print("-", row[0])

    revision_table = conn.execute(text(
        "SELECT to_regclass('public.alembic_version')"
    )).scalar()

    print("ALEMBIC VERSION TABLE:", revision_table)

    if revision_table:
        revision = conn.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one_or_none()
        print("CURRENT REVISION:", revision)

engine.dispose()
