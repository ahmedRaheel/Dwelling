"""Search refinement, agency directory, saved searches and visit scheduling.

Revision ID: 0003_discovery_workspace
Revises: 0002_listing_media
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = '0003_discovery_workspace'
down_revision = '0002_listing_media'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('tenants', sa.Column('public_description', sa.Text(), nullable=False, server_default=''))
    op.add_column('tenants', sa.Column('public_city', sa.String(100), nullable=False, server_default=''))
    op.add_column('tenants', sa.Column('public_phone', sa.String(40), nullable=True))
    op.add_column('tenants', sa.Column('public_email', sa.String(255), nullable=True))
    op.add_column('properties', sa.Column('society', sa.String(120), nullable=False, server_default=''))
    op.add_column('properties', sa.Column('block', sa.String(100), nullable=False, server_default=''))
    op.add_column('properties', sa.Column('price_negotiable', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('properties', sa.Column('ready_to_move', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('properties', sa.Column('video_url', sa.String(350), nullable=True))
    op.create_index('ix_properties_society', 'properties', ['city', 'society'])
    op.add_column('property_photos', sa.Column('category', sa.String(20), nullable=False, server_default='gallery'))
    op.create_check_constraint('ck_photo_category', 'property_photos', "category IN ('gallery','floorplan')")

    op.create_table('saved_searches',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('name', sa.String(120), nullable=False),
        sa.Column('filters', postgresql.JSONB(), nullable=False),
        sa.Column('alerts_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_saved_searches_owner', 'saved_searches', ['tenant_id', 'user_id'])
    op.create_table('viewing_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('property_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('properties.id'), nullable=False),
        sa.Column('customer_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('preferred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('contact_name', sa.String(160), nullable=False),
        sa.Column('contact_phone', sa.String(40), nullable=False),
        sa.Column('note', sa.String(1000), nullable=False, server_default=''),
        sa.Column('status', sa.String(20), nullable=False, server_default='requested'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('requested','confirmed','declined','completed','cancelled')", name='ck_viewing_status'),
    )
    op.create_index('ix_viewings_agency_time', 'viewing_requests', ['tenant_id', 'preferred_at'])
    op.create_index('ix_viewings_customer', 'viewing_requests', ['customer_user_id', 'created_at'])

    tid = "nullif(current_setting('app.tenant_id', true), '')::uuid"
    uid = "nullif(current_setting('app.user_id', true), '')::uuid"
    for table in ('saved_searches', 'viewing_requests'):
        op.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY')
    op.execute(f'CREATE POLICY search_select ON saved_searches FOR SELECT USING (tenant_id = {tid} AND user_id = {uid})')
    op.execute(f'CREATE POLICY search_insert ON saved_searches FOR INSERT WITH CHECK (tenant_id = {tid} AND user_id = {uid})')
    op.execute(f'CREATE POLICY search_update ON saved_searches FOR UPDATE USING (tenant_id = {tid} AND user_id = {uid}) WITH CHECK (tenant_id = {tid} AND user_id = {uid})')
    op.execute(f'CREATE POLICY search_delete ON saved_searches FOR DELETE USING (tenant_id = {tid} AND user_id = {uid})')
    op.execute(f'CREATE POLICY viewing_select ON viewing_requests FOR SELECT USING (tenant_id = {tid} OR customer_user_id = {uid})')
    op.execute(f'CREATE POLICY viewing_insert ON viewing_requests FOR INSERT WITH CHECK (tenant_id = {tid} AND customer_user_id = {uid})')
    op.execute(f'CREATE POLICY viewing_update ON viewing_requests FOR UPDATE USING (tenant_id = {tid} OR customer_user_id = {uid}) WITH CHECK (tenant_id = {tid} OR (customer_user_id = {uid} AND status = \'cancelled\'))')
    op.execute('GRANT SELECT, INSERT, UPDATE, DELETE ON saved_searches TO proptech_app')
    op.execute('GRANT SELECT, INSERT, UPDATE ON viewing_requests TO proptech_app')

    # Prevent cross-tenant forged appointments by resolving agency identity from a published listing.
    # This is owned by the migrator, not proptech_app, and grants only constrained EXECUTE.
    op.execute("""
      CREATE FUNCTION public.request_property_viewing(
          p_property uuid, p_when timestamptz, p_name text, p_phone text, p_note text)
      RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
      DECLARE v_tenant uuid; v_customer uuid; v_viewing uuid;
      BEGIN
        v_customer := nullif(current_setting('app.user_id', true), '')::uuid;
        IF v_customer IS NULL OR v_customer = '00000000-0000-0000-0000-000000000000'
          OR NOT EXISTS (SELECT 1 FROM public.users WHERE id=v_customer AND active) THEN
          RAISE EXCEPTION 'Authenticated account required' USING ERRCODE='28000';
        END IF;
        IF p_when < now() + interval '1 hour' OR p_when > now() + interval '90 days'
          OR length(p_name) NOT BETWEEN 2 AND 160 OR length(p_phone) NOT BETWEEN 7 AND 40
          OR length(p_note) > 1000 THEN
          RAISE EXCEPTION 'Invalid viewing request' USING ERRCODE='22023';
        END IF;
        SELECT tenant_id INTO v_tenant FROM public.properties WHERE id=p_property AND status='published';
        IF v_tenant IS NULL THEN RAISE EXCEPTION 'Property unavailable' USING ERRCODE='22023'; END IF;
        INSERT INTO public.viewing_requests(id,tenant_id,property_id,customer_user_id,preferred_at,contact_name,contact_phone,note)
        VALUES (gen_random_uuid(),v_tenant,p_property,v_customer,p_when,p_name,p_phone,p_note)
        RETURNING id INTO v_viewing;
        RETURN v_viewing;
      END; $$
    """)
    op.execute('REVOKE ALL ON FUNCTION public.request_property_viewing(uuid,timestamptz,text,text,text) FROM PUBLIC')
    op.execute('GRANT EXECUTE ON FUNCTION public.request_property_viewing(uuid,timestamptz,text,text,text) TO proptech_app')


def downgrade():
    op.execute('DROP FUNCTION IF EXISTS public.request_property_viewing(uuid,timestamptz,text,text,text)')
    op.drop_table('viewing_requests')
    op.drop_table('saved_searches')
    op.drop_constraint('ck_photo_category', 'property_photos', type_='check')
    op.drop_column('property_photos', 'category')
    op.drop_index('ix_properties_society', 'properties')
    for name in ('video_url','ready_to_move','price_negotiable','block','society'):
        op.drop_column('properties', name)
    for name in ('public_email','public_phone','public_city','public_description'):
        op.drop_column('tenants', name)
