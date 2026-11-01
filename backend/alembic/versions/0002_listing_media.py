#!/usr/bin/env python3
"""Repair Alembic 0002 revision metadata and duplicate properties.amenities.

Place THIS SCRIPT at the repository root (beside compose.yaml), NOT in
backend/alembic/versions/. Run: python3 fix_listing_media.py

Backs up the actual migration and refuses to modify files that do not look
like real Alembic migrations. Review changes and test against a DB backup.
"""
from __future__ import annotations

import ast
import difflib
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
VERSIONS = BASE / "backend" / "alembic" / "versions"
INITIAL = VERSIONS / "0001_initial.py"
TARGET = VERSIONS / "0002_listing_media.py"
EXPECTED = {"revision": "0002_listing_media", "down_revision": "0001_initial"}
HELPER = "_proptech_column_exists"


def literal(node):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def op_action(node):
    fn = node.func if isinstance(node, ast.Call) else None
    if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name) and fn.value.id == "op":
        return fn.attr
    return None


def is_column(node, col):
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "Column" and bool(node.args)
            and literal(node.args[0]) == col)


def amenity_operation(stmt, action):
    if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Call):
        return False
    call = stmt.value
    if op_action(call) != action or len(call.args) < 2 or literal(call.args[0]) != "properties":
        return False
    return (is_column(call.args[1], "amenities") if action == "add_column"
            else literal(call.args[1]) == "amenities")


def initial_defines_amenities(tree):
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        action = op_action(node)
        if action == "create_table" and node.args and literal(node.args[0]) == "properties":
            if any(is_column(arg, "amenities") for arg in node.args[1:]):
                return True
        if action == "add_column" and len(node.args) >= 2 and literal(node.args[0]) == "properties":
            if is_column(node.args[1], "amenities"):
                return True
    return False


def function(tree, name):
    matches = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one {name}() in 0002; restore the original migration first")
    return matches[0]


def missing_metadata(tree):
    missing = []
    for key, expected in EXPECTED.items():
        vals = []
        for n in tree.body:
            if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == key for t in n.targets):
                vals.append(literal(n.value))
            elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.target.id == key:
                vals.append(literal(n.value))
        if not vals:
            missing.append(key)
        elif vals != [expected]:
            raise ValueError(f"Conflicting {key}={vals!r}; expected {expected!r}")
    return missing


def main():
    if not INITIAL.is_file() or not TARGET.is_file():
        raise ValueError(f"Expected migrations at {VERSIONS}; place this script at the project root")

    initial_tree = ast.parse(INITIAL.read_text(encoding="utf-8"))
    before = TARGET.read_text(encoding="utf-8")