"""Dependency-free release guards. These do not replace the image/import smoke test."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'app'


def test_python_source_compiles():
    for path in [*APP.rglob('*.py'), *(ROOT / 'alembic').rglob('*.py')]:
        compile(path.read_bytes(), str(path), 'exec')


def test_all_internal_app_imports_resolve_to_packaged_modules():
    # Detects omitted modules such as app.services.listing_insights even when
    # third-party dependencies are unavailable in the developer environment.
    for path in APP.rglob('*.py'):
        for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
            targets = []
            if isinstance(node, ast.Import):
                targets = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                targets = [node.module]
            for target in targets:
                if not target.startswith('app.'):
                    continue
                location = ROOT.joinpath(*target.split('.'))
                assert location.with_suffix('.py').is_file() or (location / '__init__.py').is_file(), (
                    f'{path.relative_to(ROOT)} references missing shipped module {target}'
                )


def test_detail_relationships_loaded_before_access():
    source = (APP / 'features/listings/commands.py').read_text()
    tree = ast.parse(source)
    assign = next(node for node in tree.body if isinstance(node, ast.AsyncFunctionDef) and node.name == 'assign_details')
    refresh_positions = [node.lineno for node in ast.walk(assign) if isinstance(node, ast.Await)
                         and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute)
                         and node.value.func.attr == 'refresh']
    relationship_positions = [node.lineno for node in ast.walk(assign) if isinstance(node, ast.Attribute)
                              and isinstance(node.value, ast.Name) and node.value.id == 'item'
                              and node.attr in {'pg', 'portion'}]
    assert refresh_positions and relationship_positions
    assert min(refresh_positions) < min(relationship_positions)


def test_release_image_build_performs_import_smoke():
    dockerfile = (ROOT / 'Dockerfile').read_text()
    assert 'python -m app.release_check' in dockerfile
    assert (APP / 'services/listing_insights.py').is_file()
