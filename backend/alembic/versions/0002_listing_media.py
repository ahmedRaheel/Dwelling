#!/usr/bin/env python3
"""Repair PropTech Alembic 0002 metadata and duplicate amenities operations.

Run from the repository root: python3 fix_listing_media.py
Creates a timestamped backup and validates the resulting Python source.
"""
from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sys

MIGRATIONS = Path("backend/alembic/versions")
INITIAL = MIGRATIONS / "0001_initial.py"
LISTING = MIGRATIONS / "0002_listing_media.py"
HELPER_NAME = "_proptech_column_exists"
EXPECTED_REVISIONS = {"revision": "0002_listing_media", "down_revision": "0001_initial"}


def string_literal(node: ast.AST) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def operation(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "op":
        return func.attr
    return None


def is_column(node: ast.AST, name: str) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "Column"
        and bool(node.args)
        and string_literal(node.args[0]) == name
    )


def is_amenities_statement(node: ast.stmt, action: str) -> bool:
    if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
        return False
    call = node.value
    if operation(call) != action or len(call.args) < 2 or string_literal(call.args[0]) != "properties":
        return False
    return is_column(call.args[1], "amenities") if action == "add_column" else string_literal(call.args[1]) == "amenities"


def initial_creates_amenities(source: str) -> bool:
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        if operation(node) == "create_table" and node.args and string_literal(node.args[0]) == "properties":
            if any(is_column(arg, "amenities") for arg in node.args[1:]):
                return True
        if operation(node) == "add_column" and len(node.args) > 1 and string_literal(node.args[0]) == "properties":
            if is_column(node.args[1], "amenities"):
                return True
    return False


def get_function(tree: ast.Module, name: str) -> ast.FunctionDef:
    matches = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one {name}() function")
    return matches[0]


def check_metadata(tree: ast.Module) -> list[str]:
    missing = []
    for key, expected in EXPECTED_REVISIONS.items():
        values = []
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == key for t in node.targets):
                values.append(string_literal(node.value))
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == key:
                values.append(string_literal(node.value) if node.value is not None else None)
        if not values:
            missing.append(key)
        elif len(values) != 1 or values[0] != expected:
            raise ValueError(f"Unexpected {key} value {values!r}; expected {expected!r}. Manual review required")
    return missing


def main() -> int:
    if not INITIAL.is_file() or not LISTING.is_file():
        print("ERROR: Run from the repository root containing backend/alembic/versions/", file=sys.stderr)
        return 2
    try:
        initial_source = INITIAL.read_text(encoding="utf-8")
        source = LISTING.read_text(encoding="utf-8")
        tree = ast.parse(source)
        owns = initial_creates_amenities(initial_source)
        upgrade = get_function(tree, "upgrade")
        downgrade = get_function(tree, "downgrade")
        missing = check_metadata(tree)

        adds = [n for n in upgrade.body if is_amenities_statement(n, "add_column")]
        drops = [n for n in downgrade.body if is_amenities_statement(n, "drop_column")]
        if len(adds) > 1 or len(drops) > 1:
            raise ValueError("Multiple direct amenities add/drop operations; review manually")
        if not owns and not adds and HELPER_NAME not in source:
            raise ValueError("0001 does not own amenities, and 0002 has no direct add or existing guard")

        lines = source.splitlines(keepends=True)
        edits: list[tuple[int, int, list[str]]] = []

        def delete_statement(fn: ast.FunctionDef, node: ast.stmt) -> None:
            # Replace a sole statement with pass so the function stays valid.
            if len(fn.body) == 1:
                indentation = " " * (node.col_offset)
                edits.append((node.lineno - 1, node.end_lineno, [indentation + "pass\n"]))
            else:
                edits.append((node.lineno - 1, node.end_lineno, []))

        if adds:
            add = adds[0]
            if owns:
                delete_statement(upgrade, add)
            else:
                indent = " " * add.col_offset
                old = lines[add.lineno - 1:add.end_lineno]
                edits.append((add.lineno - 1, add.end_lineno,
                              [indent + f'if not {HELPER_NAME}("properties", "amenities"):\n']
                              + ["    " + line for line in old]))
        if drops:
            # A downgrade cannot know if the column predated migration 0002.
            delete_statement(downgrade, drops[0])

        for start, end, replacement in sorted(edits, key=lambda e: e[0], reverse=True):
            lines[start:end] = replacement
        updated = "".join(lines)
        ast.parse(updated)

        # Insert metadata and helper immediately before upgrade(), after imports.
        insertion = []
        for key in missing:
            insertion.append(f'{key} = "{EXPECTED_REVISIONS[key]}"\n')
        if missing:
            insertion.append("\n")
        if not owns and adds and HELPER_NAME not in updated:
            insertion.extend([
                "def _proptech_column_exists(table_name: str, column_name: str) -> bool:\n",
                "    from alembic import op\n",
                "    import sqlalchemy as sa\n",
                "    inspector = sa.inspect(op.get_bind())\n",
                "    return any(col['name'] == column_name for col in inspector.get_columns(table_name, schema='public'))\n",
                "\n\n",
            ])
        if insertion:
            new_tree = ast.parse(updated)
            new_upgrade = get_function(new_tree, "upgrade")
            new_lines = updated.splitlines(keepends=True)
            new_lines[new_upgrade.lineno - 1:new_upgrade.lineno - 1] = insertion
            updated = "".join(new_lines)

        final_tree = ast.parse(updated)
        if check_metadata(final_tree):
            raise ValueError("Revision metadata still incomplete")
        get_function(final_tree, "upgrade")
        get_function(final_tree, "downgrade")

        if updated == source:
            print("No change necessary: migration already patched and metadata valid.")
            return 0
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = LISTING.with_name(f"{LISTING.name}.backup-{timestamp}")
        shutil.copy2(LISTING, backup)
        LISTING.write_text(updated, encoding="utf-8")
        print(f"Updated: {LISTING}")
        print(f"Backup:  {backup}")
        print("Review:  git diff -- backend/alembic/versions/0002_listing_media.py")
        return 0
    except (SyntaxError, ValueError) as exc:
        print(f"ERROR: {exc}. No files changed.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
