"""Fast release gates; no running PostgreSQL required for these tests."""
import ast
from pathlib import Path

from app.release_check import verify
from app.features.listings.commands import load_listing_relations


def test_every_production_module_importable():
    verify()


def test_listing_command_boundary_never_uses_sync_session():
    source = Path(__file__).parents[1] / 'app/features/listings/commands.py'
    module = ast.parse(source.read_text())
    assert any(isinstance(node, ast.AsyncFunctionDef) and node.name == 'assign_details' for node in module.body)
    assert any(isinstance(node, ast.AsyncFunctionDef) and node.name == 'load_listing_relations' for node in module.body)
    assert 'await db.refresh(item, attribute_names=' in source.read_text()


def test_insights_is_a_shipped_service():
    from app.services.listing_insights import calculate_market_insights
    from decimal import Decimal
    result = calculate_market_insights(asking_price=Decimal('50000'), area_sqft=Decimal('1400'), comparable_prices=[], duplicate_count=0)
    assert result['positioning'] == 'insufficient_data'
