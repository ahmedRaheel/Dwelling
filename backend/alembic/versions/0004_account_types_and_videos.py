"""Account categories and private listing video metadata.

Revision ID: 0004_account_types_and_videos
Revises: 0003_discovery_workspace
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = '0004_account_types_and_videos'
down_revision = '0003_discovery_workspace'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {col['name'] for col in sa.inspect(bind).get_columns('tenants')}
    if 'account_type' not in columns:
        op.add_column('tenants', sa.Column('account_type', sa.String(24),
                      nullable=False, server_default='agency'))
    op.execute("""ALTER TABLE public.tenants
       ADD CONSTRAINT ck_tenant_account_type CHECK
       (account_type IN ('agency','owner','broker','dealer','customer'))""")
    op.create_table(
        'property_videos',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('property_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('object_key', sa.String(255), nullable=False, unique=True),
        sa.Column('mime_type', sa.String(40), nullable=False),
        sa.Column('byte_size', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint('byte_size > 0', name='ck_video_size'),
    )
    op.create_index('ix_property_videos_tenant_id', 'property_videos', ['tenant_id'])
    op.execute('ALTER TABLE public.property_videos ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE public.property_videos FORCE ROW LEVEL SECURITY')
    tid = "nullif(current_setting('app.tenant_id', true), '')::uuid"
    op.execute(f"""CREATE POLICY video_select ON public.property_videos FOR SELECT
      USING (tenant_id = {tid} OR EXISTS (
         SELECT 1 FROM public.properties p WHERE p.id = property_id AND p.status='published'))""")
    op.execute(f"""CREATE POLICY video_insert ON public.property_videos FOR INSERT
      WITH CHECK (tenant_id = {tid} AND EXISTS (
         SELECT 1 FROM public.properties p WHERE p.id = property_id AND p.tenant_id = {tid}))""")
    op.execute(f"""CREATE POLICY video_update ON public.property_videos FOR UPDATE
      USING (tenant_id = {tid}) WITH CHECK (tenant_id = {tid})""")
    op.execute(f"CREATE POLICY video_delete ON public.property_videos FOR DELETE USING (tenant_id = {tid})")
    op.execute('GRANT SELECT, INSERT, UPDATE, DELETE ON public.property_videos TO proptech_app')


def downgrade():
    raise RuntimeError('Manual, data-preserving rollback required for account types and uploaded videos')
