
"""Photo gallery, listing highlights, map location, and agent contact."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Alembic revision identifiers
revision = "0002_listing_media"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())

    return any(
        column["name"] == column_name
        for column in inspector.get_columns(
            table_name,
            schema="public",
        )
    )


def upgrade() -> None:
    # Prevent the known duplicate-column error.
    if not column_exists("properties", "amenities"):
        op.add_column(
            "properties",
            sa.Column(
                "amenities",
                postgresql.JSONB(),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
        )

    # Keep all other operations from your ORIGINAL
    # 0002_listing_media.py here.


def downgrade() -> None:
    # Keep the original downgrade operations.
    # Do not drop amenities if migration 0001 owns it.
    pass
