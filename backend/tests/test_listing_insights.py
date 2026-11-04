"""Pure tests run without PostgreSQL; endpoint authorization is integration-tested."""
from decimal import Decimal
from app.services.listing_insights import calculate_market_insights


def test_insufficient_comparables_never_claim_valuation():
    result = calculate_market_insights(asking_price=Decimal('5000000'), area_sqft=Decimal('1000'),
                                       comparable_prices=[Decimal('3000000')], duplicate_count=0)
    assert result['positioning'] == 'insufficient_data'
    assert result['local_median_asking_price'] is None
    assert result['asking_price_per_sqft'] == 5000


def test_comparables_and_duplicate_warning():
    result = calculate_market_insights(asking_price=Decimal('12000000'), area_sqft=Decimal('1200'),
                                       comparable_prices=[Decimal('8000000'), Decimal('9000000'), Decimal('10000000')],
                                       duplicate_count=2)
    assert result['local_median_asking_price'] == 9000000
    assert result['positioning'] == 'above_local_asking_median'
    assert result['difference_from_local_median_pct'] == 33.3
    assert len(result['warnings']) == 1


def test_zero_area_safe_and_bad_comparables_ignored():
    result = calculate_market_insights(asking_price=Decimal('100'), area_sqft=Decimal('0'),
                                       comparable_prices=[Decimal('0'), Decimal('-50'), Decimal('100')], duplicate_count=0)
    assert result['asking_price_per_sqft'] is None
    assert result['local_sample_size'] == 1
