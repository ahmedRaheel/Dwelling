"""Non-mutating mapping/schema comparison. Run in backend container: python schema_check.py"""
import asyncio
import json
from sqlalchemy import inspect
from app.core.database import engine, Base
import app.models  # noqa: F401


def inspect_schema(connection):
    inspector = inspect(connection)
    missing = {}
    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name, schema='public'):
            missing[table.name] = {'table_missing': True}
            continue
        present = {c['name'] for c in inspector.get_columns(table.name, schema='public')}
        absent = sorted(set(table.columns.keys()) - present)
        if absent:
            missing[table.name] = {'missing_columns': absent}
    return missing


async def main():
    async with engine.connect() as connection:
        missing = await connection.run_sync(inspect_schema)
    print(json.dumps({'status': 'schema_matches_models' if not missing else 'schema_mismatch', 'differences': missing}, indent=2))
    if missing:
        raise SystemExit(2)


if __name__ == '__main__':
    asyncio.run(main())
