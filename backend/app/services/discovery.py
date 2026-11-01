"""Search refinement, agency directory, saved searches and visit scheduling.

Revision ID: 0003_discovery_workspace
Revises: 0002_listing_media

This migration tolerates objects already created by an earlier revision, but
refuses to silently accept incompatible column definitions or missing tables.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_discovery_workspace"
down_revision = "0002_listing_media"
branch_labels = None
depends_on = None

SCHEMA = "public"


def _inspector():
    return sa.inspect(op.get_bind())


def _table_exists(table):
    return _inspector().has_table(table, schema=SCHEMA)


def _columns(table):
    if not _table_exists(table):
        raise RuntimeError(f"Required table {SCHEMA}.{table} does not exist")
    return {col["name"]: col for col in _inspector().get_columns(table, schema=SCHEMA)}


def _add_column(table, column):
    columns = _columns(table)
    existing = columns.get(column.name)
    if existing is None:
        op.add_column(table, column, schema=SCHEMA)
        return

    # A name collision is not proof of a compatible schema. Confirm the
    # basic PostgreSQL type and nullability before accepting the column.
    expected_type = column.type.compile(dialect=postgresql.dialect()).lower()
    found_type = existing["type"].compile(dialect=postgresql.dialect()).lower()
    aliases = {
        "boolean": {"boolean", "bool"},
        "text": {"text"},
    }
    allowed = aliases.get(expected_type, {expected_type})
    if found_type not in allowed or existing["nullable"] != column.nullable:
        raise RuntimeError(
            f"Existing {table}.{column.name} differs from migration: "
            f"found {found_type}, nullable={existing['nullable']}; "
            f"expected {expected_type}, nullable={column.nullable}. "
            "Review and reconcile manually before proceeding."
        )


def _create_index(name, table, columns):
    indexes = {index["name"]: index for index in _inspector().get_indexes(table, schema=SCHEMA)}
    existing = indexes.get(name)
    if existing is None:
        op.create_index(name, table, columns, schema=SCHEMA)
    elif existing["column_names"] != columns or existing.get("unique", False):
        raise RuntimeError(f"Existing index {name} has an unexpected definition")


def _create_check(name, table, expression):
    checks = {item["name"]: item for item in _inspector().get_check_constraints(table, schema=SCHEMA)}
    if name not in checks:
        op.create_check_constraint(name, table, expression, schema=SCHEMA)
    else:
        # Merely matching the constraint name does not establish equivalence.
        # Compare the normalized condition for the one expected constraint.
        found = "".join(checks[name]["sqltext"].lower().split())
        expected_values = ("gallery", "floorplan")
        if not all(value in found for value in expected_values) or "category" not in found:
            raise RuntimeError(f"Existing check {name} needs manual review: {checks[name]['sqltext']}")


def _create_table_if_missing(name, *columns):
    if not _table_exists(name):
        op.create_table(name, *columns, schema=SCHEMA)
    else:
        actual = _columns(name)
        expected_names = {column.name for column in columns if isinstance(column, sa.Column)}
        if not expected_names.issubset(actual):
            missing = sorted(expected_names - actual.keys())
            raise RuntimeError(f"Existing table {name} lacks required columns: {missing}")
        # Existing tables with matching names require further schema validation.
        # Guard against silently accepting missing tenant/RLS-critical constraints.
        expected_pk = [c.name for c in columns if isinstance(c, sa.Column) and c.primary_key]
        primary = _inspector().get_pk_constraint(name, schema=SCHEMA)
        if sorted(primary.get("constrained_columns") or []) != sorted(expected_pk):