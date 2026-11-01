"""Prune orphaned gallery objects safely after DB commits/rollbacks.

Run from a trusted maintenance job with access to the persistent media volume
and the privileged migration database URL. Default is DRY RUN.

  python scripts/prune_media.py --min-age-hours 48
  python scripts/prune_media.py --min-age-hours 48 --apply
"""
import argparse
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg


def clean_url(raw: str) -> str:
    # SQLAlchemy sync dialect prefix is not accepted by bare psycopg.
    return raw.replace('postgresql+psycopg://', 'postgresql://', 1)


def main() -> None:
    parser = argparse.ArgumentParser(description='Remove orphaned property photographs')
    parser.add_argument('--apply', action='store_true', help='Actually unlink orphaned files')
    parser.add_argument('--min-age-hours', type=int, default=48)
    args = parser.parse_args()
    if args.min_age_hours < 24:
        parser.error('Use a safety window of at least 24 hours')
    root = Path(os.environ.get('MEDIA_DIR', '/srv/media')).resolve()
    db_url = os.environ.get('MIGRATION_DATABASE_URL')
    if not db_url:
        parser.error('MIGRATION_DATABASE_URL is required')
    if not root.is_dir():
        parser.error(f'Media directory not found: {root}')
    with psycopg.connect(clean_url(db_url), autocommit=True) as db:
        with db.cursor() as cur:
            cur.execute('SELECT object_key, thumbnail_key FROM property_photos')
            live = {key for pair in cur.fetchall() for key in pair}
    threshold = (datetime.now(timezone.utc) - timedelta(hours=args.min_age_hours)).timestamp()
    unreferenced: list[Path] = []
    for file in root.rglob('*.webp'):
        if file.is_symlink() or not file.is_file():
            continue
        if file.stat().st_mtime < threshold and file.relative_to(root).as_posix() not in live:
            unreferenced.append(file)
    for file in unreferenced:
        print(('REMOVE' if args.apply else 'DRY-RUN'), file.relative_to(root))
        if args.apply:
            file.unlink(missing_ok=True)
    print(f'{len(unreferenced)} orphaned object(s) found; apply={args.apply}')


if __name__ == '__main__':
    main()
