
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
    # PROPTECH_PHOTO_SCHEMA_REPAIR_V1
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
