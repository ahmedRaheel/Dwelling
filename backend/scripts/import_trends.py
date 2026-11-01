"""Import externally sourced, reviewed PKR market benchmarks. Run with migration DB credentials.

CSV columns: month,city,area_name,kind,median_sale_price,median_monthly_rent,sample_size
Example: python scripts/import_trends.py ./trends.csv --source 'Your Verified Data Vendor' --approve
"""
import argparse
import csv
import os
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import create_engine, text
from app.models.entities import PropertyKind


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('csv_file')
    parser.add_argument('--source', required=True)
    parser.add_argument('--approve', action='store_true', help='Attest source and methodology were independently reviewed')
    args = parser.parse_args()
    if not args.approve:
        parser.error('Explicit --approve required: do not present unverified data as verified market facts')
    with open(args.csv_file, newline='', encoding='utf-8-sig') as handle:
        rows = list(csv.DictReader(handle))
    engine = create_engine(os.environ['MIGRATION_DATABASE_URL'])
    with engine.begin() as connection:
        for row in rows:
            if row['kind'] not in PropertyKind._value2member_map_:
                raise ValueError(f"Invalid kind: {row['kind']}")
            date = datetime.strptime(row['month'], '%Y-%m').replace(tzinfo=timezone.utc)
            sale = Decimal(row['median_sale_price']) if row['median_sale_price'] else None
            rent = Decimal(row['median_monthly_rent']) if row['median_monthly_rent'] else None
            sample_size = int(row['sample_size'])
            if sample_size < 3 or (sale is None and rent is None) or (sale is not None and sale <= 0) or (rent is not None and rent <= 0):
                raise ValueError('At least 3 observations and at least one positive price/rent are required')
            connection.execute(text('''INSERT INTO market_trends
                (id, city, area_name, month, kind, median_sale_price, median_monthly_rent, sample_size, verified, source)
                VALUES (:id, :city, :area_name, :month, CAST(:kind AS property_kind), :sale, :rent, :sample_size, true, :source)
                ON CONFLICT (city, area_name, month, kind) DO UPDATE SET
                median_sale_price=EXCLUDED.median_sale_price, median_monthly_rent=EXCLUDED.median_monthly_rent,
                sample_size=EXCLUDED.sample_size, verified=true, source=EXCLUDED.source'''),
                               {'id': uuid4(), 'city': row['city'].strip(), 'area_name': row['area_name'].strip(),
                                'month': date, 'kind': row['kind'], 'sale': sale, 'rent': rent,
                                'sample_size': sample_size, 'source': args.source})
    print(f'Imported {len(rows)} reviewed trend observations')


if __name__ == '__main__':
    main()
