#!/usr/bin/env python3
"""Guarded repair for a missing property_photos table in PropTech migration 0002.

Run at repository root: python3 repair_0002_photos.py
This changes *source only*, backs it up, and requires the existing ORM table
mapping to define the schema. It never modifies PostgreSQL directly.
"""
from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sys

ROOT = Path.cwd()
TARGET = ROOT / 'backend/alembic/versions/0002_listing_media.py'
INITIAL = ROOT / 'backend/alembic/versions/0001_initial.py'
MARKER = '# PROPTECH_PHOTO_SCHEMA_REPAIR_V1'


def assignments(tree: ast.Module, name: str) -> list[str | None]:
    result = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            result.append(node.value.value if isinstance(node.value, ast.Constant) else None)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            result.append(node.value.value if isinstance(node.value, ast.Constant) else None)
    return result


def main() -> int:
    if not TARGET.exists() or not INITIAL.exists():
        print('Missing migration source: run at ~/Dwelling and ensure 0001 and 0002 exist.', file=sys.stderr)
        return 2
    source = TARGET.read_text(encoding='utf-8')
    tree = ast.parse(source)
    upgrades = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'upgrade']
    downgrades = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'downgrade']
    if len(upgrades) != 1 or len(downgrades) != 1:
        print('0002 is not a valid migration with one upgrade and downgrade. Restore original.', file=sys.stderr)
        return 2
    if MARKER in source:
        print('Already patched; no changes made.')
        return 0
    revisions = assignments(tree, 'revision')
    parents = assignments(tree, 'down_revision')
    if revisions not in ([], ['0002_listing_media']) or parents not in ([], ['0001_initial']):
        print('Conflicting revision metadata; refusing to change.', file=sys.stderr)
        return 2
    # If 0002 explicitly creates the table, the cause is different: do not double-create.
    for node in ast.walk(upgrades[0]):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != 'create_table' or not isinstance(node.func.value, ast.Name) or node.func.value.id != 'op':
            continue
        if node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == 'property_photos':
            print('0002 already creates property_photos. Inspect execution and database URL instead of patching.', file=sys.stderr)
            return 2
    # This hook creates the precise mapped table rather than guessing column definitions.
    # It also fails closed if the ORM mapping does not include tenant_id and property_id.
    block = '''    # PROPTECH_PHOTO_SCHEMA_REPAIR_V1
    # Recover 0002's required gallery table using the application's mapped schema.
    # IMPORTANT: Replace this recovery hook with a frozen explicit migration after
    # checking the final schema against the original release.
    from app.core.database import Base
    import app.models  # noqa: F401; ensure mappings are registered
    from sqlalchemy import inspect, text
    photo_table = Base.metadata.tables.get("property_photos")
    if photo_table is None:
        raise RuntimeError("ORM is missing property_photos mapping; restore original 0002 migration")
    if not {"tenant_id", "property_id"}.issubset(photo_table.columns.keys()):
        raise RuntimeError("property_photos ORM mapping lacks tenant_id/property_id; manual migration needed")
    photo_table.create(bind=op.get_bind(), checkfirst=True)
    op.execute("ALTER TABLE public.property_photos ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.property_photos FORCE ROW LEVEL SECURITY")
    photo_policy_rows = op.get_bind().execute(text(
        "SELECT policyname FROM pg_policies WHERE schemaname='public' AND tablename='property_photos'"
    )).all()
    if not photo_policy_rows:
        photo_tid = "nullif(current_setting('app.tenant_id', true), '')::uuid"
        op.execute(f"CREATE POLICY photo_select ON public.property_photos FOR SELECT USING (tenant_id = {photo_tid} OR EXISTS (SELECT 1 FROM public.properties p WHERE p.id = property_id AND p.status = 'published'))")
        op.execute(f"CREATE POLICY photo_insert ON public.property_photos FOR INSERT WITH CHECK (tenant_id = {photo_tid} AND EXISTS (SELECT 1 FROM public.properties p WHERE p.id = property_id AND p.tenant_id = {photo_tid}))")
        op.execute(f"CREATE POLICY photo_update ON public.property_photos FOR UPDATE USING (tenant_id = {photo_tid}) WITH CHECK (tenant_id = {photo_tid} AND EXISTS (SELECT 1 FROM public.properties p WHERE p.id = property_id AND p.tenant_id = {photo_tid}))")
        op.execute(f"CREATE POLICY photo_delete ON public.property_photos FOR DELETE USING (tenant_id = {photo_tid})")
    else:
        raise RuntimeError("Existing property_photos RLS policies require manual security review")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON public.property_photos TO proptech_app")
'''
    lines = source.splitlines(keepends=True)
    fn = upgrades[0]
    # Insert at beginning of upgrade, after any existing docstring.
    insert_at = fn.body[0].end_lineno if (fn.body and isinstance(fn.body[0], ast.Expr) and isinstance(fn.body[0].value, ast.Constant) and isinstance(fn.body[0].value.value, str)) else fn.body[0].lineno - 1
    lines.insert(insert_at, block)
    updated = ''.join(lines)
    missing = []
    if not revisions: missing.append('revision = "0002_listing_media"\n')
    if not parents: missing.append('down_revision = "0001_initial"\n')
    if missing:
        updated = ''.join(missing) + updated  # valid if original module has no __future__ import
        # Reposition after module docstring/imports if needed.
        t2 = ast.parse(updated)
        if any(isinstance(n, ast.ImportFrom) and n.module == '__future__' for n in t2.body):
            raise RuntimeError('File has future imports and missing revision metadata; add metadata manually')
    compile(updated, str(TARGET), 'exec')
    date = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup = TARGET.with_name(TARGET.name + '.backup-' + date)
    shutil.copy2(TARGET, backup)
    TARGET.write_text(updated, encoding='utf-8')
    print('Updated', TARGET)
    print('Backup ', backup)
    print('IMPORTANT: This is a provisional model-derived schema recovery. Check full 0002 and integration tests.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
