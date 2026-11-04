"""Explainable editorial and asking-price insights. Never present as a valuation."""
from decimal import Decimal
from statistics import median


def calculate_market_insights(*, asking_price: Decimal, area_sqft: Decimal,
                              comparable_prices: list[Decimal], duplicate_count: int) -> dict:
    prices = [Decimal(str(p)) for p in comparable_prices if p is not None and Decimal(str(p)) > 0]
    asking = Decimal(str(asking_price))
    area = Decimal(str(area_sqft))
    sample_size = len(prices)
    market_median = Decimal(str(median(prices))) if sample_size >= 3 else None
    difference = round(float((asking - market_median) / market_median * 100), 1) if market_median else None
    if difference is None:
        positioning = 'insufficient_data'
    elif difference > 15:
        positioning = 'above_local_asking_median'
    elif difference < -15:
        positioning = 'below_local_asking_median'
    else:
        positioning = 'near_local_asking_median'
    warnings = []
    if duplicate_count:
        warnings.append('Similar headline already exists in your portfolio; review for duplicate advertising')
    if sample_size < 3:
        warnings.append('Not enough local asking-price examples for a meaningful comparison')
    return {
        'asking_price_per_sqft': round(float(asking / area), 2) if area > 0 else None,
        'local_median_asking_price': round(float(market_median), 2) if market_median else None,
        'local_sample_size': sample_size,
        'difference_from_local_median_pct': difference,
        'positioning': positioning,
        'similar_portfolio_ad_count': duplicate_count,
        'warnings': warnings,
        'disclaimer': 'Based on advertised prices, not verified transactions or an appraisal. Local examples match city, locality, property type and sale/rent purpose.',
    }
