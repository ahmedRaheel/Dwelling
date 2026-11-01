"""Photo gallery, listing highlights, map location, and agent contact.

Revision ID: 0002_listing_media
Revises: 0001_initial
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = '0002_listing_media'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('properties', sa.Column('amenities', postgresql.JSONB(), nullable=False, server_default='[]'))
    op.add_column('properties', sa.Column('highlights', postgresql.JSONB(), nullable=False, server_default='[]'))
    op.add_column('properties', sa.Column('contact_phone', sa.String(40)))
    op.add_column('properties', sa.Column('latitude', sa.Float()))
    op.add_column('properties', sa.Column('longitude', sa.Float()))
    op.create_table(
        'property_photos',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('property_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('object_key', sa.String(255), nullable=False, unique=True),
        sa.Column('thumbnail_key', sa.String(255), nullable=False, unique=True),
        sa.Column('alt_text', sa.String(180), nullable=False, server_default=''),
        sa.Column('width', sa.Integer(), nullable=False),
        sa.Column('height', sa.Integer(), nullable=False),
        sa.Column('byte_size', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_cover', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('position >= 0', name='ck_photo_position'),
        sa.CheckConstraint('byte_size > 0 AND width > 0 AND height > 0', name='ck_photo_dimensions'),
    )
    op.create_index('ix_property_photos_property_id', 'property_photos', ['property_id'])
    op.create_index('ix_property_photos_tenant_id', 'property_photos', ['tenant_id'])
    op.create_index('ix_property_photos_order', 'property_photos', ['property_id', 'position'])
    op.execute('ALTER TABLE property_photos ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE property_photos FORCE ROW LEVEL SECURITY')
    tenant = "nullif(current_setting('app.tenant_id', true), '')::uuid"
    op.execute(f"""CREATE POLICY photos_select ON property_photos FOR SELECT USING (
        tenant_id = {tenant} OR EXISTS (
            SELECT 1 FROM properties p WHERE p.id = property_id AND p.status = 'published'))""")
    for cmd in ('INSERT', 'UPDATE', 'DELETE'):
        name = f'photos_{cmd.lower()}'
        if cmd == 'INSERT':
            op.execute(f'CREATE POLICY {name} ON property_photos FOR INSERT WITH CHECK (tenant_id = {tenant})')
        elif cmd == 'UPDATE':
            op.execute(f'CREATE POLICY {name} ON property_photos FOR UPDATE USING (tenant_id = {tenant}) WITH CHECK (tenant_id = {tenant})')
        else:
            op.execute(f'CREATE POLICY {name} ON property_photos FOR DELETE USING (tenant_id = {tenant})')
    op.execute('GRANT SELECT, INSERT, UPDATE, DELETE ON property_photos TO proptech_app')


def downgrade():
    op.drop_table('property_photos')
    for column in ('longitude', 'latitude', 'contact_phone', 'highlights', 'amenities'):
        op.drop_column('properties', column)
