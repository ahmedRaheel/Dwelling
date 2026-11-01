#!/usr/bin/env python3
"""Conservative patch for PropTech Alembic 0002 duplicate amenities column.

Run from repository root: python3 fix_listing_media.py
Uses only Python standard library; leaves a timestamped backup.
"""
from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sys

MIGRATIONS = Path('backend/alembic/versions')
INITIAL = MIGRATIONS / '0001_initial.py'
LISTING = MIGRATIONS / '0002_listing_media.py'
HELPER_NAME = '_proptech_column_exists'


def literal_str(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def op_name(node: ast.Call) -> str | None:
    f = node.func
    if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == 'op':
        return f.attr
    return None


def column_name(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
        return None
    if node.func.attr != 'Column' or not node.args:
        return None
    return literal_str(node.args[0])


def is_amenities_op(node: ast.AST, action: str) -> bool:
    if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
        return False
    call = node.value
    if op_name(call) != action or len(call.args) < 2 or literal_str(call.args[0]) != 'properties':
        return False
    if action == 'add_column':
        return column_name(call.args[1]) == 'amenities'
    return literal_str(call.args[1]) == 'amenities'


def initial_owns_column(source: str) -> bool:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        action = op_name(node)
        if action == 'create_table' and node.args and literal_str(node.args[0]) == 'properties':
            if any(column_name(arg) == 'amenities' for arg in node.args[1:]):
                return True
        if action == 'add_column' and len(node.args) > 1 and literal_str(node.args[0]) == 'properties':
            if column_name(node.args[1]) == 'amenities':
                return True
    return False


def statements_in_function(tree: ast.Module, name: str) -> list[ast.stmt]:
    functions = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    if len(functions) != 1:
        raise ValueError(f'Expected exactly one {name}() function.')
    return functions[0].body


def insert_helper(source: str) -> str:
    if HELPER_NAME in source:
        return source
    helper = '''\n\ndef _proptech_column_exists(table_name: str, column_name: str) -> bool:\n    from alembic import op\n    import sqlalchemy as sa\n\n    inspector = sa.inspect(op.get_bind())\n    return any(\n        column["name"] == column_name\n        for column in inspector.get_columns(table_name, schema="public")\n    )\n'''
    tree = ast.parse(source)
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'upgrade']
    if len(funcs) != 1:
        raise ValueError('Missing or ambiguous upgrade() function')
    lines = source.splitlines(keepends=True)
    loc = funcs[0].lineno - 1
    lines.insert(loc, helper + '\n')
    return ''.join(lines)


def main() -> int:
    if not INITIAL.is_file() or not LISTING.is_file():
        print('ERROR: Run this in the PropTech repository root containing backend/alembic/versions/', file=sys.stderr)
        return 2

    initial = INITIAL.read_text(encoding='utf-8')
    original = LISTING.read_text(encoding='utf-8')
    tree = ast.parse(original)
    owns = initial_owns_column(initial)
    upgrades = [n for n in statements_in_function(tree, 'upgrade') if is_amenities_op(n, 'add_column')]
    if len(upgrades) != 1:
        print(f'ERROR: Expected exactly one direct amenities add_column in 0002 upgrade(), found {len(upgrades)}. No changes made.', file=sys.stderr)
        return 2
    downgrade_ops = [n for n in statements_in_function(tree, 'downgrade') if is_amenities_op(n, 'drop_column')]
    if len(downgrade_ops) > 1:
        print('ERROR: Multiple amenities drop operations; no changes made.', file=sys.stderr)
        return 2

    lines = original.splitlines(keepends=True)
    add = upgrades[0]
    indent = lines[add.lineno - 1][:len(lines[add.lineno - 1]) - len(lines[add.lineno - 1].lstrip())]
    if not indent:
        print('ERROR: add_column not indented inside upgrade(); no changes made.', file=sys.stderr)
        return 2

    replacements: list[tuple[int, int, list[str]]] = []
    if owns:
        replacements.append((add.lineno - 1, add.end_lineno, []))
        if downgrade_ops:
            drop = downgrade_ops[0]
            replacements.append((drop.lineno - 1, drop.end_lineno, []))
        print('0001_initial already defines properties.amenities; removing duplicate add/drop from 0002.')
    else:
        original_stmt = lines[add.lineno - 1:add.end_lineno]
        wrapped = [indent + f'if not {HELPER_NAME}("properties", "amenities"):\n']
        wrapped.extend('    ' + line for line in original_stmt)
        replacements.append((add.lineno - 1, add.end_lineno, wrapped))
        # Do not drop a potentially pre-existing column when downgrading.
        if downgrade_ops:
            drop = downgrade_ops[0]
            replacements.append((drop.lineno - 1, drop.end_lineno, []))
        print('0001_initial does not declare amenities; adding an existence guard to 0002.')

    for start, end, replacement in sorted(replacements, reverse=True):
        lines[start:end] = replacement
    updated = ''.join(lines)
    if not owns:
        updated = insert_helper(updated)
    ast.parse(updated)

    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup = LISTING.with_name(LISTING.name + f'.backup-{timestamp}')
    shutil.copy2(LISTING, backup)
    LISTING.write_text(updated, encoding='utf-8')
    print(f'Patched: {LISTING}')
    print(f'Backup:  {backup}')
    print('Review diff: git diff -- backend/alembic/versions/0002_listing_media.py')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
